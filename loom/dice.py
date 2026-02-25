"""Server-side dice rolling engine.

Supports standard notation: XdY, XdY+Z, XdY-Z.
Examples: 2d6, 1d20, 3d10+2, 2d6-1.
"""

from __future__ import annotations

import random
import re

_NOTATION_RE = re.compile(
    r"^(?P<count>[1-9]\d*)?d(?P<sides>[1-9]\d*)(?P<mod>[+-]\d+)?$",
    re.IGNORECASE,
)

_MAX_DICE = 100
_MAX_SIDES = 1000


class DiceError(ValueError):
    """Raised when a dice notation is invalid."""


def parse(notation: str) -> tuple[int, int, int]:
    """Parse dice notation into (count, sides, modifier).

    Args:
        notation: Dice notation string, e.g. "2d6+3".

    Returns:
        Tuple of (number of dice, sides per die, flat modifier).

    Raises:
        DiceError: If the notation is invalid or out of range.
    """
    m = _NOTATION_RE.match(notation.strip())
    if not m:
        raise DiceError(f"Invalid dice notation: {notation!r}")

    count = int(m.group("count") or 1)
    sides = int(m.group("sides"))
    modifier = int(m.group("mod") or 0)

    if count > _MAX_DICE:
        raise DiceError(f"Too many dice: {count} (max {_MAX_DICE})")
    if sides > _MAX_SIDES:
        raise DiceError(f"Too many sides: {sides} (max {_MAX_SIDES})")

    return count, sides, modifier


def roll(notation: str) -> int:
    """Roll dice described by notation and return the total.

    Args:
        notation: Dice notation string, e.g. "2d6+3".

    Returns:
        Integer total of all dice plus any modifier.

    Raises:
        DiceError: If the notation is invalid.
    """
    count, sides, modifier = parse(notation)
    total = sum(random.randint(1, sides) for _ in range(count))
    return total + modifier
