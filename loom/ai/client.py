"""High-level async AI functions for Loom features.

This module replaces loom/ai/stubs.py for all production AI calls. Each
function maps to a specific AI feature and uses the model configured for that
feature's category (classification vs. creative) in Settings.
"""

from __future__ import annotations

import json

from loom.ai.context import assemble_scene_context
from loom.ai.provider import get_provider
from loom.config import settings
from loom.models import Game, Scene


async def oracle_interpretations(
    question: str,
    word_pair: tuple[str, str],
    *,
    game: Game | None = None,
    scene: Scene | None = None,
) -> list[str]:
    """Generate 3 oracle interpretations for a question and word pair.

    Args:
        question: The oracle question posed by the player.
        word_pair: (action_word, descriptor_word) drawn from the word seed table.
        game: Game instance for world/safety context (world_document and
              safety_tools should be loaded).
        scene: Current scene for narrative context (act, beats, characters_present
               should be loaded).

    Returns:
        A list of exactly 3 interpretation strings.
    """
    action, descriptor = word_pair

    system = (
        "You are an oracular voice for a collaborative tabletop roleplaying game. "
        "Your interpretations should be evocative, narratively rich, and fit the "
        "established world tone. Respect all lines and veils listed in the context. "
        "Return a JSON array containing exactly 3 strings — no other text."
    )

    prompt_parts: list[str] = []
    if game is not None and scene is not None:
        context_block = assemble_scene_context(
            game, scene, beat_history_window=settings.ai_context_beat_history_window
        )
        if context_block:
            prompt_parts.append(context_block)

    prompt_parts.append(
        f"ORACLE QUESTION: {question}\n"
        f"WORD SEEDS: action={action!r}, descriptor={descriptor!r}\n\n"
        "Generate 3 distinct, evocative interpretations inspired by the question "
        "and word seeds. Each should suggest a possible truth, consequence, or "
        "revelation that fits the world and advances the story. "
        "Return as a JSON array of exactly 3 strings."
    )

    raw = await get_provider().generate(
        system=system,
        prompt="\n\n".join(prompt_parts),
        model=settings.ai_model_creative,
        max_tokens=512,
    )

    # Parse JSON response
    try:
        result = json.loads(raw)
        if isinstance(result, list) and len(result) >= 3:
            return [str(s) for s in result[:3]]
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: split on newlines if the model returned prose instead of JSON
    candidates = [
        line.strip().lstrip("-•*123456789. ") for line in raw.strip().splitlines() if line.strip()
    ]
    candidates = [c for c in candidates if c]
    while len(candidates) < 3:
        candidates.append("The oracle speaks in riddles — the answer lies within.")
    return candidates[:3]


async def session0_synthesis(
    question: str,
    inputs: list[str],
    *,
    game_name: str = "",
    pitch: str = "",
) -> str:
    """Synthesize player responses to a Session 0 prompt into a coherent paragraph.

    Args:
        question: The Session 0 prompt question being synthesized.
        inputs: Player responses to synthesize.
        game_name: Name of the game (for context).
        pitch: Game pitch (for context).

    Returns:
        A synthesis paragraph capturing the group's shared vision.
    """
    system = (
        "You are assisting a game organizer running a collaborative tabletop RPG "
        "Session 0. Synthesize the players' responses into a single cohesive paragraph "
        "that captures the group's shared vision for this prompt. Be evocative and "
        "faithful to what the players wrote. Write in present-tense world-building prose. "
        "Return only the synthesis paragraph — no heading, no preamble."
    )

    lines: list[str] = []
    if game_name:
        lines.append(f"Game: {game_name}")
    if pitch:
        lines.append(f"Pitch: {pitch}")
    lines.append(f"Prompt: {question}")
    lines.append("\nPlayer responses:")
    for i, inp in enumerate(inputs, 1):
        lines.append(f"  {i}. {inp}")

    return await get_provider().generate(
        system=system,
        prompt="\n".join(lines),
        model=settings.ai_model_creative,
        max_tokens=512,
    )


async def generate_world_document(session0_data: dict) -> str:
    """Generate a world document from Session 0 synthesis data.

    Args:
        session0_data: Dict with keys:
            game_name (str), pitch (str | None),
            prompts (list of {question, synthesis, responses}).

    Returns:
        A structured Markdown world document.
    """
    system = (
        "You are a world-builder for a collaborative tabletop RPG. "
        "Using the Session 0 synthesis data provided, write a concise but evocative "
        "world document in Markdown. Include sections for: World Overview, Tone & "
        "Aesthetic, Setting, Central Tensions, and Key Themes. "
        "Be concrete and usable at the table. Return only the Markdown document."
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

    return await get_provider().generate(
        system=system,
        prompt="\n".join(prompt_parts),
        model=settings.ai_model_creative,
        max_tokens=2048,
    )


async def classify_beat_significance(beat_text: str) -> str:
    """Classify a beat as 'minor' or 'major' based on its narrative weight.

    Args:
        beat_text: The full text of the beat to classify.

    Returns:
        Either "minor" or "major".
    """
    system = (
        "You are a narrative classifier for a collaborative tabletop RPG. "
        "Classify the provided beat as either 'minor' (routine action, small moment) "
        "or 'major' (significant plot point, character revelation, world-changing event). "
        "Reply with only the single word: minor or major."
    )

    raw = await get_provider().generate(
        system=system,
        prompt=f"Beat text:\n{beat_text}",
        model=settings.ai_model_classification,
        max_tokens=16,
    )
    result = raw.strip().lower()
    if result in ("minor", "major"):
        return result
    return "minor"
