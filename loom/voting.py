"""Voting threshold helpers shared across routers."""

from __future__ import annotations


def approval_threshold(total_players: int) -> float:
    """Return the yes-vote count required for approval (strictly more than half)."""
    return total_players / 2


def is_approved(yes_count: int, total_players: int) -> bool:
    """Return True when yes_count strictly exceeds half of total_players."""
    return yes_count > approval_threshold(total_players)
