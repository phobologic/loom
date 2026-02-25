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
