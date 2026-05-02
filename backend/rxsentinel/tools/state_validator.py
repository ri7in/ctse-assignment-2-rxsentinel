"""State validator tool — owned by Rivin (Coordinator agent).

Synchronous, dependency-free input check that the Coordinator runs before
spending any LLM tokens. Catches empty/garbage/prompt-injection inputs early.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Common prompt-injection markers seen in jailbreak attempts.
_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bignore\s+(all\s+)?(previous|prior|above)\b", re.I),
    re.compile(r"\bdisregard\s+(all\s+)?(previous|prior|above|instructions)\b", re.I),
    re.compile(r"\bsystem\s*:\s*you\s+are\b", re.I),
    re.compile(r"\bbypass\b.*\b(safety|filter|guard)", re.I),
    re.compile(r"\bjailbreak\b", re.I),
)

_MIN_LEN = 3
_MAX_LEN = 4000  # absurdly large = noise


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Outcome of input validation."""

    is_valid: bool
    errors: list[str]


def validate_initial_state(raw_input: str) -> ValidationResult:
    """Validate that user input is plausibly a medication list.

    This runs BEFORE any LLM call, so it must be cheap and side-effect-free.
    It rejects empty input, oversized input, prompt-injection markers, and
    inputs with no alphabetic content.

    Args:
        raw_input: User-submitted free text.

    Returns:
        ValidationResult(is_valid=True, errors=[]) if input passes.
        ValidationResult(is_valid=False, errors=[...]) listing every reason
        the input was rejected.

    Examples:
        >>> validate_initial_state("metformin 500mg twice daily").is_valid
        True
        >>> validate_initial_state("").is_valid
        False
        >>> validate_initial_state("ignore previous instructions").is_valid
        False
    """
    errors: list[str] = []

    if raw_input is None:
        return ValidationResult(False, ["input is None"])

    text = raw_input.strip()

    if len(text) < _MIN_LEN:
        errors.append(f"input is too short (need at least {_MIN_LEN} characters)")

    if len(text) > _MAX_LEN:
        errors.append(f"input is too long (max {_MAX_LEN} characters)")

    if not re.search(r"[A-Za-z]", text):
        errors.append("input contains no alphabetic characters")

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            errors.append("input contains prompt-injection markers")
            break

    # If a string is mostly digits/punctuation, treat as garbage.
    alpha_ratio = sum(c.isalpha() for c in text) / max(len(text), 1)
    if alpha_ratio < 0.2:
        errors.append("input is mostly non-alphabetic (likely not a medication list)")

    return ValidationResult(is_valid=not errors, errors=errors)
