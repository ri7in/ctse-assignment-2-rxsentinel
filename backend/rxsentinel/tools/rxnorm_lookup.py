"""RxNorm lookup tool — owned by Thusala (Medication Parser agent).

Hits the NIH RxNorm REST API to normalize free-form drug names to a canonical
RxCUI (RxNorm Concept Unique Identifier). Falls back to fuzzy/approximate
matching when the exact name doesn't resolve. Caches results in a SQLite file
for 7 days to keep the demo fast and to survive offline mode.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any

import httpx
from rapidfuzz import fuzz
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from rxsentinel.config import settings


_CACHE_TTL = timedelta(days=7)
def _cache_db() -> "Path":
    """Resolve the cache DB path lazily so test fixtures can redirect it."""
    return settings.cache_dir / "rxnorm_cache.db"


@dataclass(slots=True)
class RxNormResult:
    """Outcome of an RxNorm lookup.

    Attributes:
        rxcui: The canonical RxNorm Concept Unique Identifier, or None.
        canonical_name: The canonical drug name (e.g., "acetaminophen"), or
            the original query if no match.
        confidence: 1.0 for exact match, 0.4-0.9 for fuzzy, 0.0 for no match.
        alternatives: Up to 4 alternative candidates from approximate matching.
        source: "exact", "approximate", "cache", or "none".
    """

    rxcui: str | None
    canonical_name: str
    confidence: float
    alternatives: list[dict[str, Any]] = field(default_factory=list)
    source: str = "none"


class RxNormAPIError(RuntimeError):
    """Raised when the RxNorm API repeatedly fails."""


def _ensure_cache_table() -> None:
    """Create the cache table on first use."""
    with closing(sqlite3.connect(_cache_db())) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rxnorm_cache (
                query TEXT PRIMARY KEY,
                result TEXT NOT NULL,
                fetched_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def _cache_get(query: str) -> RxNormResult | None:
    """Read a cached result if it exists and is not stale."""
    _ensure_cache_table()
    with closing(sqlite3.connect(_cache_db())) as conn:
        row = conn.execute(
            "SELECT result, fetched_at FROM rxnorm_cache WHERE query = ?",
            (query.lower(),),
        ).fetchone()
    if not row:
        return None
    fetched_at = datetime.fromisoformat(row[1])
    if datetime.utcnow() - fetched_at > _CACHE_TTL:
        return None
    data = json.loads(row[0])
    data["source"] = "cache"
    return RxNormResult(**data)


def _cache_put(query: str, result: RxNormResult) -> None:
    _ensure_cache_table()
    with closing(sqlite3.connect(_cache_db())) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO rxnorm_cache (query, result, fetched_at) VALUES (?, ?, ?)",
            (query.lower(), json.dumps(asdict(result)), datetime.utcnow().isoformat()),
        )
        conn.commit()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type((httpx.HTTPError, ConnectionError, TimeoutError)),
    reraise=True,
)
async def _fetch_exact(client: httpx.AsyncClient, name: str) -> str | None:
    """Try the exact-match endpoint and return rxcui if found."""
    resp = await client.get(
        f"{settings.rxnorm_base_url}/rxcui.json",
        params={"name": name},
        timeout=settings.http_timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    ids = data.get("idGroup", {}).get("rxnormId") or []
    return ids[0] if ids else None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type((httpx.HTTPError, ConnectionError, TimeoutError)),
    reraise=True,
)
async def _fetch_approximate(
    client: httpx.AsyncClient, name: str
) -> list[dict[str, Any]]:
    """Try the approximate-term endpoint and return up to 5 candidates."""
    resp = await client.get(
        f"{settings.rxnorm_base_url}/approximateTerm.json",
        params={"term": name, "maxEntries": 5},
        timeout=settings.http_timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("approximateGroup", {}).get("candidate") or []


async def rxnorm_lookup(drug_name: str, *, fuzzy: bool = True) -> RxNormResult:
    """Resolve a free-form drug name to a normalized RxNorm record.

    Cache-first: a hit on the local SQLite cache short-circuits the API call.

    Args:
        drug_name: The drug name in any form — brand, generic, or misspelled.
        fuzzy: If True (default), fall back to approximateTerm when the exact
            endpoint returns nothing.

    Returns:
        RxNormResult. If no match is found, rxcui is None and confidence is 0.

    Raises:
        RxNormAPIError: Only after 3 retries on the underlying API.

    Examples:
        >>> import asyncio
        >>> r = asyncio.run(rxnorm_lookup("Tylenol"))
        >>> r.canonical_name
        'acetaminophen'
        >>> r.rxcui
        '1191'
    """
    if not drug_name or not drug_name.strip():
        return RxNormResult(rxcui=None, canonical_name="", confidence=0.0, source="none")

    name = drug_name.strip()
    cached = _cache_get(name)
    if cached:
        return cached

    async with httpx.AsyncClient() as client:
        try:
            exact = await _fetch_exact(client, name)
        except httpx.HTTPError as e:
            raise RxNormAPIError(f"exact lookup failed for {name!r}") from e

        if exact:
            result = RxNormResult(
                rxcui=exact,
                canonical_name=name.lower(),
                confidence=1.0,
                source="exact",
            )
            _cache_put(name, result)
            return result

        if not fuzzy:
            result = RxNormResult(rxcui=None, canonical_name=name, confidence=0.0)
            _cache_put(name, result)
            return result

        try:
            candidates = await _fetch_approximate(client, name)
        except httpx.HTTPError as e:
            raise RxNormAPIError(f"approximate lookup failed for {name!r}") from e

    if not candidates:
        result = RxNormResult(rxcui=None, canonical_name=name, confidence=0.0)
        _cache_put(name, result)
        return result

    top = candidates[0]
    rxcui = str(top.get("rxcui") or "") or None
    canonical = str(top.get("name") or name).lower()
    # Combine RxNorm score (0..100) with rapidfuzz string similarity for a
    # confidence in [0,1]. RxNorm score weighted 0.6, fuzz weighted 0.4.
    api_score = float(top.get("score") or 0) / 100
    fuzz_score = fuzz.ratio(name.lower(), canonical) / 100
    confidence = round(0.6 * api_score + 0.4 * fuzz_score, 2)

    result = RxNormResult(
        rxcui=rxcui,
        canonical_name=canonical,
        confidence=confidence,
        alternatives=[{"rxcui": c.get("rxcui"), "name": c.get("name")} for c in candidates[1:5]],
        source="approximate",
    )
    _cache_put(name, result)
    return result
