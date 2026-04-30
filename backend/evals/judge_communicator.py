"""LLM-as-Judge for the Patient Communicator agent — Sachila.

Validates that the Communicator produces plain-English summaries at or below
6th-grade reading level, never gives direct medical advice, and preserves
every clinical fact and severity level from its input.
"""
from __future__ import annotations

import asyncio
import json

from rxsentinel.agents.patient_communicator import patient_communicator
from rxsentinel.schemas import Interaction, Medication, SeveritySummary

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
        name="single-high-interaction",
        input={
            "parsed_medications": [
                _med("warfarin", "29046"),
                _med("ibuprofen", "5640"),
            ],
            "interactions": [
                Interaction(
                    drug_a="29046", drug_b="5640",
                    drug_a_name="warfarin", drug_b_name="ibuprofen",
                    severity="high",
                    mechanism="additive bleeding risk plus CYP2C9 inhibition",
                    clinical_effect="major hemorrhage",
                    recommendation="avoid combination",
                    source=["local-db"],
                )
            ],
            "severity_summary": SeveritySummary(high=1, moderate=0, low=0),
        },
        expected={"contains_warning": True, "max_grade": 8.0},
    ),
    Case(
        name="no-interactions",
        input={
            "parsed_medications": [_med("acetaminophen", "1191")],
            "interactions": [],
            "severity_summary": SeveritySummary(),
        },
        expected={"reassuring": True, "max_grade": 8.0},
    ),
]


RUBRIC = """The Patient Communicator output must:
- Be plain English (6th-grade reading level, max 8th-grade tolerated).
- Use "you" rather than "the patient" or "subjects".
- End with: "Talk to your doctor or pharmacist before changing any medicines."
- Translate ALL medical jargon (e.g., "QT prolongation" -> "irregular heartbeat").
- Preserve every severity warning from the input.
- Never give direct medical advice (no "stop taking X").
- Never use scare tactics — be calm, factual, and clear.
- For empty interactions, be reassuring without being dismissive.
"""


async def runner(case: Case) -> tuple[str, str]:
    state = {
        "request_id": f"judge-comm-{case.name}",
        **case.input,
    }
    out = await patient_communicator(state)
    return (
        json.dumps({
            "interactions": [i.model_dump() for i in case.input["interactions"]],
            "severity_summary": case.input["severity_summary"].model_dump(),
        }),
        out.get("patient_summary", ""),
    )


async def run() -> None:
    results = await run_judge_suite("communicator", CASES, runner, RUBRIC)
    print_summary("Patient Communicator", results)


if __name__ == "__main__":
    main_dispatch(run)
