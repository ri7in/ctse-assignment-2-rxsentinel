"""Patient Communicator — Sachila. Initial draft without readability loop."""
from __future__ import annotations

from rxsentinel.config import settings
from rxsentinel.llm import get_ollama_client
from rxsentinel.schemas import Interaction, SeveritySummary
from rxsentinel.state import RxState


SYSTEM_PROMPT = """You write plain-English medication summaries for patients.
Use simple words. Use 'you' not 'patient'. End with: 'Talk to your doctor or pharmacist'.
"""


async def patient_communicator(state: RxState) -> RxState:
    interactions: list = list(state.get("interactions", []))
    summary = state.get("severity_summary") or SeveritySummary()
    if isinstance(summary, dict):
        summary = SeveritySummary(**summary)

    lines = [f"- {i.drug_a_name} + {i.drug_b_name}: {i.clinical_effect}" for i in interactions]
    user_prompt = "Findings:\n" + ("\n".join(lines) if lines else "(none)")

    client = get_ollama_client()
    try:
        draft = await client.chat_text(SYSTEM_PROMPT, user_prompt, temperature=settings.temp_communicator)
    except Exception:
        return {"patient_summary": "Could not generate summary.", "readability_grade": 0.0, "rewrites_applied": 0}

    return {"patient_summary": draft.strip(), "readability_grade": 0.0, "rewrites_applied": 0}
