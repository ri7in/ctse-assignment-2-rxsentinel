"""Dose normalizer — owned by Thusala (Med Parser support).

Converts free-text dose strings ("500mg", "0.5 g", "two tablets") into a
canonical (value, unit) pair so downstream agents can reason about doses
across different patient inputs.

Pure Python, no I/O. Fast enough to call once per parsed medication.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


_DOSE_PATTERN = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>mcg|mg|g|kg|ml|l|iu|units?|tabs?|tablets?|caps?|capsules?)",
    re.I,
)

# Normalize unit aliases to a canonical short form.
_UNIT_CANON = {
    "mcg": "mcg", "mg": "mg", "g": "g", "kg": "kg",
    "ml": "ml", "l": "ml",
    "iu": "iu", "unit": "iu", "units": "iu",
    "tab": "tablet", "tabs": "tablet", "tablet": "tablet", "tablets": "tablet",
    "cap": "capsule", "caps": "capsule", "capsule": "capsule", "capsules": "capsule",
}

# Convert all weight-units down to mg for cross-comparison.
_TO_MG = {"mcg": 0.001, "mg": 1.0, "g": 1000.0, "kg": 1_000_000.0}


@dataclass(frozen=True)
class NormalizedDose:
    """A dose parsed into structured form."""

    value: float
    unit: str
    mg_equivalent: float | None  # populated for mass units, None otherwise
    raw: str


def normalize_dose(text: str) -> NormalizedDose | None:
    """Parse a free-text dose into a structured record.

    Args:
        text: Any free-form string that might describe a dose
            (e.g., "500mg", "0.5 g", "10 ml").

    Returns:
        A NormalizedDose if a dose pattern was recognized, else None.

    Examples:
        >>> normalize_dose("500mg").mg_equivalent
        500.0
        >>> normalize_dose("0.5 g").mg_equivalent
        500.0
        >>> normalize_dose("10 ml").unit
        'ml'
        >>> normalize_dose("two tablets") is None
        True
    """
    if not text or not text.strip():
        return None
    m = _DOSE_PATTERN.search(text)
    if not m:
        return None
    value = float(m.group("value"))
    unit = _UNIT_CANON.get(m.group("unit").lower(), m.group("unit").lower())
    mg = _TO_MG.get(unit)
    return NormalizedDose(
        value=value,
        unit=unit,
        mg_equivalent=value * mg if mg is not None else None,
        raw=text.strip(),
    )
