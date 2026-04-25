"""Interaction Analyzer agent — owned by Shehan.

For every unique pair of parsed medications, queries the curated local
interactions DB AND the openFDA adverse-event endpoint. Combines the
evidence and returns a structured list of `Interaction` records, plus a
severity summary.
"""
from __future__ import annotations

import asyncio
from itertools import combinations
from typing import cast

from rxsentinel.schemas import Interaction, Medication, SeveritySummary
from rxsentinel.state import RxState
from rxsentinel.tools import check_interaction
from rxsentinel.tools.interaction_checker import (
    InteractionRecord,
    severity_summary,
)
from rxsentinel.tracing import tool_event, traced


@traced("interaction_analyzer")
async def interaction_analyzer(state: RxState) -> RxState:
    """Find drug-drug interactions across all parsed medications.

    Builds the list of unique drug pairs (skipping any without an RxCUI),
    queries `check_interaction` for each pair in parallel, then folds the
    results into typed `Interaction` records.

    Args:
        state: State with `parsed_medications` set.

    Returns:
        Partial state with `interactions` and `severity_summary`.
    """
    request_id = state["request_id"]
    meds: list[Medication] = list(state.get("parsed_medications", []))
    pairs = [
        (a, b)
        for a, b in combinations(meds, 2)
        if a.rxcui and b.rxcui and a.rxcui != b.rxcui
    ]

    async with tool_event(
        request_id, "interaction_analyzer", "build_pairs",
        {"medication_count": len(meds), "pair_count": len(pairs)},
    ) as ctx:
        ctx["result"] = {"pairs_to_check": len(pairs)}

    async def check_pair(med_a: Medication, med_b: Medication) -> list[InteractionRecord]:
        async with tool_event(
            request_id,
            "interaction_analyzer",
            "check_interaction",
            {"a": med_a.normalized_name, "b": med_b.normalized_name},
        ) as ctx_inner:
            try:
                records = await check_interaction(
                    cast(str, med_a.rxcui), cast(str, med_b.rxcui)
                )
                ctx_inner["result"] = {"hits": len(records)}
                return records
            except Exception as e:  # noqa: BLE001
                ctx_inner["result"] = {"error": str(e)}
                return []

    results = await asyncio.gather(*(check_pair(a, b) for a, b in pairs))
    flat: list[InteractionRecord] = [r for sub in results for r in sub]

    interactions = [
        Interaction(
            drug_a=r.rxcui_a,
            drug_b=r.rxcui_b,
            drug_a_name=r.name_a,
            drug_b_name=r.name_b,
            severity=r.severity,
            mechanism=r.mechanism,
            clinical_effect=r.clinical_effect,
            recommendation=r.recommendation,
            source=r.sources,
        )
        for r in flat
    ]

    summary = SeveritySummary(**severity_summary(flat))

    return {"interactions": interactions, "severity_summary": summary}
