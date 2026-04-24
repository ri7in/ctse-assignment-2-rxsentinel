"""Unit tests for severity_rules — Shehan's tool."""
from __future__ import annotations

import pytest

from rxsentinel.tools.severity_rules import (
    is_more_severe,
    reconcile,
    severity_rank,
)


class TestRanking:
    def test_high_is_lowest_rank(self) -> None:
        assert severity_rank("high") == 0

    def test_more_severe_helper(self) -> None:
        assert is_more_severe("high", "moderate")
        assert is_more_severe("moderate", "low")
        assert not is_more_severe("low", "high")


class TestReconcile:
    def test_high_never_promoted(self) -> None:
        decision = reconcile("high", 0.99)
        assert decision.severity == "high"
        assert decision.promoted is False

    def test_low_promotes_to_moderate_at_threshold(self) -> None:
        # Just above 5% threshold.
        d = reconcile("low", 0.07)
        assert d.severity == "moderate"
        assert d.promoted is True

    def test_low_stays_low_below_threshold(self) -> None:
        d = reconcile("low", 0.02)
        assert d.severity == "low"
        assert d.promoted is False

    def test_moderate_promotes_to_high_at_high_signal(self) -> None:
        d = reconcile("moderate", 0.25)
        assert d.severity == "high"
        assert d.promoted is True

    def test_moderate_stays_moderate_below_high_threshold(self) -> None:
        d = reconcile("moderate", 0.10)
        assert d.severity == "moderate"
        assert d.promoted is False
