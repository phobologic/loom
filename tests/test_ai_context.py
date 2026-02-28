"""Tests for loom.ai.context helper functions."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from loom.ai.context import assemble_scene_context, format_tension_context


class TestFormatTensionContext:
    def test_low_tension_boundary_1(self):
        result = format_tension_context(1)
        assert result.startswith("CURRENT TENSION: 1/9")
        assert "low" in result
        assert "subtle" in result

    def test_low_tension_boundary_3(self):
        result = format_tension_context(3)
        assert result.startswith("CURRENT TENSION: 3/9")
        assert "low" in result
        assert "seed-planting" in result

    def test_mid_tension_boundary_4(self):
        result = format_tension_context(4)
        assert result.startswith("CURRENT TENSION: 4/9")
        assert "moderate" in result
        assert "balanced" in result

    def test_mid_tension_boundary_6(self):
        result = format_tension_context(6)
        assert result.startswith("CURRENT TENSION: 6/9")
        assert "moderate" in result

    def test_high_tension_boundary_7(self):
        result = format_tension_context(7)
        assert result.startswith("CURRENT TENSION: 7/9")
        assert "high" in result
        assert "dramatic" in result

    def test_high_tension_boundary_9(self):
        result = format_tension_context(9)
        assert result.startswith("CURRENT TENSION: 9/9")
        assert "high" in result
        assert "escalating" in result


def _make_scene(characters_present=None, beats=None):
    """Build a minimal scene mock for assemble_scene_context."""
    act = SimpleNamespace(guiding_question="What is at stake?")
    scene = SimpleNamespace(
        act=act,
        guiding_question="What do the characters want?",
        location=None,
        characters_present=characters_present or [],
        beats=beats or [],
    )
    return scene


def _make_game(safety_tools=None, narrative_voice=None):
    """Build a minimal game mock for assemble_scene_context."""
    return SimpleNamespace(
        world_document=None, safety_tools=safety_tools or [], narrative_voice=narrative_voice
    )


class TestAssembleSceneContextVoiceNotes:
    def test_voice_notes_included_when_set(self):
        char = SimpleNamespace(
            name="Mira",
            description="A cautious scout",
            voice_notes="terse and clipped",
        )
        scene = _make_scene(characters_present=[char])
        result = assemble_scene_context(_make_game(), scene)
        assert "CHARACTERS IN SCENE" in result
        assert "Mira" in result
        assert "A cautious scout" in result
        assert "[Voice: terse and clipped]" in result

    def test_voice_notes_absent_when_none(self):
        char = SimpleNamespace(
            name="Elara",
            description="A bold merchant",
            voice_notes=None,
        )
        scene = _make_scene(characters_present=[char])
        result = assemble_scene_context(_make_game(), scene)
        assert "CHARACTERS IN SCENE" in result
        assert "Elara" in result
        assert "[Voice:" not in result

    def test_voice_notes_without_description(self):
        char = SimpleNamespace(
            name="Ghost",
            description=None,
            voice_notes="cryptic and sparse",
        )
        scene = _make_scene(characters_present=[char])
        result = assemble_scene_context(_make_game(), scene)
        assert "Ghost" in result
        assert "[Voice: cryptic and sparse]" in result
