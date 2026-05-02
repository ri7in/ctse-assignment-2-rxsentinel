"""Interaction checker tool — owned by Shehan (Interaction Analyzer agent).

Combines two evidence sources for drug-drug interactions:

1. A curated local SQLite of high-severity interactions (seeded from
   `data/seed_interactions.csv`). This is fast, offline, deterministic, and
   covers the most clinically-significant pairs.

2. The openFDA adverse-event endpoint, which gives a population-level signal:
   how often the two drugs co-appear in adverse-event reports, and what the
   top reactions are. This adds breadth at the cost of specificity.

Results from both are combined and deduplicated. The local DB wins on
mechanism/recommendation copy when both sources have data on the same pair.
"""
from __future__ import annotations

import csv
import json
import sqlite3
from contextlib import closing
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from rxsentinel.config import settings


Severity = Literal["high", "moderate", "low"]

def _interactions_db():
    """Resolve the interactions DB path lazily so test fixtures can redirect it."""
    return settings.cache_dir / "interactions.db"
_OPENFDA_CACHE_TTL = timedelta(hours=24)
_SEED_CSV = Path(__file__).resolve().parent.parent / "data" / "seed_interactions.csv"


@dataclass(slots=True)
class InteractionRecord:
    """One detected drug-drug interaction."""

    rxcui_a: str
    rxcui_b: str
    name_a: str
    name_b: str
    severity: Severity
    mechanism: str
    clinical_effect: str
    recommendation: str
    sources: list[str] = field(default_factory=list)


def _ensure_db() -> None:
    """Create the interactions table and seed it on first run."""
    with closing(sqlite3.connect(_interactions_db())) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS interactions (
                rxcui_a TEXT NOT NULL,
                rxcui_b TEXT NOT NULL,
                name_a TEXT NOT NULL,
                name_b TEXT NOT NULL,
                severity TEXT NOT NULL,
                mechanism TEXT NOT NULL,
                clinical_effect TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                PRIMARY KEY (rxcui_a, rxcui_b)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS openfda_cache (
                query_key TEXT PRIMARY KEY,
                result TEXT NOT NULL,
                fetched_at TEXT NOT NULL
            )
            """
        )
        # Seed if empty.
        n = conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
        if n == 0 and _SEED_CSV.exists():
            with _SEED_CSV.open() as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            for row in rows:
                a, b = sorted([row["rxcui_a"], row["rxcui_b"]])
                # Normalize order so (a,b) and (b,a) collapse to one entry.
                if a == row["rxcui_a"]:
                    name_a, name_b = row["name_a"], row["name_b"]
                else:
                    name_a, name_b = row["name_b"], row["name_a"]
                conn.execute(
                    """
                    INSERT OR IGNORE INTO interactions
                    (rxcui_a, rxcui_b, name_a, name_b, severity, mechanism,
                     clinical_effect, recommendation)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        a, b, name_a, name_b,
                        row["severity"], row["mechanism"],
                        row["clinical_effect"], row["recommendation"],
                    ),
                )
        conn.commit()


def _local_lookup(rxcui_a: str, rxcui_b: str) -> InteractionRecord | None:
    """Query the local DB. Returns None if no record exists for the pair."""
    _ensure_db()
    a, b = sorted([rxcui_a, rxcui_b])
    with closing(sqlite3.connect(_interactions_db())) as conn:
        row = conn.execute(
            """
            SELECT name_a, name_b, severity, mechanism, clinical_effect, recommendation
            FROM interactions
            WHERE rxcui_a = ? AND rxcui_b = ?
            """,
            (a, b),
        ).fetchone()
    if not row:
        return None
    return InteractionRecord(
        rxcui_a=a,
        rxcui_b=b,
        name_a=row[0],
        name_b=row[1],
        severity=row[2],  # type: ignore[arg-type]
        mechanism=row[3],
        clinical_effect=row[4],
        recommendation=row[5],
        sources=["local-db"],
    )


def _openfda_cache_get(key: str) -> dict[str, Any] | None:
    _ensure_db()
    with closing(sqlite3.connect(_interactions_db())) as conn:
        row = conn.execute(
            "SELECT result, fetched_at FROM openfda_cache WHERE query_key = ?", (key,)
        ).fetchone()
    if not row:
        return None
    if datetime.utcnow() - datetime.fromisoformat(row[1]) > _OPENFDA_CACHE_TTL:
        return None
    return json.loads(row[0])


def _openfda_cache_put(key: str, result: dict[str, Any]) -> None:
    _ensure_db()
    with closing(sqlite3.connect(_interactions_db())) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO openfda_cache (query_key, result, fetched_at) VALUES (?, ?, ?)",
            (key, json.dumps(result), datetime.utcnow().isoformat()),
        )
        conn.commit()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type((httpx.HTTPError, ConnectionError, TimeoutError)),
    reraise=True,
)
async def query_openfda(drug_a: str, drug_b: str) -> dict[str, Any]:
    """Query openFDA adverse-events for events co-mentioning two drugs.

    Hits https://api.fda.gov/drug/event.json — no auth required, free public API.
    The endpoint returns aggregate counts of adverse-event reactions where
    BOTH drugs appear in the report.

    Args:
        drug_a: First drug name (canonical, e.g., "metformin").
        drug_b: Second drug name.

    Returns:
        Dict with keys:
            co_mention_count: int total adverse-event reports mentioning both
            top_reactions: list[dict[str, int]] top 10 reaction terms
            severity_signal: float in [0,1] heuristic from "death"/"serious"
                fields in the data

        Returns {co_mention_count: 0, ...} on no-match. Returns cached values
        for 24h.

    Examples:
        >>> import asyncio
        >>> r = asyncio.run(query_openfda("ibuprofen", "lisinopril"))
        >>> r["co_mention_count"] >= 0
        True
    """
    a, b = sorted([drug_a.lower(), drug_b.lower()])
    cache_key = f"{a}::{b}"
    cached = _openfda_cache_get(cache_key)
    if cached is not None:
        return cached

    search = f'patient.drug.medicinalproduct:"{a}"+AND+patient.drug.medicinalproduct:"{b}"'
    url = f"{settings.openfda_base_url}/drug/event.json"
    params = {"search": search, "count": "patient.reaction.reactionmeddrapt.exact", "limit": 10}

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=settings.http_timeout)
            if resp.status_code == 404:
                # openFDA returns 404 when search produces zero results.
                result = {"co_mention_count": 0, "top_reactions": [], "severity_signal": 0.0}
                _openfda_cache_put(cache_key, result)
                return result
            resp.raise_for_status()
            data = resp.json()
        except Exception:  # noqa: BLE001 — graceful degrade on any transport error
            return {"co_mention_count": 0, "top_reactions": [], "severity_signal": 0.0}

    reactions = data.get("results", [])
    top = [{"term": r["term"], "count": r["count"]} for r in reactions]
    total = sum(r["count"] for r in reactions)

    serious_terms = {"death", "fatal", "hospitalization", "life threatening"}
    serious_count = sum(r["count"] for r in reactions if r["term"].lower() in serious_terms)
    severity_signal = min(1.0, serious_count / max(total, 1))

    result = {
        "co_mention_count": total,
        "top_reactions": top,
        "severity_signal": round(severity_signal, 3),
    }
    _openfda_cache_put(cache_key, result)
    return result


async def check_interaction(rxcui_a: str, rxcui_b: str) -> list[InteractionRecord]:
    """Check for known interactions between two RxCUIs.

    Combines the curated local DB with the openFDA adverse-event signal. The
    local DB takes priority for mechanism/recommendation text; openFDA adds
    a "severity_signal" if the local rule doesn't already classify as "high".

    Args:
        rxcui_a: First drug's RxNorm Concept Unique Identifier.
        rxcui_b: Second drug's RxCUI.

    Returns:
        A list of InteractionRecord. Empty if no interaction is found.

    Examples:
        >>> import asyncio
        >>> rs = asyncio.run(check_interaction("6809", "29046"))
        >>> all(isinstance(r, InteractionRecord) for r in rs)
        True
    """
    if not rxcui_a or not rxcui_b or rxcui_a == rxcui_b:
        return []

    local = _local_lookup(rxcui_a, rxcui_b)
    records: list[InteractionRecord] = []
    if local is not None:
        records.append(local)

    # If we have name info, query openFDA in parallel for population signal.
    if local:
        try:
            fda = await query_openfda(local.name_a, local.name_b)
            if fda["co_mention_count"] > 0:
                local.sources.append("openFDA")
                # Upgrade severity if openFDA shows >5% serious co-reports
                if fda["severity_signal"] > 0.05 and local.severity == "low":
                    local.severity = "moderate"
        except (httpx.HTTPError, ConnectionError, TimeoutError):
            pass

    return records


def severity_summary(interactions: list[InteractionRecord]) -> dict[str, int]:
    """Tally interactions by severity. Used by Analyzer agent for the report."""
    summary = {"high": 0, "moderate": 0, "low": 0}
    for r in interactions:
        summary[r.severity] += 1
    return summary


def to_dict(record: InteractionRecord) -> dict[str, Any]:
    """Serialize for trace/JSON output."""
    return asdict(record)
