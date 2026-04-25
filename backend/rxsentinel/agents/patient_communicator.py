"""Patient Communicator agent — owned by Sachila.

Reads the structured Interactions and writes a calm, plain-English summary
for the patient. Uses the readability grader to ensure output stays at or
below a 6th-grade reading level — re-running the simplifier if the first
draft scores too high.
"""
from __future__ import annotations

from rxsentinel.config import settings
from rxsentinel.llm import get_ollama_client
from rxsentinel.schemas import Interaction, Medication, SeveritySummary
from rxsentinel.state import RxState
from rxsentinel.tools import flesch_kincaid_grade, simplify_text
from rxsentinel.tracing import tool_event, traced


SYSTEM_PROMPT = """You are the Patient Communicator of RxSentinel.

Your audience: an adult patient with no medical training.

Your job: take the technical interaction list and write a calm, clear summary
they can actually use. Plain English. 6th-grade reading level. Short sentences.

Structure (use these exact section headings):
1. **Overall summary** — one sentence on what we found.
2. **Red flags** — high severity items. What to do TODAY.
3. **Yellow flags** — moderate severity. What to monitor.
4. **Green flags** — low severity items or reassurance.
5. **What to do next** — always say: "Talk to your doctor or pharmacist before changing any medicines."

Rules:
- Translate jargon. "QT prolongation" -> "could cause an irregular heartbeat".
- Use "you", not "the patient".
- Never say "consult a healthcare professional" — say "talk to your doctor or pharmacist".
- Be honest, not alarmist. No scare tactics.
- Output ONLY the summary text. No JSON, no preamble.
"""


def _format_interactions_for_prompt(interactions: list[Interaction]) -> str:
    if not interactions:
        return "No drug-drug interactions were found."
    lines = []
    for i in interactions:
        lines.append(
            f"- [{i.severity.upper()}] {i.drug_a_name} + {i.drug_b_name}: "
            f"{i.clinical_effect}. Mechanism: {i.mechanism}. "
            f"Recommendation: {i.recommendation}."
        )
    return "\n".join(lines)


def _format_meds_for_prompt(meds: list[Medication]) -> str:
    if not meds:
        return "(no medications parsed)"
    return "\n".join(
        f"- {m.normalized_name}"
        + (f" {m.dose}" if m.dose else "")
        + (f" {m.frequency}" if m.frequency else "")
        for m in meds
    )


@traced("patient_communicator")
async def patient_communicator(state: RxState) -> RxState:
    """Produce a patient-friendly summary of the interaction findings.

    Workflow:
        1. Build a compact prompt from the structured interactions list.
        2. Call the LLM (warmer temperature than the analytic agents) to draft
           a summary.
        3. Grade the draft with Flesch-Kincaid.
        4. If grade > 6.0, run `simplify_text` to rewrite (max 3 attempts).

    Args:
        state: State with `interactions`, `parsed_medications`,
            `severity_summary`.

    Returns:
        Partial state with `patient_summary`, `readability_grade`,
        `rewrites_applied`.
    """
    request_id = state["request_id"]
    interactions: list[Interaction] = list(state.get("interactions", []))
    meds: list[Medication] = list(state.get("parsed_medications", []))
    summary = state.get("severity_summary") or SeveritySummary()
    if isinstance(summary, dict):
        summary = SeveritySummary(**summary)

    user_prompt = (
        f"Medications reviewed:\n{_format_meds_for_prompt(meds)}\n\n"
        f"Interactions found ({summary.high} high, {summary.moderate} moderate, "
        f"{summary.low} low):\n{_format_interactions_for_prompt(interactions)}"
    )

    client = get_ollama_client()

    async with tool_event(
        request_id, "patient_communicator", "ollama_chat_text",
        {"interaction_count": len(interactions)},
    ) as ctx:
        try:
            draft = await client.chat_text(
                system=SYSTEM_PROMPT,
                user=user_prompt,
                temperature=settings.temp_communicator,
            )
            ctx["result"] = {"draft_chars": len(draft)}
        except Exception as e:  # noqa: BLE001
            ctx["result"] = {"error": str(e)}
            return {
                "patient_summary": "We could not generate a summary right now. "
                "Please try again, and talk to your doctor or pharmacist.",
                "readability_grade": 0.0,
                "rewrites_applied": 0,
            }

    draft = draft.strip()
    initial_grade = flesch_kincaid_grade(draft)

    async with tool_event(
        request_id, "patient_communicator", "flesch_kincaid_grade",
        {"draft_grade": initial_grade},
    ) as ctx2:
        ctx2["result"] = {"grade": initial_grade}

    rewrites = 0
    final_text = draft
    final_grade = initial_grade

    if initial_grade > 8.0:
        async with tool_event(
            request_id, "patient_communicator", "simplify_text",
            {"target_grade": 6.0},
        ) as ctx3:
            try:
                simp = await simplify_text(draft, target_grade=6.0, max_iterations=3)
                final_text = simp.simplified_text or draft
                final_grade = simp.final_grade
                rewrites = simp.iterations_used
                ctx3["result"] = {
                    "iterations": simp.iterations_used,
                    "final_grade": simp.final_grade,
                    "target_met": simp.target_met,
                }
            except Exception as e:  # noqa: BLE001
                ctx3["result"] = {"error": str(e)}

    return {
        "patient_summary": final_text,
        "readability_grade": final_grade,
        "rewrites_applied": rewrites,
    }
