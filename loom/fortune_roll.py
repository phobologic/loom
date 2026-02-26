"""Fortune Roll probability engine for the yes/no oracle.

A Fortune Roll asks a binary question, modified by the current Tension.
The result is one of: exceptional_yes, yes, no, exceptional_no.

Probability table design
------------------------
At Tension 5 (baseline), the table reflects stated odds intuitively.
Each tension point above 5 shifts ~5% probability toward "yes" and toward
exceptional results; below 5, shifts toward "no" and toward exceptional.

The table stores 3 thresholds (A, B, C) for a d100 roll (0–99):
  roll < A          → exceptional_yes
  A <= roll < B     → yes
  B <= roll < C     → no
  C <= roll         → exceptional_no

Human-readable labels for display are in ODDS_LABELS.
"""

from __future__ import annotations

import random

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FORTUNE_ROLL_ODDS: list[str] = [
    "impossible",
    "very_unlikely",
    "unlikely",
    "fifty_fifty",
    "likely",
    "very_likely",
    "near_certain",
]

FORTUNE_ROLL_RESULTS: list[str] = [
    "exceptional_yes",
    "yes",
    "no",
    "exceptional_no",
]

ODDS_LABELS: dict[str, str] = {
    "impossible": "Impossible",
    "very_unlikely": "Very Unlikely",
    "unlikely": "Unlikely",
    "fifty_fifty": "50/50",
    "likely": "Likely",
    "very_likely": "Very Likely",
    "near_certain": "Near Certain",
}

RESULT_LABELS: dict[str, str] = {
    "exceptional_yes": "Exceptional Yes",
    "yes": "Yes",
    "no": "No",
    "exceptional_no": "Exceptional No",
}

# ---------------------------------------------------------------------------
# Probability table
# ---------------------------------------------------------------------------
# Format: {odds: {tension: (A, B, C)}}
# At tension 5, baseline probabilities:
#   impossible:    1  ex.yes,  4  yes,  60  no, 35  ex.no
#   very_unlikely: 3  ex.yes, 12  yes,  65  no, 20  ex.no
#   unlikely:      5  ex.yes, 25  yes,  55  no, 15  ex.no
#   fifty_fifty:  10  ex.yes, 40  yes,  40  no, 10  ex.no
#   likely:       15  ex.yes, 55  yes,  25  no,  5  ex.no
#   very_likely:  20  ex.yes, 65  yes,  12  no,  3  ex.no
#   near_certain: 30  ex.yes, 65  yes,   4  no,  1  ex.no
#
# Each tension step above 5 shifts ~5% toward yes/exceptional.
# Each tension step below 5 shifts ~5% toward no/exceptional.
# All values are clamped to [0, 100].

_BASELINE: dict[str, tuple[int, int, int]] = {
    #                    A    B    C
    "impossible": (1, 5, 65),
    "very_unlikely": (3, 15, 80),
    "unlikely": (5, 30, 85),
    "fifty_fifty": (10, 50, 90),
    "likely": (15, 70, 95),
    "very_likely": (20, 85, 97),
    "near_certain": (30, 95, 99),
}

# Shift applied per tension step from 5 (positive = toward yes, negative = toward no).
# A and B shift positively (more yes) when tension > 5.
# C shifts negatively (fewer exceptional no) when tension > 5.
_SHIFTS: dict[str, tuple[int, int, int]] = {
    #                   dA   dB   dC
    "impossible": (1, 3, -4),
    "very_unlikely": (1, 4, -4),
    "unlikely": (1, 5, -4),
    "fifty_fifty": (2, 5, -3),
    "likely": (2, 5, -2),
    "very_likely": (2, 4, -1),
    "near_certain": (2, 3, -1),
}


def _thresholds(odds: str, tension: int) -> tuple[int, int, int]:
    """Return (A, B, C) thresholds for the given odds and tension."""
    a0, b0, c0 = _BASELINE[odds]
    da, db, dc = _SHIFTS[odds]
    steps = tension - 5
    a = max(0, min(99, a0 + da * steps))
    b = max(a + 1, min(99, b0 + db * steps))
    c = max(b + 1, min(100, c0 + dc * steps))
    return a, b, c


# Pre-compute the full probability table for all tensions 1–9.
# Exported as PROBABILITY_TABLE for transparent display in templates.
PROBABILITY_TABLE: dict[str, dict[int, dict[str, int]]] = {}
for _odds in FORTUNE_ROLL_ODDS:
    PROBABILITY_TABLE[_odds] = {}
    for _t in range(1, 10):
        _a, _b, _c = _thresholds(_odds, _t)
        PROBABILITY_TABLE[_odds][_t] = {
            "exceptional_yes": _a,
            "yes": _b - _a,
            "no": _c - _b,
            "exceptional_no": 100 - _c,
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_fortune_roll_result(odds: str, tension: int) -> str:
    """Roll the fortune die and return the result string.

    Args:
        odds: One of FORTUNE_ROLL_ODDS.
        tension: Current scene tension (1–9).

    Returns:
        One of FORTUNE_ROLL_RESULTS.

    Raises:
        ValueError: If odds is not a valid value.
    """
    if odds not in FORTUNE_ROLL_ODDS:
        raise ValueError(f"Invalid odds: {odds!r}")
    tension = max(1, min(9, tension))
    a, b, c = _thresholds(odds, tension)
    roll = random.randint(0, 99)
    if roll < a:
        return "exceptional_yes"
    if roll < b:
        return "yes"
    if roll < c:
        return "no"
    return "exceptional_no"


def is_exceptional(result: str) -> bool:
    """Return True if the result is exceptional (yes or no)."""
    return result in ("exceptional_yes", "exceptional_no")


def fortune_roll_contest_window_hours(silence_timer_hours: int, override: int | None) -> int:
    """Compute the contest window duration in hours.

    Args:
        silence_timer_hours: The game's silence timer setting.
        override: If set, use this value directly.

    Returns:
        Number of hours for the contest window.
    """
    if override is not None:
        return override
    return max(1, silence_timer_hours // 2)
