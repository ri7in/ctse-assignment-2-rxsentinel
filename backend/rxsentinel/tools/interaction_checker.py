"""Interaction checker tool — Shehan. Initial local-DB-only version."""
from __future__ import annotations

import csv
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from rxsentinel.config import settings


Severity = Literal["high", "moderate", "low"]
_DB = settings.cache_dir / "interactions.db"
_SEED = Path(__file__).resolve().parent.parent / "data" / "seed_interactions.csv"


@dataclass
class InteractionRecord:
    rxcui_a: str
    rxcui_b: str
    name_a: str
    name_b: str
    severity: Severity
    mechanism: str
    clinical_effect: str
    recommendation: str
    sources: list = field(default_factory=list)


def _ensure_db() -> None:
    with closing(sqlite3.connect(_DB)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                rxcui_a TEXT, rxcui_b TEXT, name_a TEXT, name_b TEXT,
                severity TEXT, mechanism TEXT, clinical_effect TEXT,
                recommendation TEXT, PRIMARY KEY (rxcui_a, rxcui_b)
            )""")
        n = conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
        if n == 0 and _SEED.exists():
            with _SEED.open() as f:
                for row in csv.DictReader(f):
                    a, b = sorted([row["rxcui_a"], row["rxcui_b"]])
                    name_a, name_b = (row["name_a"], row["name_b"]) if a == row["rxcui_a"] else (row["name_b"], row["name_a"])
                    conn.execute(
                        "INSERT OR IGNORE INTO interactions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (a, b, name_a, name_b, row["severity"], row["mechanism"],
                         row["clinical_effect"], row["recommendation"]),
                    )
        conn.commit()


async def check_interaction(rxcui_a: str, rxcui_b: str) -> list[InteractionRecord]:
    """Look up an interaction in the curated local DB."""
    if not rxcui_a or not rxcui_b or rxcui_a == rxcui_b:
        return []
    _ensure_db()
    a, b = sorted([rxcui_a, rxcui_b])
    with closing(sqlite3.connect(_DB)) as conn:
        row = conn.execute(
            "SELECT name_a, name_b, severity, mechanism, clinical_effect, recommendation "
            "FROM interactions WHERE rxcui_a = ? AND rxcui_b = ?", (a, b),
        ).fetchone()
    if not row:
        return []
    return [InteractionRecord(a, b, row[0], row[1], row[2], row[3], row[4], row[5], ["local-db"])]


def severity_summary(interactions: list) -> dict:
    summary = {"high": 0, "moderate": 0, "low": 0}
    for r in interactions:
        summary[r.severity] += 1
    return summary
