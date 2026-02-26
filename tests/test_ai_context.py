"""Tests for loom.ai.context helper functions."""

import pytest

from loom.ai.context import format_tension_context


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
