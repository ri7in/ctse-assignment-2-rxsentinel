"""Med Parser — Thusala. Sequential rxnorm lookups (slower)."""
from __future__ import annotations

from typing import Any

from rxsentinel.config import settings
from rxsentinel.llm import get_ollama_client
from rxsentinel.schemas import Medication
from rxsentinel.state import RxState
from rxsentinel.tools import rxnorm_lookup


SYSTEM_PROMPT = """You parse medications.
For each medication, extract: drug name, dose, frequency, route.
Output ONLY: {"candidates": [{"raw_term","normalized_name","dose","frequency","route"}]}
"""


async def med_parser(state: RxState) -> RxState:
    raw_input = state["raw_input"]
    client = get_ollama_client()
    try:
        llm_out = await client.chat_json(SYSTEM_PROMPT, raw_input, temperature=settings.temp_parser)
    except Exception:
        return {"parsed_medications": [], "unparsed_terms": [raw_input]}

    medications: list = []
    unparsed: list = []
    for cand in llm_out.get("candidates", []):
        name = (cand.get("normalized_name") or cand.get("raw_term") or "").strip()
        if not name:
            unparsed.append(cand.get("raw_term") or "unknown")
            continue
        try:
            rx = await rxnorm_lookup(name)
            medications.append(Medication(
                raw_term=cand.get("raw_term", name),
                normalized_name=rx.canonical_name or name,
                rxcui=rx.rxcui, dose=cand.get("dose"),
                frequency=cand.get("frequency"), route=cand.get("route"),
                confidence=rx.confidence,
            ))
        except Exception:
            unparsed.append(cand.get("raw_term", name))
    return {"parsed_medications": medications, "unparsed_terms": unparsed}
