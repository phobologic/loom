"""Context assembly for AI prompts.

Builds structured context blocks from game state (world document, act/scene
guiding questions, characters present, recent beat history, lines and veils)
for inclusion in AI system and user prompts.
"""

from __future__ import annotations

from loom.models import BeatStatus, Game, Scene


def format_safety_tools_context(tools: list) -> str:
    """Format lines and veils as a context block for AI prompts.

    Args:
        tools: List of GameSafetyTool instances with .kind.value and .description.

    Returns:
        A formatted string for inclusion in an AI prompt, or "" if no tools exist.
    """
    lines = [t for t in tools if t.kind.value == "line"]
    veils = [t for t in tools if t.kind.value == "veil"]

    if not lines and not veils:
        return ""

    parts = ["SAFETY TOOLS — content boundaries established by the players:"]
    if lines:
        parts.append("Lines (must NOT appear in any content or suggestions):")
        for t in lines:
            parts.append(f"  - {t.description}")
    if veils:
        parts.append("Veils (may be referenced but not depicted in detail — fade to black):")
        for t in veils:
            parts.append(f"  - {t.description}")

    return "\n".join(parts)


def assemble_scene_context(
    game: Game,
    scene: Scene,
    *,
    beat_history_window: int = 10,
) -> str:
    """Build a context block describing the current game/scene state.

    Includes world document, act and scene guiding questions, characters
    present, recent canon beats, and lines/veils. Relationships that were not
    eagerly loaded (None or empty) are skipped gracefully.

    Args:
        game: Game instance (world_document and safety_tools should be loaded).
        scene: Scene instance (act, beats with events, and characters_present
               should be loaded).
        beat_history_window: How many recent canon beats to include.

    Returns:
        A formatted multi-section context string.
    """
    act = scene.act
    parts: list[str] = []

    if game.world_document and game.world_document.content:
        parts.append(f"WORLD DOCUMENT:\n{game.world_document.content}")

    parts.append(f"CURRENT ACT GUIDING QUESTION: {act.guiding_question}")

    scene_header = f"CURRENT SCENE GUIDING QUESTION: {scene.guiding_question}"
    if scene.location:
        scene_header += f"\nLocation: {scene.location}"
    parts.append(scene_header)

    if scene.characters_present:
        char_lines = []
        for char in scene.characters_present:
            entry = char.name
            if char.description:
                entry += f": {char.description}"
            char_lines.append(f"  - {entry}")
        parts.append("CHARACTERS IN SCENE:\n" + "\n".join(char_lines))

    # Recent canon beats, sorted by order
    canon_beats = sorted(
        [b for b in scene.beats if b.status == BeatStatus.canon],
        key=lambda b: b.order,
    )
    recent = canon_beats[-beat_history_window:]
    if recent:
        snippets = []
        for beat in recent:
            for event in beat.events:
                if event.content:
                    snippets.append(f"  - {event.content}")
        if snippets:
            parts.append("RECENT STORY BEATS:\n" + "\n".join(snippets))

    if game.safety_tools:
        safety_ctx = format_safety_tools_context(game.safety_tools)
        if safety_ctx:
            parts.append(safety_ctx)

    return "\n\n".join(parts)


def format_tension_context(tension: int) -> str:
    """Format scene tension as a tonal guidance block for AI prompts.

    Args:
        tension: Current scene tension value (1-9).

    Returns:
        A formatted string describing the tension level and tonal guidance.
    """
    if tension <= 3:
        descriptor = (
            "low — favour subtle, seed-planting interpretations that introduce "
            "possibilities without forcing escalation"
        )
    elif tension <= 6:
        descriptor = (
            "moderate — balanced interpretations that neither force escalation nor deflate tension"
        )
    else:
        descriptor = (
            "high — favour dramatic, escalating interpretations that heighten "
            "stakes and push the story forward"
        )
    return f"CURRENT TENSION: {tension}/9 ({descriptor})"


def scene_context_components(game: Game, scene: Scene) -> list[str]:
    """Return the names of context components that assemble_scene_context would include.

    Inspects the loaded relationships without re-assembling the full context
    string. Used for AI usage logging.

    Args:
        game: Game instance (same state as passed to assemble_scene_context).
        scene: Scene instance (same state as passed to assemble_scene_context).

    Returns:
        A list of component name strings (e.g. ["world_document", "beat_history"]).
    """
    components: list[str] = ["act_guiding_question", "scene_guiding_question", "tension"]
    if game.world_document and game.world_document.content:
        components.insert(0, "world_document")
    if scene.characters_present:
        components.append("characters_present")
    canon_beats = [b for b in scene.beats if b.status == BeatStatus.canon]
    if canon_beats:
        components.append("beat_history")
    if game.safety_tools:
        components.append("safety_tools")
    return components
