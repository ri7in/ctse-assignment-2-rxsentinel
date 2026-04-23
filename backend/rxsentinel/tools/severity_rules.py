"""Severity rules — owned by Shehan (Interaction Analyzer support).

Provides the ordering and promotion rules that the Interaction Analyzer
uses to combine evidence from the local DB and openFDA. Centralizing this
here makes the rules easy to test in isolation and to extend without
touching the analyzer agent code.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Severity = Literal["high", "moderate", "low"]


_RANK: dict[Severity, int] = {"high": 0, "moderate": 1, "low": 2}


@dataclass(frozen=True)
class SeverityDecision:
    """Outcome of a severity reconciliation between two evidence sources."""

    severity: Severity
    promoted: bool   # True if openFDA evidence raised the local-DB severity
    reason: str


def severity_rank(s: Severity) -> int:
    """Return the integer rank of a severity (lower = more severe)."""
    return _RANK[s]


def is_more_severe(a: Severity, b: Severity) -> bool:
    """Return True if a is strictly more severe than b."""
    return _RANK[a] < _RANK[b]


def reconcile(local: Severity, fda_serious_signal: float) -> SeverityDecision:
    """Decide the final severity by combining local DB + openFDA signal.

    Args:
        local: Severity assigned by the curated local interactions DB.
        fda_serious_signal: A value in [0, 1] where higher means more
            serious-outcome reports per total reports for the drug pair.

    Returns:
        SeverityDecision with the final severity and reason.

    Examples:
        >>> reconcile("low", 0.0).severity
        'low'
        >>> reconcile("low", 0.07).severity     # signal > 5% promotes to moderate
        'moderate'
        >>> reconcile("high", 0.5).severity     # already high, never promoted
        'high'
    """
    # Already at the most severe tier — nothing to promote.
    if local == "high":
        return SeverityDecision("high", False, "local DB already classifies as high")

    if fda_serious_signal > 0.05 and local == "low":
        return SeverityDecision(
            "moderate",
            True,
            f"openFDA serious-outcome rate {fda_serious_signal:.0%} promotes low->moderate",
        )

    if fda_serious_signal > 0.20 and local == "moderate":
        return SeverityDecision(
            "high",
            True,
            f"openFDA serious-outcome rate {fda_serious_signal:.0%} promotes moderate->high",
        )

    return SeverityDecision(local, False, "local DB severity preserved")
