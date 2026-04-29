"""Unit tests for readability_grader — Sachila's tool."""
from __future__ import annotations

import pytest

from rxsentinel.tools.readability_grader import (
    count_syllables,
    flesch_kincaid_grade,
    split_sentences,
    split_words,
)


class TestSyllableCount:
    @pytest.mark.parametrize(
        "word,min_count,max_count",
        [
            ("cat", 1, 1),
            ("apple", 2, 2),
            ("medication", 4, 4),
            ("interaction", 4, 4),
            ("pharmacy", 3, 3),
            ("a", 1, 1),
            ("", 0, 0),
        ],
    )
    def test_known_words(self, word: str, min_count: int, max_count: int) -> None:
        assert min_count <= count_syllables(word) <= max_count


class TestSplitters:
    def test_split_sentences_basic(self) -> None:
        s = "First. Second! Third? Fourth."
        out = split_sentences(s)
        assert len(out) == 4

    def test_split_words_alpha_only(self) -> None:
        out = split_words("Take 2 aspirin for pain.")
        assert "aspirin" in out
        assert "2" not in out


class TestFleschKincaid:
    def test_simple_text_low_grade(self) -> None:
        text = "The cat sat on the mat. It was a hot day."
        grade = flesch_kincaid_grade(text)
        assert grade < 4.0, f"expected low grade, got {grade}"

    def test_complex_text_high_grade(self) -> None:
        text = (
            "Pharmacokinetic interactions between concomitantly administered "
            "anticoagulants and nonsteroidal antiinflammatory medications "
            "potentiate hemorrhagic complications via cytochrome P450 inhibition."
        )
        grade = flesch_kincaid_grade(text)
        assert grade > 12.0, f"expected high grade, got {grade}"

    def test_empty_returns_zero(self) -> None:
        assert flesch_kincaid_grade("") == 0.0
        assert flesch_kincaid_grade("   ") == 0.0

    def test_property_higher_word_count_higher_grade(self) -> None:
        """Longer sentences with same vocabulary should generally score higher."""
        short = "I run. You walk."
        long = "I run very quickly through the park while you walk slowly."
        assert flesch_kincaid_grade(long) >= flesch_kincaid_grade(short)
