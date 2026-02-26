"""High-level async AI functions for Loom features.

Each function maps to a specific AI feature and uses the model configured for
that feature's category (classification vs. creative) in Settings. All
responses are validated Pydantic models via instructor — format constraints
live in loom/ai/schemas.py, not in prompt text.

Every function accepts optional ``db`` and ``game_id`` parameters. When
provided, an AIUsageLog row is written after each successful call so all AI
activity is queryable for analysis.
"""

from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from loom.ai.context import (
    assemble_scene_context,
    format_tension_context,
    scene_context_components,
)
from loom.ai.provider import UsageInfo, get_provider
from loom.ai.schemas import (
    BeatClassification,
    OracleResponse,
    SynthesisResponse,
    TensionAdjustmentResponse,
    WorldDocumentResponse,
)
from loom.config import settings
from loom.models import AIUsageLog, Game, Scene


async def _log_usage(
    db: AsyncSession,
    *,
    feature: str,
    model: str,
    usage: UsageInfo,
    context_components: list[str] | None = None,
    game_id: int | None = None,
) -> None:
    """Insert an AIUsageLog row. Committed as part of the caller's session."""
    log = AIUsageLog(
        feature=feature,
        model=model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        context_components=json.dumps(context_components)
        if context_components is not None
        else None,
        game_id=game_id,
    )
    db.add(log)
    await db.flush()


async def oracle_interpretations(
    question: str,
    word_pair: tuple[str, str],
    *,
    game: Game | None = None,
    scene: Scene | None = None,
    db: AsyncSession | None = None,
    game_id: int | None = None,
) -> list[str]:
    """Generate 3 oracle interpretations for a question and word pair.

    Args:
        question: The oracle question posed by the player.
        word_pair: (action_word, descriptor_word) drawn from the word seed table.
        game: Game instance for world/safety context (world_document and
              safety_tools should be loaded).
        scene: Current scene for narrative context (act, beats, characters_present
               should be loaded).
        db: AsyncSession for writing an AIUsageLog entry (optional).
        game_id: ID of the game, used in the usage log (optional).

    Returns:
        A list of exactly 3 interpretation strings.
    """
    action, descriptor = word_pair

    system = (
        "You are an oracular voice for a collaborative tabletop roleplaying game. "
        "Your interpretations should be evocative, narratively rich, and fit the "
        "established world tone. Respect all lines and veils listed in the context."
    )

    prompt_parts: list[str] = []
    context_comps: list[str] | None = None
    if game is not None and scene is not None:
        context_block = assemble_scene_context(
            game, scene, beat_history_window=settings.ai_context_beat_history_window
        )
        if context_block:
            prompt_parts.append(context_block)
        context_comps = scene_context_components(game, scene)

    if scene is not None:
        prompt_parts.append(format_tension_context(scene.tension))

    prompt_parts.append(
        f"ORACLE QUESTION: {question}\nWORD SEEDS: action={action!r}, descriptor={descriptor!r}"
    )

    model = settings.ai_model_creative
    response, usage = await get_provider().generate_structured(
        system=system,
        prompt="\n\n".join(prompt_parts),
        model=model,
        max_tokens=512,
        response_model=OracleResponse,
    )

    if db is not None:
        await _log_usage(
            db,
            feature="oracle_interpretations",
            model=model,
            usage=usage,
            context_components=context_comps,
            game_id=game_id,
        )

    return response.interpretations


async def session0_synthesis(
    question: str,
    inputs: list[str],
    *,
    game_name: str = "",
    pitch: str = "",
    db: AsyncSession | None = None,
    game_id: int | None = None,
) -> str:
    """Synthesize player responses to a Session 0 prompt into a coherent paragraph.

    Args:
        question: The Session 0 prompt question being synthesized.
        inputs: Player responses to synthesize.
        game_name: Name of the game (for context).
        pitch: Game pitch (for context).
        db: AsyncSession for writing an AIUsageLog entry (optional).
        game_id: ID of the game, used in the usage log (optional).

    Returns:
        A synthesis paragraph capturing the group's shared vision.
    """
    system = (
        "You are assisting a game organizer running a collaborative tabletop RPG "
        "Session 0. Synthesize the players' responses into a single cohesive paragraph "
        "that captures the group's shared vision for this prompt. Be evocative and "
        "faithful to what the players wrote. Write in present-tense world-building prose."
    )

    lines: list[str] = []
    context_comps: list[str] = []
    if game_name:
        lines.append(f"Game: {game_name}")
        context_comps.append("game_name")
    if pitch:
        lines.append(f"Pitch: {pitch}")
        context_comps.append("pitch")
    lines.append(f"Prompt: {question}")
    lines.append("\nPlayer responses:")
    for i, inp in enumerate(inputs, 1):
        lines.append(f"  {i}. {inp}")
    context_comps.append("player_responses")

    model = settings.ai_model_creative
    response, usage = await get_provider().generate_structured(
        system=system,
        prompt="\n".join(lines),
        model=model,
        max_tokens=512,
        response_model=SynthesisResponse,
    )

    if db is not None:
        await _log_usage(
            db,
            feature="session0_synthesis",
            model=model,
            usage=usage,
            context_components=context_comps,
            game_id=game_id,
        )

    return response.text


async def generate_world_document(
    session0_data: dict,
    *,
    db: AsyncSession | None = None,
    game_id: int | None = None,
) -> str:
    """Generate a world document from Session 0 synthesis data.

    Args:
        session0_data: Dict with keys:
            game_name (str), pitch (str | None),
            prompts (list of {question, synthesis, responses}).
        db: AsyncSession for writing an AIUsageLog entry (optional).
        game_id: ID of the game, used in the usage log (optional).

    Returns:
        A structured Markdown world document.
    """
    system = (
        "You are a world-builder for a collaborative tabletop RPG. "
        "Using the Session 0 synthesis data provided, write a concise but evocative "
        "world document. Be concrete and usable at the table."
    )

    prompt_parts = [f"# {session0_data.get('game_name', 'Unnamed Game')}"]
    if session0_data.get("pitch"):
        prompt_parts.append(f"**Pitch:** {session0_data['pitch']}")

    prompt_parts.append("\n## Session 0 Syntheses")
    for p in session0_data.get("prompts", []):
        q = p.get("question", "")
        synth = p.get("synthesis", "")
        if q and synth:
            prompt_parts.append(f"\n**{q}**\n{synth}")

    model = settings.ai_model_creative
    response, usage = await get_provider().generate_structured(
        system=system,
        prompt="\n".join(prompt_parts),
        model=model,
        max_tokens=2048,
        response_model=WorldDocumentResponse,
    )

    if db is not None:
        await _log_usage(
            db,
            feature="generate_world_document",
            model=model,
            usage=usage,
            context_components=["session0_syntheses"],
            game_id=game_id,
        )

    return response.markdown


async def classify_beat_significance(
    beat_text: str,
    *,
    db: AsyncSession | None = None,
    game_id: int | None = None,
) -> str:
    """Classify a beat as 'minor' or 'major' based on its narrative weight.

    Args:
        beat_text: The full text of the beat to classify.
        db: AsyncSession for writing an AIUsageLog entry (optional).
        game_id: ID of the game, used in the usage log (optional).

    Returns:
        Either "minor" or "major".
    """
    system = (
        "You are a narrative classifier for a collaborative tabletop RPG. "
        "Classify the provided beat based on its narrative weight."
    )

    model = settings.ai_model_classification
    response, usage = await get_provider().generate_structured(
        system=system,
        prompt=f"Beat text:\n{beat_text}",
        model=model,
        max_tokens=64,
        response_model=BeatClassification,
    )

    if db is not None:
        await _log_usage(
            db,
            feature="classify_beat_significance",
            model=model,
            usage=usage,
            game_id=game_id,
        )

    return response.significance


async def evaluate_tension_adjustment(
    game: Game,
    scene: Scene,
    recent_scene_history: list[tuple[int, str | None]],
    *,
    db: AsyncSession | None = None,
    game_id: int | None = None,
) -> tuple[int, str]:
    """Evaluate a completed scene and propose a tension adjustment.

    Args:
        game: Fully loaded game (world_document, safety_tools, members loaded).
        scene: Just-completed scene (beats with events loaded).
        recent_scene_history: List of (tension, ai_rationale) for the last few
            completed scenes in the act (oldest first), for arc-level context.
        db: AsyncSession for writing an AIUsageLog entry (optional).
        game_id: ID of the game, used in the usage log (optional).

    Returns:
        (delta, rationale) — delta is -1, 0, or +1; rationale is player-facing text
        that names which factors drove the recommendation.
    """
    system = (
        "You are a narrative pacing evaluator for a collaborative tabletop RPG. "
        "Analyze the completed scene and recommend a tension adjustment (+1, -1, or 0). "
        "Be fully transparent in your rationale about which factors drove the choice."
    )

    prompt_parts: list[str] = []
    context_comps: list[str] | None = None

    context_block = assemble_scene_context(
        game, scene, beat_history_window=settings.ai_context_beat_history_window
    )
    if context_block:
        prompt_parts.append(context_block)
    context_comps = scene_context_components(game, scene)

    if recent_scene_history:
        history_lines = ["## Recent scene history (oldest first)"]
        for i, (t, rationale) in enumerate(recent_scene_history, 1):
            line = f"Scene -{len(recent_scene_history) - i + 1}: tension={t}"
            if rationale:
                line += f" — {rationale}"
            history_lines.append(line)
        prompt_parts.append("\n".join(history_lines))
        context_comps = (context_comps or []) + ["recent_scene_history"]

    current_tension = scene.tension
    prompt_parts.append(
        f"## Tension evaluation task\n"
        f"Current tension: {current_tension}/9. The scene above has just completed.\n\n"
        f"Evaluate the tension adjustment using these factors in order:\n\n"
        f"1. SCENE OUTCOME: Did stakes rise (plans failed, new threats, unresolved surprises → +1) "
        f"or fall (goals achieved, conflict resolved, characters in control → -1)? "
        f"Mixed or ambiguous → 0.\n\n"
        f"2. NARRATIVE ARC: Based on the recent scene history above — "
        f"if tension has been low (≤3) for multiple scenes, lean toward +1 even on neutral scenes. "
        f"If tension has been high (≥7) for multiple scenes, lean toward -1 for a breather.\n\n"
        f"3. FEEDBACK LOOP: Low tension makes fortune rolls more favorable, which tends to keep "
        f"tension low. If tension is already low and the scene outcome is ambiguous, consider "
        f"recommending +1 to prevent narrative stagnation.\n\n"
        f"4. EXTREME CORRECTION: If current tension ≥ 8, prefer -1 unless the scene was clearly "
        f"escalating. If current tension ≤ 3, prefer +1 unless the scene was clearly resolving.\n\n"
        f"In your rationale, explicitly name which factor(s) drove your recommendation. "
        f"Write 2-4 sentences addressed directly to the players. They will read this before voting."
    )

    model = settings.ai_model_classification
    response, usage = await get_provider().generate_structured(
        system=system,
        prompt="\n\n".join(prompt_parts),
        model=model,
        max_tokens=400,
        response_model=TensionAdjustmentResponse,
    )

    if db is not None:
        await _log_usage(
            db,
            feature="evaluate_tension_adjustment",
            model=model,
            usage=usage,
            context_components=context_comps,
            game_id=game_id,
        )

    return response.delta, response.rationale
