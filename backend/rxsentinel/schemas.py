"""Pydantic schemas — single source of truth for data shapes across agents."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Severity = Literal["high", "moderate", "low"]


class Medication(BaseModel):
    """A single normalized medication record produced by the Parser agent."""

    raw_term: str = Field(..., description="Original term as written by user")
    normalized_name: str = Field(..., description="Canonical name (often the RxNorm name)")
    rxcui: str | None = Field(None, description="RxNorm Concept Unique Identifier")
    dose: str | None = None
    frequency: str | None = None
    route: str | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)


class Interaction(BaseModel):
    """A drug-drug interaction record produced by the Analyzer agent."""

    drug_a: str  # rxcui
    drug_b: str
    drug_a_name: str
    drug_b_name: str
    severity: Severity
    mechanism: str
    clinical_effect: str
    recommendation: str
    source: list[str]  # ["openFDA", "local-db", ...]


class SeveritySummary(BaseModel):
    high: int = 0
    moderate: int = 0
    low: int = 0


class TraceEvent(BaseModel):
    """One step in the agent run, written to JSONL trace and streamed via SSE."""

    ts: datetime
    agent: str
    event_type: Literal["enter", "exit", "tool_call", "tool_result", "error", "llm_token"]
    payload: dict
    duration_ms: float | None = None
    request_id: str


class FinalReport(BaseModel):
    """The structured response delivered to the frontend."""

    request_id: str
    started_at: datetime
    completed_at: datetime
    duration_ms: float
    medications: list[Medication]
    unparsed_terms: list[str]
    interactions: list[Interaction]
    severity_summary: SeveritySummary
    patient_summary: str
    readability_grade: float
    limitations: list[str] = Field(
        default_factory=lambda: [
            "RxSentinel is an educational decision-support tool and does not replace professional medical advice.",
            "Coverage of interactions depends on RxNorm and openFDA data quality.",
            "Local SLM may occasionally produce inaccurate output; always confirm with a clinician.",
        ]
    )
