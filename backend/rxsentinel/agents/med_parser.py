"""Medication Parser agent — owned by Thusala.

Converts free-text medication lists into structured `Medication` records.
Calls the RxNorm API via `rxnorm_lookup` — never fabricates RxCUI codes.
"""
from __future__ import annotations

import asyncio
from typing import Any

from pydantic import ValidationError

from rxsentinel.config import settings
from rxsentinel.llm import get_ollama_client
from rxsentinel.schemas import Medication
from rxsentinel.state import RxState
from rxsentinel.tools import rxnorm_lookup
from rxsentinel.tracing import tool_event, traced


SYSTEM_PROMPT = """You are the Medication Parser of RxSentinel.

Convert the user's messy medication list into a structured array of records.
For EACH medication mentioned, extract: drug name, dose, frequency, route.

Output ONLY valid JSON:
{
  "candidates": [
    {
      "raw_term": "<original substring as the user wrote it>",
      "normalized_name": "<your best guess at the canonical drug name>",
      "dose": "<dose if stated, else null>",
      "frequency": "<schedule if stated, else null>",
      "route": "<oral|topical|iv|inhaled|other if stated, else null>"
    }
  ]
}

Rules:
- Handle brand names (Tylenol -> acetaminophen).
- Handle obvious misspellings (metfromin -> metformin).
- For lay descriptions like "the blue pill for blood pressure" you may
  GUESS a normalized_name but it will be flagged with low confidence.
- Combination drugs like "amox-clav" -> two records (amoxicillin + clavulanate).
- Output JSON only. No prose, no preamble.
"""


@traced("med_parser")
async def med_parser(state: RxState) -> RxState:
    """Parse free-text medications into normalized records.

    1. Calls the LLM to split + extract candidates from the raw input.
    2. For each candidate, calls `rxnorm_lookup` to assign an RxCUI.
    3. Returns a list of `Medication` records + any unparsed terms.

    Args:
        state: State with `raw_input` and `request_id`.

    Returns:
        Partial state with `parsed_medications` and `unparsed_terms`.
    """
    request_id = state["request_id"]
    raw_input = state["raw_input"]

    client = get_ollama_client()

    async with tool_event(
        request_id, "med_parser", "ollama_chat_json", {"chars": len(raw_input)}
    ) as ctx:
        try:
            llm_out = await client.chat_json(
                system=SYSTEM_PROMPT,
                user=raw_input,
                temperature=settings.temp_parser,
            )
            ctx["result"] = {"candidate_count": len(llm_out.get("candidates", []))}
        except Exception as e:  # noqa: BLE001
            ctx["result"] = {"error": str(e)}
            return {"parsed_medications": [], "unparsed_terms": [raw_input]}

    candidates = llm_out.get("candidates", [])
    medications: list[Medication] = []
    unparsed: list[str] = []

    # Parallel RxNorm lookups for speed.
    async def resolve_one(cand: dict[str, Any]) -> Medication | str:
        name = (cand.get("normalized_name") or cand.get("raw_term") or "").strip()
        if not name:
            return cand.get("raw_term") or "unknown"
        async with tool_event(
            request_id, "med_parser", "rxnorm_lookup", {"name": name}
        ) as ctx_inner:
            try:
                rx = await rxnorm_lookup(name)
                ctx_inner["result"] = {"rxcui": rx.rxcui, "confidence": rx.confidence}
            except Exception:  # noqa: BLE001
                return cand.get("raw_term") or name

        try:
            return Medication(
                raw_term=cand.get("raw_term", name),
                normalized_name=rx.canonical_name or name,
                rxcui=rx.rxcui,
                dose=cand.get("dose"),
                frequency=cand.get("frequency"),
                route=cand.get("route"),
                confidence=rx.confidence,
            )
        except ValidationError:
            return cand.get("raw_term", name)

    resolved = await asyncio.gather(*(resolve_one(c) for c in candidates))
    for r in resolved:
        if isinstance(r, Medication):
            medications.append(r)
        else:
            unparsed.append(r)

    return {"parsed_medications": medications, "unparsed_terms": unparsed}
