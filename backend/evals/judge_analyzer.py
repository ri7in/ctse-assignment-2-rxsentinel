"""LLM-as-Judge for the Interaction Analyzer agent — Shehan.

Validates that the Analyzer correctly identifies known severe pairs, never
invents a mechanism beyond what tool data provides, and assigns proper severity.
"""
from __future__ import annotations

import asyncio
import json

from rxsentinel.agents.interaction_analyzer import interaction_analyzer
from rxsentinel.schemas import Medication

from evals._judge import (
    Case,
    main_dispatch,
    print_summary,
    run_judge_suite,
)


def _med(name: str, rxcui: str) -> Medication:
    return Medication(
        raw_term=name, normalized_name=name, rxcui=rxcui,
        dose=None, frequency=None, route=None, confidence=1.0,
    )


CASES = [
    Case(
        name="warfarin-ibuprofen-known-severe",
        input=[_med("warfarin", "29046"), _med("ibuprofen", "5640")],
        expected={"min_high": 1, "must_include_pair": ("warfarin", "ibuprofen")},
    ),
    Case(
        name="metformin-warfarin-low",
        input=[_med("metformin", "6809"), _med("warfarin", "29046")],
        expected={"max_severity": "low"},
    ),
    Case(
        name="three-meds-with-amiodarone",
        input=[
            _med("amiodarone", "1551"),
            _med("warfarin", "29046"),
            _med("digoxin", "3443"),
        ],
        expected={"min_high": 2},
    ),
    Case(
        name="single-med-no-pairs",
        input=[_med("metformin", "6809")],
        expected={"interaction_count": 0},
    ),
]


RUBRIC = """The Analyzer output must:
- Be valid JSON with "interactions" (list) and "severity_summary" (dict).
- Each interaction must have: drug_a, drug_b, drug_a_name, drug_b_name,
  severity (high|moderate|low), mechanism, clinical_effect, recommendation, source.
- NEVER fabricate a mechanism beyond what tool data supports.
- Known severe pairs (e.g., warfarin+ibuprofen, amiodarone+warfarin) must be
  flagged "high".
- Single-medication input must produce ZERO interactions.
- Severity summary counts must match the actual interaction list.
"""


async def runner(case: Case) -> tuple[str, str]:
    state = {
        "request_id": f"judge-analyzer-{case.name}",
        "parsed_medications": case.input,
    }
    out = await interaction_analyzer(state)
    summary = out.get("severity_summary")
    return (
        json.dumps([m.model_dump() for m in case.input]),
        json.dumps({
            "interactions": [i.model_dump() for i in out.get("interactions", [])],
            "severity_summary": summary.model_dump() if summary else {},
        }),
    )


async def run() -> None:
    results = await run_judge_suite("analyzer", CASES, runner, RUBRIC)
    print_summary("Interaction Analyzer", results)


if __name__ == "__main__":
    main_dispatch(run)
