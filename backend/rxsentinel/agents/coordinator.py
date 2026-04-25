"""Coordinator — Rivin. Validate-only first cut."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from rxsentinel.state import RxState
from rxsentinel.tools import validate_initial_state


async def coordinator_validate(state: RxState) -> RxState:
    """Entry node — validate input, decide proceed/halt."""
    request_id = state.get("request_id") or str(uuid.uuid4())
    started_at = state.get("started_at") or datetime.now(UTC).isoformat()
    raw = state.get("raw_input", "")
    rule_check = validate_initial_state(raw)
    return {
        "request_id": request_id,
        "started_at": started_at,
        "is_valid": rule_check.is_valid,
        "validation_errors": rule_check.errors,
        "decision": "proceed" if rule_check.is_valid else "halt",
    }


def should_continue(state: RxState) -> str:
    return "halt" if state.get("decision") == "halt" else "parser"
