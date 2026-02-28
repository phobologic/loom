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
    assemble_act_narrative_context,
    assemble_scene_context,
    assemble_scene_narrative_context,
    format_tension_context,
    scene_context_components,
)
from loom.ai.provider import UsageInfo, get_provider
from loom.ai.schemas import (
    ActNarrativeResponse,
    BeatClassification,
    CharacterUpdateResponse,
    ConsistencyCheckResponse,
    NarrativeVoiceSuggestions,
    NPCDetailSuggestions,
    OracleResponse,
    ProseExpansion,
    RelationshipSuggestionsResponse,
    SceneNarrativeResponse,
    SynthesisResponse,
    TensionAdjustmentResponse,
    WorldDocumentResponse,
    WorldEntrySuggestionsResponse,
)
from loom.config import settings
from loom.models import NPC, Act, AIUsageLog, Character, Game, Scene, WorldEntry


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


async def suggest_narrative_voices(
    game_name: str,
    pitch: str,
    genre_tone_context: str,
    *,
    db: AsyncSession | None = None,
    game_id: int | None = None,
) -> list[str]:
    """Generate narrative voice options suited to the game's genre and tone.

    Args:
        game_name: Name of the game.
        pitch: Game pitch (may be empty).
        genre_tone_context: Synthesized genre/tone text from completed Session 0 prompts.
        db: AsyncSession for writing an AIUsageLog entry (optional).
        game_id: ID of the game, used in the usage log (optional).

    Returns:
        A list of 3-4 voice option strings for the group to choose from.
    """
    system = (
        "You are a creative writing consultant helping a tabletop RPG group choose a narrative "
        "prose style for their collaborative game. Based on the game's genre and tone, suggest "
        "3-4 distinct narrative voice options the group can choose from. Each option should be "
        "a short, vivid description of a prose style — concrete enough that the AI can apply it "
        "consistently. Make the options genuinely different from each other."
    )

    lines: list[str] = [f"Game: {game_name}"]
    context_comps: list[str] = ["game_name"]
    if pitch:
        lines.append(f"Pitch: {pitch}")
        context_comps.append("pitch")
    if genre_tone_context:
        lines.append(f"\nGame genre and tone established in Session 0:\n{genre_tone_context}")
        context_comps.append("genre_tone_context")
    lines.append(
        "\nSuggest 3-4 narrative voice options for this game's AI-generated prose. "
        "Each should be a 1-2 sentence style description a writer could follow consistently."
    )

    model = settings.ai_model_creative
    response, usage = await get_provider().generate_structured(
        system=system,
        prompt="\n".join(lines),
        model=model,
        max_tokens=512,
        response_model=NarrativeVoiceSuggestions,
    )

    if db is not None:
        await _log_usage(
            db,
            feature="suggest_narrative_voices",
            model=model,
            usage=usage,
            context_components=context_comps,
            game_id=game_id,
        )

    return response.voices


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


async def expand_beat_prose(
    game: Game,
    scene: Scene,
    beat_text: str,
    *,
    db: AsyncSession | None = None,
    game_id: int | None = None,
) -> str:
    """Generate a polished prose expansion of a submitted beat's narrative text.

    Args:
        game: Fully loaded game (world_document, safety_tools, members loaded).
        scene: Current scene (act, characters_present, beats with events loaded).
        beat_text: The raw narrative text submitted by the player.
        db: AsyncSession for writing an AIUsageLog entry (optional).
        game_id: ID of the game, used in the usage log (optional).

    Returns:
        A polished prose string matching the game's narrative voice.
    """
    scene_ctx = assemble_scene_context(game, scene)
    tension_ctx = format_tension_context(scene.tension)
    context_comps = scene_context_components(game, scene)

    system = (
        "You are a prose editor for a collaborative tabletop RPG. "
        "Your role is to take a player's raw beat submission and rewrite it as polished, "
        "literary collaborative-fiction prose — third person, present tense, matching the "
        "game's established narrative voice and the character's voice notes if provided. "
        "Preserve every fact, action, and event from the original. "
        "Do not introduce new events, characters, or information not present in the original. "
        "Do not contradict the story context. Respect all safety tool boundaries."
    )

    voice_instruction = (
        f"Apply this narrative voice: {game.narrative_voice}"
        if game.narrative_voice
        else "Match the narrative voice implied by the world document above."
    )
    prompt = (
        f"{scene_ctx}\n\n"
        f"{tension_ctx}\n\n"
        f"PLAYER'S SUBMITTED BEAT:\n{beat_text}\n\n"
        f"Rewrite the beat as polished prose. {voice_instruction}"
    )

    model = settings.ai_model_creative
    response, usage = await get_provider().generate_structured(
        system=system,
        prompt=prompt,
        model=model,
        max_tokens=512,
        response_model=ProseExpansion,
    )

    if db is not None:
        await _log_usage(
            db,
            feature="expand_beat_prose",
            model=model,
            usage=usage,
            context_components=context_comps,
            game_id=game_id,
        )

    return response.prose


async def check_beat_consistency(
    game: Game,
    scene: Scene,
    beat_text: str,
    roll_results: list[tuple[str, int]] | None = None,
    *,
    db: AsyncSession | None = None,
    game_id: int | None = None,
) -> list[str]:
    """Check a beat draft for consistency with established fiction before submission.

    Args:
        game: Fully loaded game (world_document, safety_tools loaded).
        scene: Current scene (act, characters_present, beats with events loaded).
        beat_text: The narrative text the player is about to submit.
        roll_results: Optional list of (notation, total) for rolls included in the
            same beat — used to check whether the narrative matches roll outcomes.
        db: AsyncSession for writing an AIUsageLog entry (optional).
        game_id: ID of the game, used in the usage log (optional).

    Returns:
        A list of player-facing flag strings describing inconsistencies, or an
        empty list if the beat is consistent with the established fiction.
    """
    scene_ctx = assemble_scene_context(
        game, scene, beat_history_window=settings.ai_context_beat_history_window
    )
    tension_ctx = format_tension_context(scene.tension)
    context_comps = scene_context_components(game, scene)

    system = (
        "You are a continuity editor for a collaborative tabletop RPG. "
        "Your role is to catch factual inconsistencies between a beat draft and the "
        "established fiction — not to judge creative choices, style, or tone. "
        "Flag only clear contradictions: facts established in prior beats, "
        "safety-tool violations (lines and veils), and roll-result mismatches. "
        "If the beat is consistent, return an empty flags list."
    )

    prompt_parts = [scene_ctx, tension_ctx]

    if roll_results:
        roll_lines = ["ROLLS IN THIS BEAT:"]
        for notation, total in roll_results:
            roll_lines.append(f"  {notation} → {total}")
        prompt_parts.append("\n".join(roll_lines))

    prompt_parts.append(
        f"BEAT DRAFT (not yet submitted):\n{beat_text}\n\n"
        "Check the beat draft against the established fiction above. "
        "Report only factual inconsistencies, safety-tool violations, or roll-result mismatches. "
        "Do not flag style choices, narrative gaps, or anything not clearly contradicted by the context."
    )

    model = settings.ai_model_classification
    response, usage = await get_provider().generate_structured(
        system=system,
        prompt="\n\n".join(prompt_parts),
        model=model,
        max_tokens=512,
        response_model=ConsistencyCheckResponse,
    )

    if db is not None:
        await _log_usage(
            db,
            feature="check_beat_consistency",
            model=model,
            usage=usage,
            context_components=context_comps,
            game_id=game_id,
        )

    return response.flags


async def suggest_npc_details(
    beat_text: str,
    role: str,
    *,
    name: str | None = None,
    want: str | None = None,
    existing_pc_names: list[str] | None = None,
    existing_npc_names: list[str] | None = None,
    game: Game | None = None,
    db: AsyncSession | None = None,
    game_id: int | None = None,
) -> tuple[list[str], list[str]]:
    """Suggest name and/or want options for a new NPC based on a beat and player input.

    Only suggests characters with complex motivations — a want or need they are
    actively pursuing that could affect play. Simple threats are not good NPC candidates.

    Args:
        beat_text: The narrative text of the beat where the character appeared.
        role: Required player-provided description of who the character is.
        name: Player-provided name (empty string or None → suggest alternatives).
        want: Player-provided want/goal (empty string or None → suggest alternatives).
        existing_pc_names: PC names to avoid duplicating.
        existing_npc_names: Existing NPC names to avoid duplicating.
        game: Game instance for world document context (optional).
        db: AsyncSession for writing an AIUsageLog entry (optional).
        game_id: ID of the game, used in the usage log (optional).

    Returns:
        (name_suggestions, want_suggestions) — each a list of 0-3 strings.
    """
    system = (
        "You are an NPC creation assistant for a collaborative tabletop RPG. "
        "Help players fill in details for a new non-player character. "
        "Focus on NPCs with complex motivations — a want or need they actively pursue "
        "that could affect how play unfolds. Use the world's established tone and naming "
        "conventions when suggesting names."
    )

    prompt_parts: list[str] = []

    if game is not None and game.world_document and game.world_document.content:
        prompt_parts.append(f"WORLD CONTEXT:\n{game.world_document.content}")

    prompt_parts.append(f"BEAT TEXT:\n{beat_text}")
    prompt_parts.append(f"WHO IS THIS CHARACTER: {role}")

    if existing_pc_names or existing_npc_names:
        all_names = (existing_pc_names or []) + (existing_npc_names or [])
        prompt_parts.append(f"ALREADY TRACKED (do not suggest these): {', '.join(all_names)}")

    if name:
        prompt_parts.append(f"PLAYER-PROVIDED NAME: {name} (suggest alternatives if helpful)")
    else:
        prompt_parts.append("NAME: not yet provided — please suggest 2-3 options")

    if want:
        prompt_parts.append(f"PLAYER-PROVIDED WANT: {want} (suggest alternatives if helpful)")
    else:
        prompt_parts.append(
            "WANT (active goal): not yet provided — please suggest 2-3 options. "
            "Focus on what this character is actively pursuing that could affect the story, "
            "not simple opposition or instinctive aggression."
        )

    model = settings.ai_model_classification
    response, usage = await get_provider().generate_structured(
        system=system,
        prompt="\n\n".join(prompt_parts),
        model=model,
        max_tokens=400,
        response_model=NPCDetailSuggestions,
    )

    if db is not None:
        await _log_usage(
            db,
            feature="suggest_npc_details",
            model=model,
            usage=usage,
            game_id=game_id,
        )

    return response.name_suggestions, response.want_suggestions


async def suggest_character_updates(
    game: Game,
    scene: Scene,
    character: Character,
    *,
    db: AsyncSession | None = None,
    game_id: int | None = None,
) -> list[tuple[str, str, str, list[int]]]:
    """Review completed scene beats and suggest additions to a character sheet.

    Args:
        game: Fully loaded game (world_document, safety_tools loaded).
        scene: Just-completed scene (act, beats with events loaded).
        character: The character whose sheet is being reviewed.
        db: AsyncSession for writing an AIUsageLog entry (optional).
        game_id: ID of the game, used in the usage log (optional).

    Returns:
        A list of (category, suggestion_text, reason, beat_ids) tuples.
        Empty list if no updates suggested.
    """
    from loom.models import BeatStatus

    context_comps = scene_context_components(game, scene)

    # Build safety context
    from loom.ai.context import format_safety_tools_context

    safety_ctx = format_safety_tools_context(game.safety_tools) if game.safety_tools else ""

    # Build labeled beat history so the AI can cite specific beat IDs
    canon_beats = sorted(
        [b for b in scene.beats if b.status == BeatStatus.canon],
        key=lambda b: b.order,
    )
    beat_lines = []
    for beat in canon_beats:
        for event in beat.events:
            if event.content:
                beat_lines.append(f"[Beat #{beat.id}] {event.content}")

    # Build character sheet context
    char_parts = [f"Character Name: {character.name}"]
    if character.description:
        char_parts.append(f"Description:\n{character.description}")
    if character.notes:
        char_parts.append(f"Notes:\n{character.notes}")
    char_sheet = "\n\n".join(char_parts)

    system = (
        "You are a character development assistant for a collaborative tabletop RPG. "
        "Review the completed scene beats and suggest concrete additions to the character "
        "sheet that are directly supported by what happened in the scene. "
        "Only suggest changes grounded in specific events from the beats. "
        "Do not invent events that did not occur. "
        "Reference beats by their ID (e.g., 'Beat #42') in your reason and beat_ids fields. "
        "Respect all safety tool content boundaries."
    )

    prompt_parts: list[str] = []

    if game.world_document and game.world_document.content:
        prompt_parts.append(f"WORLD DOCUMENT:\n{game.world_document.content}")

    prompt_parts.append(
        f"SCENE GUIDING QUESTION: {scene.guiding_question}"
        + (f"\nLocation: {scene.location}" if scene.location else "")
    )

    if beat_lines:
        prompt_parts.append("SCENE BEATS (all canon, labeled with IDs):\n" + "\n".join(beat_lines))
    else:
        prompt_parts.append("SCENE BEATS: (no canon beats recorded)")

    if safety_ctx:
        prompt_parts.append(safety_ctx)

    prompt_parts.append(
        f"CHARACTER SHEET (current state):\n{char_sheet}\n\n"
        "The scene above has just completed. Review the labeled beats for this character "
        "and suggest any additions to their sheet: new relationships, traits revealed "
        "through action, items acquired or lost, or goals that changed. "
        "For each suggestion, include the beat IDs that support it and a brief reason "
        "citing those beats by their ID number."
    )

    model = settings.ai_model_creative
    response, usage = await get_provider().generate_structured(
        system=system,
        prompt="\n\n".join(prompt_parts),
        model=model,
        max_tokens=768,
        response_model=CharacterUpdateResponse,
    )

    if db is not None:
        await _log_usage(
            db,
            feature="suggest_character_updates",
            model=model,
            usage=usage,
            context_components=context_comps + ["character_sheet"],
            game_id=game_id,
        )

    return [(s.category, s.suggestion_text, s.reason, s.beat_ids) for s in response.suggestions]


async def suggest_world_entries(
    beat_text: str,
    existing_entries: list[WorldEntry],
    *,
    game: Game | None = None,
    db: AsyncSession | None = None,
    game_id: int | None = None,
) -> list[tuple[str, str, str, str]]:
    """Scan a canon beat for new world elements worth tracking.

    Args:
        beat_text: The narrative text of the canon beat.
        existing_entries: Current world entries for this game — used to avoid
            re-suggesting things already tracked.
        game: Game instance for world document context (optional).
        db: AsyncSession for writing an AIUsageLog entry (optional).
        game_id: ID of the game, used in the usage log (optional).

    Returns:
        A list of (entry_type, name, description, reason) tuples.
        Empty list if no new trackable elements are found.
    """
    system = (
        "You are a world-tracking assistant for a collaborative tabletop RPG. "
        "Your job is to identify named locations, organizations, significant items, "
        "and concepts introduced in a beat that don't already have world entries. "
        "Only suggest things with clear story relevance that could recur in the fiction. "
        "Do not suggest player characters, NPCs, or generic nouns."
    )

    prompt_parts: list[str] = []

    if game is not None and game.world_document and game.world_document.content:
        prompt_parts.append(f"WORLD DOCUMENT:\n{game.world_document.content}")

    if existing_entries:
        existing_lines = [f"  - {e.name} [{e.entry_type.value}]" for e in existing_entries]
        prompt_parts.append("ALREADY TRACKED (do not suggest these):\n" + "\n".join(existing_lines))

    prompt_parts.append(
        f"CANON BEAT:\n{beat_text}\n\n"
        "Identify any named world elements introduced in this beat that are not already "
        "tracked above and are worth recording as world entries. "
        "Return an empty list if nothing new warrants tracking."
    )

    model = settings.ai_model_classification
    response, usage = await get_provider().generate_structured(
        system=system,
        prompt="\n\n".join(prompt_parts),
        model=model,
        max_tokens=512,
        response_model=WorldEntrySuggestionsResponse,
    )

    if db is not None:
        context_comps = ["beat_text"]
        if game is not None and game.world_document:
            context_comps.append("world_document")
        if existing_entries:
            context_comps.append("existing_entries")
        await _log_usage(
            db,
            feature="suggest_world_entries",
            model=model,
            usage=usage,
            context_components=context_comps,
            game_id=game_id,
        )

    return [(s.entry_type, s.name, s.description, s.reason) for s in response.suggestions]


async def suggest_relationships(
    beat_text: str,
    characters: list[Character],
    npcs: list[NPC],
    world_entries: list[WorldEntry],
    existing_relationship_labels: list[tuple[str, int, str, int, str]],
    *,
    game: Game | None = None,
    db: AsyncSession | None = None,
    game_id: int | None = None,
) -> list[tuple[str, int, str, int, str, str]]:
    """Scan a canon beat for new relationships between already-tracked entities.

    Args:
        beat_text: The narrative text of the canon beat.
        characters: Player characters tracked in this game.
        npcs: NPCs tracked in this game.
        world_entries: World entries tracked in this game.
        existing_relationship_labels: Current relationships as
            (entity_a_type, entity_a_id, entity_b_type, entity_b_id, label) tuples —
            used to avoid re-suggesting duplicates.
        game: Game instance for world document context (optional).
        db: AsyncSession for writing an AIUsageLog entry (optional).
        game_id: ID of the game, used in the usage log (optional).

    Returns:
        A list of (entity_a_type, entity_a_id, entity_b_type, entity_b_id,
        suggested_label, reason) tuples. Empty list if no new relationships found.
    """
    system = (
        "You are a relationship-tracking assistant for a collaborative tabletop RPG. "
        "Your job is to identify relationships between already-tracked entities "
        "(characters, NPCs, and world entries) that are established or strongly implied "
        "by a canon beat. Only suggest relationships grounded in specific events in the beat. "
        "Use the exact entity IDs from the catalogue provided — do not invent IDs."
    )

    prompt_parts: list[str] = []

    if game is not None and game.world_document and game.world_document.content:
        prompt_parts.append(f"WORLD DOCUMENT:\n{game.world_document.content}")

    # Build entity catalogue
    catalogue_lines: list[str] = []
    for c in characters:
        catalogue_lines.append(f"  character:{c.id} — {c.name}")
    for n in npcs:
        catalogue_lines.append(f"  npc:{n.id} — {n.name}")
    for e in world_entries:
        catalogue_lines.append(f"  world_entry:{e.id} — {e.name} [{e.entry_type.value}]")

    if catalogue_lines:
        prompt_parts.append("TRACKED ENTITIES (use these IDs):\n" + "\n".join(catalogue_lines))
    else:
        # No entities to relate — skip the call
        return []

    if existing_relationship_labels:
        existing_lines = [
            f"  {a_type}:{a_id} — {label} — {b_type}:{b_id}"
            for a_type, a_id, b_type, b_id, label in existing_relationship_labels
        ]
        prompt_parts.append(
            "ALREADY TRACKED RELATIONSHIPS (do not re-suggest these):\n" + "\n".join(existing_lines)
        )

    prompt_parts.append(
        f"CANON BEAT:\n{beat_text}\n\n"
        "Identify any new relationships between the tracked entities above that this beat "
        "establishes or strongly implies. Only use entity IDs from the catalogue. "
        "Return an empty list if no clear new relationships are supported by the beat."
    )

    model = settings.ai_model_classification
    response, usage = await get_provider().generate_structured(
        system=system,
        prompt="\n\n".join(prompt_parts),
        model=model,
        max_tokens=512,
        response_model=RelationshipSuggestionsResponse,
    )

    if db is not None:
        context_comps = ["beat_text", "entity_catalogue"]
        if game is not None and game.world_document:
            context_comps.append("world_document")
        if existing_relationship_labels:
            context_comps.append("existing_relationships")
        await _log_usage(
            db,
            feature="suggest_relationships",
            model=model,
            usage=usage,
            context_components=context_comps,
            game_id=game_id,
        )

    return [
        (
            s.entity_a_type,
            s.entity_a_id,
            s.entity_b_type,
            s.entity_b_id,
            s.suggested_label,
            s.reason,
        )
        for s in response.suggestions
    ]


async def generate_scene_narrative(
    game: Game,
    scene: Scene,
    *,
    db: AsyncSession | None = None,
    game_id: int | None = None,
) -> str:
    """Generate a compiled prose narrative for a completed scene.

    Weaves all narrative, roll, oracle, and fortune-roll events from the scene's
    canon beats into a single coherent prose narrative in the game's voice.
    OOC events are excluded.

    Args:
        game: Fully loaded game (world_document, narrative_voice, safety_tools loaded).
        scene: Completed scene (act, beats with events, and characters_present loaded).
        db: AsyncSession for writing an AIUsageLog entry (optional).
        game_id: ID of the game, used in the usage log (optional).

    Returns:
        A prose narrative string for the completed scene.
    """
    scene_ctx = assemble_scene_narrative_context(game, scene)
    context_comps = scene_context_components(game, scene)

    system = (
        "You are a prose author for a collaborative tabletop RPG. "
        "Your role is to write a complete scene narrative that weaves together "
        "all the events of the scene into coherent literary prose — third person, "
        "past tense, matching the game's narrative voice. "
        "Include all significant story events from the provided material. "
        "Do not introduce new events or characters not present in the source. "
        "Respect all safety tool boundaries."
    )

    voice_instruction = (
        f"Apply this narrative voice: {game.narrative_voice}"
        if game.narrative_voice
        else "Match the narrative voice implied by the world document above."
    )

    prompt = f"{scene_ctx}\n\nWrite a complete scene narrative in past tense. {voice_instruction}"

    model = settings.ai_model_creative
    response, usage = await get_provider().generate_structured(
        system=system,
        prompt=prompt,
        model=model,
        max_tokens=1024,
        response_model=SceneNarrativeResponse,
    )

    if db is not None:
        await _log_usage(
            db,
            feature="generate_scene_narrative",
            model=model,
            usage=usage,
            context_components=context_comps,
            game_id=game_id,
        )

    return response.narrative


async def generate_act_narrative(
    game: Game,
    act: Act,
    *,
    db: AsyncSession | None = None,
    game_id: int | None = None,
) -> str:
    """Generate a compiled prose narrative for a completed act.

    Weaves the act's scene narratives (or raw beats as fallback) into a single
    coherent prose narrative framed by the act's guiding question and arc.

    Args:
        game: Fully loaded game (world_document, narrative_voice, safety_tools loaded).
        act: Completed act (scenes with beats and events loaded).
        db: AsyncSession for writing an AIUsageLog entry (optional).
        game_id: ID of the game, used in the usage log (optional).

    Returns:
        A prose narrative string for the completed act.
    """
    act_ctx = assemble_act_narrative_context(game, act)

    system = (
        "You are a prose author for a collaborative tabletop RPG. "
        "Your role is to write a complete act narrative that weaves together "
        "the act's scenes into coherent literary prose — third person, "
        "past tense, matching the game's narrative voice. "
        "Use the act's guiding question as framing for the overall arc. "
        "Do not introduce new events or characters not present in the source. "
        "Respect all safety tool boundaries."
    )

    voice_instruction = (
        f"Apply this narrative voice: {game.narrative_voice}"
        if game.narrative_voice
        else "Match the narrative voice implied by the world document above."
    )
    prompt = (
        f"{act_ctx}\n\n"
        f"Write a complete act narrative in past tense that frames the scenes above "
        f"around the act's guiding question. {voice_instruction}"
    )

    model = settings.ai_model_creative
    response, usage = await get_provider().generate_structured(
        system=system,
        prompt=prompt,
        model=model,
        max_tokens=2048,
        response_model=ActNarrativeResponse,
    )

    if db is not None:
        context_comps: list[str] = ["act_guiding_question", "scene_narratives"]
        if game.world_document and game.world_document.content:
            context_comps.insert(0, "world_document")
        if game.narrative_voice:
            context_comps.append("narrative_voice")
        if game.safety_tools:
            context_comps.append("safety_tools")
        await _log_usage(
            db,
            feature="generate_act_narrative",
            model=model,
            usage=usage,
            context_components=context_comps,
            game_id=game_id,
        )

    return response.narrative
