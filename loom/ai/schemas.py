"""Pydantic response models for all AI functions.

Format constraints (counts, allowed values, output shape) live here — not in
prompt text. Behavioral instructions (tone, world context) stay in prompts.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class OracleResponse(BaseModel):
    interpretations: list[str] = Field(
        min_length=3,
        max_length=3,
        description=(
            "Exactly 3 distinct, evocative interpretations inspired by the question "
            "and word seeds. Each should suggest a possible truth, consequence, or "
            "revelation that fits the world and advances the story."
        ),
    )


class BeatClassification(BaseModel):
    significance: Literal["minor", "major"] = Field(
        description=(
            "'minor' for routine actions or small moments; "
            "'major' for significant plot points, character revelations, or world-changing events."
        ),
    )


class SynthesisResponse(BaseModel):
    text: str = Field(
        description=(
            "A single cohesive paragraph in present-tense world-building prose that captures "
            "the group's shared vision for this prompt. No heading, no preamble, no attribution."
        ),
    )


class WorldDocumentResponse(BaseModel):
    markdown: str = Field(
        description=(
            "A structured Markdown world document with sections: World Overview, "
            "Tone & Aesthetic, Setting, Central Tensions, and Key Themes. "
            "Be concrete and usable at the table."
        ),
    )


class ProseExpansion(BaseModel):
    prose: str = Field(
        description=(
            "A polished, literary rewrite of the submitted beat text in third-person "
            "collaborative-fiction prose. Preserve every fact, action, and event from the "
            "original — only elevate the language and match the game's established narrative "
            "voice. Do not introduce new events, characters, or information."
        ),
    )


class SceneNarrativeResponse(BaseModel):
    narrative: str = Field(
        description=(
            "A complete prose narrative of the scene, written as literary collaborative-fiction "
            "in third-person past tense. Weave all the provided events into a coherent, "
            "scene-length narrative. Match the game's established narrative voice. "
            "Do not introduce new events or characters not present in the source material."
        ),
    )


class ActNarrativeResponse(BaseModel):
    narrative: str = Field(
        description=(
            "A complete prose narrative of the act, written as literary collaborative-fiction "
            "in third-person past tense. Weave the provided scene narratives into a coherent "
            "act-length narrative that reflects the act's guiding question and arc. "
            "Match the game's established narrative voice. "
            "Do not introduce events not present in the source material."
        ),
    )


class ConsistencyCheckResponse(BaseModel):
    flags: list[str] = Field(
        max_length=5,
        description=(
            "Potential inconsistencies between the beat and the established fiction. "
            "Each flag is a single, specific, player-facing concern — e.g. "
            "'You rolled a partial success but this reads like a full success' or "
            "'The warehouse was established as locked in a prior beat'. "
            "Return an empty list if the beat is consistent with the fiction. "
            "Do NOT flag creative choices, tone, or style — only factual contradictions, "
            "safety-tool violations, and roll-result mismatches."
        ),
    )


class CharacterUpdateSuggestionItem(BaseModel):
    category: Literal["relationship", "trait", "item", "goal"] = Field(
        description=(
            "'relationship' for new or changed bonds with other characters or factions; "
            "'trait' for personality qualities, skills, or flaws revealed through action; "
            "'item' for objects acquired, lost, or altered; "
            "'goal' for changed or newly established motivations."
        ),
    )
    suggestion_text: str = Field(
        description=(
            "A concrete, specific update for the character sheet in 1-3 sentences. "
            "Write as a factual addition the player can accept as-is. "
            "Ground it in what actually happened in the scene beats provided."
        ),
    )
    reason: str = Field(
        description=(
            "Brief rationale explaining which specific beat(s) support this suggestion. "
            "Reference beats by their ID as shown in the prompt (e.g., 'Beat #42 shows ...'). "
            "1-2 sentences."
        ),
    )
    beat_ids: list[int] = Field(
        default_factory=list,
        description=(
            "IDs of the specific beats that support this suggestion. "
            "Use the numeric IDs provided in the prompt (e.g., [42, 47]). "
            "Leave empty only if the suggestion follows from the overall scene arc "
            "rather than specific beats."
        ),
    )


class CharacterUpdateResponse(BaseModel):
    suggestions: list[CharacterUpdateSuggestionItem] = Field(
        max_length=4,
        description=(
            "Targeted updates for this character based on recent scene beats. "
            "Return an empty list if no meaningful changes occurred for this character. "
            "Each suggestion must be grounded in specific events from the scene."
        ),
    )


class NPCDetailSuggestions(BaseModel):
    name_suggestions: list[str] = Field(
        max_length=3,
        description=(
            "2-3 name suggestions for this character based on their role and the beat context. "
            "Match the world's naming conventions and tone. "
            "Return an empty list if a name was already provided and no alternatives are needed."
        ),
    )
    want_suggestions: list[str] = Field(
        max_length=3,
        description=(
            "2-3 suggestions for what this character wants — an active goal or need they are "
            "pursuing that could affect play. Each should be a single concrete sentence. "
            "Return an empty list if a want was already provided and no alternatives are needed."
        ),
    )


class WorldEntrySuggestionItem(BaseModel):
    entry_type: Literal["location", "faction", "item", "concept", "other"] = Field(
        description=(
            "'location' for named places (buildings, cities, regions, landmarks); "
            "'faction' for organizations, groups, guilds, or factions; "
            "'item' for significant named objects, artifacts, or items; "
            "'concept' for named ideas, religions, schools of thought, or cultural concepts; "
            "'other' for significant named things that don't fit the above categories."
        ),
    )
    name: str = Field(
        description=(
            "The name of the world element as it appears in the beat text. "
            "Use the exact name from the fiction, not a paraphrase. "
            "Maximum 150 characters."
        ),
    )
    description: str = Field(
        description=(
            "A 1-3 sentence description of this element grounded in what the beat revealed. "
            "Write in present-tense world-building prose. Do not speculate beyond the beat."
        ),
    )
    reason: str = Field(
        description=(
            "One sentence explaining why this element warrants a world entry — "
            "e.g. 'Named location introduced in this beat with significant story relevance.' "
            "Be concise and direct."
        ),
    )


class WorldEntrySuggestionsResponse(BaseModel):
    suggestions: list[WorldEntrySuggestionItem] = Field(
        max_length=4,
        description=(
            "New world elements introduced in this beat that don't already have entries. "
            "Only suggest named locations, organizations, significant items, or concepts "
            "that could recur in the fiction and are worth tracking. "
            "Return an empty list if no new trackable elements are introduced."
        ),
    )


class RelationshipSuggestionItem(BaseModel):
    entity_a_type: Literal["character", "npc", "world_entry"] = Field(
        description=(
            "Type of the first entity in the relationship: "
            "'character' for player characters, 'npc' for non-player characters, "
            "'world_entry' for locations, factions, items, or concepts."
        ),
    )
    entity_a_id: int = Field(
        description="Numeric ID of the first entity, as listed in the provided entity catalogue.",
    )
    entity_b_type: Literal["character", "npc", "world_entry"] = Field(
        description="Type of the second entity in the relationship.",
    )
    entity_b_id: int = Field(
        description="Numeric ID of the second entity, as listed in the provided entity catalogue.",
    )
    suggested_label: str = Field(
        description=(
            "A short, evocative relationship label describing how entity A relates to entity B "
            "— e.g. 'rivals with', 'sworn to protect', 'secretly fears', 'owes a debt to'. "
            "Phrase it as a verb or short phrase. Maximum 100 characters."
        ),
    )
    reason: str = Field(
        description=(
            "One sentence explaining which event in the beat supports this relationship. "
            "Be specific and cite the beat text."
        ),
    )


class RelationshipSuggestionsResponse(BaseModel):
    suggestions: list[RelationshipSuggestionItem] = Field(
        max_length=4,
        description=(
            "New relationships between already-tracked entities that are supported by this beat. "
            "Only suggest relationships grounded in specific events in the beat text. "
            "Both entities must be from the provided catalogue — do not invent IDs. "
            "Return an empty list if no clear new relationships are established."
        ),
    )


class NarrativeVoiceSuggestions(BaseModel):
    voices: list[str] = Field(
        min_length=3,
        max_length=4,
        description=(
            "3-4 distinct narrative voice options suited to this game's genre and tone. "
            "Each option is a 1-2 sentence description of a prose style — e.g. "
            "'Terse and atmospheric: short sentences, sensory detail, little interiority.' "
            "Make each option clearly distinct so the group can choose. "
            "Do not number or label them — each entry is just the description."
        ),
    )


class TensionAdjustmentResponse(BaseModel):
    delta: Literal[-1, 0, 1] = Field(
        description=(
            "-1 if the scene resolved tension "
            "(conflict defused, goals achieved, characters in control); "
            "+1 if the scene escalated tension "
            "(plans failed, new threats emerged, surprises dominated); "
            "0 if results were mixed or ambiguous."
        ),
    )
    rationale: str = Field(
        description=(
            "Player-facing explanation of the recommendation in 2-4 sentences. "
            "Be transparent about which factors drove the choice: scene outcome, "
            "recent narrative arc, fortune-roll feedback loop, or extreme tension correction. "
            "Write as if addressing the players directly."
        ),
    )
