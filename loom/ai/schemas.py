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
