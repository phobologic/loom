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
