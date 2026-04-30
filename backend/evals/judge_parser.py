"""LLM-as-Judge for the Medication Parser agent — Thusala.

Validates that the Parser correctly normalizes brand names, handles misspellings,
and never fabricates RxCUI codes (it must come from the rxnorm tool).
"""
from __future__ import annotations

import asyncio
import json

from rxsentinel.agents.med_parser import med_parser

from evals._judge import (
    Case,
    main_dispatch,
    print_summary,
    run_judge_suite,
)


CASES = [
    Case(
        name="brand-name",
        input="Tylenol 500mg PRN",
        expected={"normalized_name_contains": "acetaminophen"},
    ),
    Case(
        name="generic-name",
        input="metformin 500mg twice daily",
        expected={"normalized_name_contains": "metformin"},
    ),
    Case(
        name="misspelling",
        input="metfromin 500mg",
        expected={"normalized_name_contains": "metformin"},
    ),
    Case(
        name="multiple-medications",
        input="warfarin 5mg, ibuprofen 400mg, lisinopril 10mg",
        expected={"min_count": 3},
    ),
    Case(
        name="lay-description",
        input="the blue pill for blood pressure",
        expected={"low_confidence": True},
    ),
]


RUBRIC = """The Parser output must:
- Be valid JSON containing a "parsed_medications" list.
- For each medication: include raw_term, normalized_name, rxcui, and confidence.
- NEVER fabricate an rxcui — it should be a real string number or null.
- Brand names (Tylenol) should map to generic name (acetaminophen).
- Common misspellings should still produce a confident match.
- Lay descriptions should result in low confidence (<0.6) or null rxcui.
- Multiple medications in input should produce multiple entries.
"""


async def runner(case: Case) -> tuple[str, str]:
    state = {
        "raw_input": case.input,
        "request_id": f"judge-parser-{case.name}",
    }
    out = await med_parser(state)
    return case.input, json.dumps(
        {"parsed_medications": [m.model_dump() for m in out.get("parsed_medications", [])],
         "unparsed_terms": out.get("unparsed_terms", [])}
    )


async def run() -> None:
    results = await run_judge_suite("parser", CASES, runner, RUBRIC)
    print_summary("Med Parser", results)


if __name__ == "__main__":
    main_dispatch(run)
