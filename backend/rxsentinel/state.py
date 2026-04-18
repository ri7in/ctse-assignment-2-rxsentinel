"""LangGraph state — the single TypedDict that flows through the pipeline.

Each agent reads what it needs and writes ONLY its own keys. LangGraph merges
returned partial-states automatically.
"""
from __future__ import annotations

from typing import TypedDict

from rxsentinel.schemas import (
    FinalReport,
    Interaction,
    Medication,
    SeveritySummary,
    TraceEvent,
)


class RxState(TypedDict, total=False):
    """Global state passed between every node in the LangGraph."""

    # Inputs
    raw_input: str
    request_id: str
    started_at: str  # ISO-8601

    # Coordinator (validation pass)
    is_valid: bool
    validation_errors: list[str]
    decision: str  # "proceed" | "halt"

    # Parser
    parsed_medications: list[Medication]
    unparsed_terms: list[str]

    # Analyzer
    interactions: list[Interaction]
    severity_summary: SeveritySummary

    # Communicator
    patient_summary: str
    readability_grade: float
    rewrites_applied: int

    # Final report (assembled by Coordinator)
    final_report: FinalReport

    # Observability (append-only)
    trace: list[TraceEvent]
