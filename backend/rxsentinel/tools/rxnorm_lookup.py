"""RxNorm lookup tool — Thusala.

Initial cut: exact-match-only against the NIH RxNorm REST API. No cache,
no fuzzy fallback. Will be hardened in follow-up commits.
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from rxsentinel.config import settings


@dataclass
class RxNormResult:
    rxcui: str | None
    canonical_name: str
    confidence: float


async def rxnorm_lookup(drug_name: str) -> RxNormResult:
    """Look up a drug name in NIH RxNorm. Exact match only for now."""
    if not drug_name.strip():
        return RxNormResult(None, "", 0.0)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.rxnorm_base_url}/rxcui.json",
            params={"name": drug_name.strip()},
            timeout=settings.http_timeout,
        )
        resp.raise_for_status()
        ids = resp.json().get("idGroup", {}).get("rxnormId") or []
    if ids:
        return RxNormResult(ids[0], drug_name.lower(), 1.0)
    return RxNormResult(None, drug_name, 0.0)
