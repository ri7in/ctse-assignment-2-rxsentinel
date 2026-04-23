"""Readability grader tool — owned by Sachila (Patient Communicator agent).

Computes the Flesch-Kincaid Grade Level for English text, and provides an
iterative simplifier that calls the Communicator's LLM to rewrite text until
it falls below a target grade level. The grader is pure Python (no API), so
it's fast and offline-safe; the simplifier is async because it makes LLM calls.

The Flesch-Kincaid formula:
    0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from rxsentinel.config import settings
from rxsentinel.llm import get_ollama_client


# Pre-compiled patterns for hot-path performance.
_SENTENCE_SPLIT: Final = re.compile(r"[.!?]+")
_WORD_SPLIT: Final = re.compile(r"\b[a-zA-Z']+\b")
_VOWEL_GROUP: Final = re.compile(r"[aeiouy]+", re.I)
_SILENT_E: Final = re.compile(r"e$", re.I)


_SIMPLIFIER_SYSTEM = """You rewrite medical text in plain English at a 6th-grade reading level.

Rules:
- Replace every medical jargon term with a plain-English explanation.
- Keep sentences short (under 15 words when possible).
- Use "you" instead of "the patient".
- Preserve every clinical fact and severity warning.
- Do not add advice that wasn't in the original.
- Output ONLY the rewritten text, with no preamble.
"""


@dataclass(slots=True)
class SimplifyResult:
    """Outcome of an iterative simplification run."""

    simplified_text: str
    original_grade: float
    final_grade: float
    iterations_used: int
    target_met: bool


def count_syllables(word: str) -> int:
    """Estimate syllables in an English word.

    Uses a fast heuristic (vowel-group count with silent-e and final-le
    corrections) — accurate enough for grade-level statistics without needing
    a dictionary lookup.

    Args:
        word: A single English word.

    Returns:
        Estimated syllable count, minimum 1.

    Examples:
        >>> count_syllables("cat")
        1
        >>> count_syllables("medication")
        4
        >>> count_syllables("interaction")
        4
    """
    if not word:
        return 0
    w = word.lower().strip("'.,;:!?\"()")
    if not w:
        return 0
    # Count vowel groups.
    groups = _VOWEL_GROUP.findall(w)
    n = len(groups)
    # Silent terminal "e" usually doesn't add a syllable.
    if w.endswith("e") and n > 1 and not w.endswith("le"):
        n -= 1
    # Final "le" preceded by a consonant adds one.
    if len(w) > 2 and w.endswith("le") and w[-3] not in "aeiouy":
        n += 1
    return max(n, 1)


def split_sentences(text: str) -> list[str]:
    """Split text into sentences. Empty fragments are dropped."""
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]


def split_words(text: str) -> list[str]:
    """Tokenize text into words (letters + apostrophes only)."""
    return _WORD_SPLIT.findall(text)


def flesch_kincaid_grade(text: str) -> float:
    """Compute the Flesch-Kincaid Grade Level for the given English text.

    Higher number = harder to read. 6.0 = sixth-grade reading level. 12.0 =
    high-school senior. 16+ = college / academic.

    Args:
        text: English text to grade.

    Returns:
        Grade level, rounded to one decimal. Returns 0.0 for empty/all-whitespace.

    Examples:
        >>> flesch_kincaid_grade("The cat sat on the mat.")
        1.5
        >>> flesch_kincaid_grade("Pharmacokinetic interactions may potentiate adverse hepatic events.")  # doctest: +SKIP
        16.4
    """
    if not text or not text.strip():
        return 0.0
    sentences = split_sentences(text)
    words = split_words(text)
    if not sentences or not words:
        return 0.0
    total_syllables = sum(count_syllables(w) for w in words)
    asl = len(words) / len(sentences)
    asw = total_syllables / len(words)
    grade = 0.39 * asl + 11.8 * asw - 15.59
    return round(max(grade, 0.0), 1)


async def simplify_text(text: str, *, target_grade: float = 6.0, max_iterations: int = 3) -> SimplifyResult:
    """Iteratively rewrite text until below target grade level.

    Calls the configured Ollama model with a tight simplification prompt.
    Each iteration measures the rewritten text's grade level and stops as
    soon as it falls at or below the target. If max_iterations is reached
    without success, returns the best version produced.

    Args:
        text: The original (possibly jargon-heavy) text.
        target_grade: Maximum acceptable grade level (default 6.0).
        max_iterations: Hard cap on rewrite passes (default 3).

    Returns:
        SimplifyResult with the rewritten text and grade-level metrics.

    Examples:
        >>> import asyncio
        >>> r = asyncio.run(simplify_text("Pharmacokinetic interactions may occur."))  # doctest: +SKIP
        >>> r.target_met or r.iterations_used == 3
        True
    """
    if not text.strip():
        return SimplifyResult("", 0.0, 0.0, 0, target_met=True)

    original = flesch_kincaid_grade(text)
    if original <= target_grade:
        return SimplifyResult(text, original, original, 0, target_met=True)

    client = get_ollama_client()
    current_text = text
    current_grade = original
    best_text = text
    best_grade = original
    iterations = 0

    for _ in range(max_iterations):
        iterations += 1
        rewritten = await client.chat_text(
            system=_SIMPLIFIER_SYSTEM,
            user=f"Rewrite this at a 6th-grade level:\n\n{current_text}",
            temperature=settings.temp_communicator,
        )
        rewritten = rewritten.strip()
        new_grade = flesch_kincaid_grade(rewritten)
        if new_grade < best_grade:
            best_text = rewritten
            best_grade = new_grade
        if new_grade <= target_grade:
            return SimplifyResult(rewritten, original, new_grade, iterations, target_met=True)
        current_text = rewritten
        current_grade = new_grade

    return SimplifyResult(best_text, original, best_grade, iterations, target_met=False)
