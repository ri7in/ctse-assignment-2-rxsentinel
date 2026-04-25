"""Interaction Analyzer — Shehan. Sequential pair check (slower baseline)."""
from __future__ import annotations

from itertools import combinations

from rxsentinel.schemas import Interaction, Medication, SeveritySummary
from rxsentinel.state import RxState
from rxsentinel.tools import check_interaction
from rxsentinel.tools.interaction_checker import severity_summary


async def interaction_analyzer(state: RxState) -> RxState:
    meds: list = list(state.get("parsed_medications", []))
    flat = []
    for a, b in combinations(meds, 2):
        if not (a.rxcui and b.rxcui and a.rxcui != b.rxcui):
            continue
        try:
            recs = await check_interaction(a.rxcui, b.rxcui)
            flat.extend(recs)
        except Exception:
            continue

    interactions = [
        Interaction(
            drug_a=r.rxcui_a, drug_b=r.rxcui_b,
            drug_a_name=r.name_a, drug_b_name=r.name_b,
            severity=r.severity, mechanism=r.mechanism,
            clinical_effect=r.clinical_effect, recommendation=r.recommendation,
            source=r.sources,
        ) for r in flat
    ]
    summary = SeveritySummary(**severity_summary(flat))
    return {"interactions": interactions, "severity_summary": summary}
