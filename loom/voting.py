"""Voting threshold helpers shared across routers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from loom.models import Act, Scene


def approval_threshold(total_players: int) -> float:
    """Return the yes-vote count required for approval (strictly more than half)."""
    return total_players / 2


def is_approved(yes_count: int, total_players: int) -> bool:
    """Return True when yes_count strictly exceeds half of total_players."""
    return yes_count > approval_threshold(total_players)


def resolve_tension_vote(
    yes_count: int,
    suggest_count: int,
    no_count: int,
    ai_delta: int,
) -> int:
    """Resolve a tension adjustment vote by plurality.

    VoteChoice mapping: yes → +1, suggest_modification → 0, no → -1.
    Returns the winning delta. AI delta breaks ties and applies if no votes cast.

    Args:
        yes_count: Number of votes for +1 (escalate).
        suggest_count: Number of votes for 0 (hold steady).
        no_count: Number of votes for -1 (ease tension).
        ai_delta: The AI's recommended delta, used as tiebreaker and default.

    Returns:
        The resolved tension delta (-1, 0, or +1).
    """
    counts = {1: yes_count, 0: suggest_count, -1: no_count}
    if all(v == 0 for v in counts.values()):
        return ai_delta  # no votes cast → AI suggestion wins
    max_count = max(counts.values())
    winners = [delta for delta, count in counts.items() if count == max_count]
    if len(winners) == 1:
        return winners[0]
    return ai_delta  # tie → AI suggestion wins


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


def activate_scene(scenes: list[Scene], new_scene: Scene) -> None:
    """Complete any currently active scene and set new_scene to active.

    Args:
        scenes: All scenes for the act (used to find and complete the current active scene).
        new_scene: The scene being activated.
    """
    from loom.models import SceneStatus

    for scene in scenes:
        if scene.status == SceneStatus.active:
            scene.status = SceneStatus.complete
    new_scene.status = SceneStatus.active
