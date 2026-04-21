"""RxNorm lookup — Thusala. Adds approximate-term fallback for misspellings."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx
from rapidfuzz import fuzz

from rxsentinel.config import settings


@dataclass
class RxNormResult:
    rxcui: str | None
    canonical_name: str
    confidence: float
    alternatives: list = field(default_factory=list)
    source: str = "none"


async def rxnorm_lookup(drug_name: str, *, fuzzy: bool = True) -> RxNormResult:
    """Resolve a drug name with exact match, then fuzzy fallback."""
    if not drug_name or not drug_name.strip():
        return RxNormResult(None, "", 0.0)

    name = drug_name.strip()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.rxnorm_base_url}/rxcui.json",
            params={"name": name}, timeout=settings.http_timeout,
        )
        resp.raise_for_status()
        ids = resp.json().get("idGroup", {}).get("rxnormId") or []
        if ids:
            return RxNormResult(ids[0], name.lower(), 1.0, source="exact")

        if not fuzzy:
            return RxNormResult(None, name, 0.0)

        resp = await client.get(
            f"{settings.rxnorm_base_url}/approximateTerm.json",
            params={"term": name, "maxEntries": 5},
            timeout=settings.http_timeout,
        )
        resp.raise_for_status()
        candidates = resp.json().get("approximateGroup", {}).get("candidate") or []

    if not candidates:
        return RxNormResult(None, name, 0.0)

    top = candidates[0]
    rxcui = str(top.get("rxcui") or "") or None
    canonical = str(top.get("name") or name).lower()
    api_score = float(top.get("score") or 0) / 100
    fuzz_score = fuzz.ratio(name.lower(), canonical) / 100
    confidence = round(0.6 * api_score + 0.4 * fuzz_score, 2)
    return RxNormResult(
        rxcui=rxcui, canonical_name=canonical, confidence=confidence,
        alternatives=[{"rxcui": c.get("rxcui"), "name": c.get("name")} for c in candidates[1:5]],
        source="approximate",
    )
