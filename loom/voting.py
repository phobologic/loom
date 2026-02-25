"""Voting threshold helpers shared across routers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from loom.models import Act


def approval_threshold(total_players: int) -> float:
    """Return the yes-vote count required for approval (strictly more than half)."""
    return total_players / 2


def is_approved(yes_count: int, total_players: int) -> bool:
    """Return True when yes_count strictly exceeds half of total_players."""
    return yes_count > approval_threshold(total_players)


def activate_act(acts: list[Act], new_act: Act) -> None:
    """Complete any currently active act and set new_act to active.

    Args:
        acts: All acts for the game (used to find and complete the current active act).
        new_act: The act being activated.
    """
    from loom.models import ActStatus

    for act in acts:
        if act.status == ActStatus.active:
            act.status = ActStatus.complete
    new_act.status = ActStatus.active
