"""Unit tests for dose_normalizer — Thusala's tool."""
from __future__ import annotations

import pytest

from rxsentinel.tools.dose_normalizer import normalize_dose


class TestKnownDoses:
    @pytest.mark.parametrize(
        "text,expected_value,expected_unit",
        [
            ("500mg", 500.0, "mg"),
            ("500 mg", 500.0, "mg"),
            ("0.5 g", 0.5, "g"),
            ("250mcg", 250.0, "mcg"),
            ("10 ml", 10.0, "ml"),
            ("100 IU", 100.0, "iu"),
            ("1 tablet", 1.0, "tablet"),
        ],
    )
    def test_parses(self, text: str, expected_value: float, expected_unit: str) -> None:
        out = normalize_dose(text)
        assert out is not None
        assert out.value == expected_value
        assert out.unit == expected_unit


class TestMgEquivalence:
    def test_g_to_mg(self) -> None:
        assert normalize_dose("0.5 g").mg_equivalent == 500.0

    def test_mcg_to_mg(self) -> None:
        assert normalize_dose("250mcg").mg_equivalent == 0.25

    def test_ml_no_mg(self) -> None:
        # Volume units have no mg equivalent.
        assert normalize_dose("10 ml").mg_equivalent is None


class TestNoMatch:
    @pytest.mark.parametrize("text", ["", "as needed", "two tablets", None])
    def test_returns_none(self, text: str | None) -> None:
        # type: ignore[arg-type]
        assert normalize_dose(text) is None  # type: ignore[arg-type]
