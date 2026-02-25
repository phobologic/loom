"""Unit tests for the dice rolling engine."""

import pytest

from loom.dice import DiceError, parse, roll


class TestParse:
    def test_simple_notation(self) -> None:
        assert parse("2d6") == (2, 6, 0)

    def test_implicit_one_die(self) -> None:
        assert parse("d20") == (1, 20, 0)

    def test_positive_modifier(self) -> None:
        assert parse("2d6+3") == (2, 6, 3)

    def test_negative_modifier(self) -> None:
        assert parse("3d10-2") == (3, 10, -2)

    def test_case_insensitive(self) -> None:
        assert parse("2D6") == (2, 6, 0)

    def test_large_valid(self) -> None:
        assert parse("10d100+50") == (10, 100, 50)

    def test_invalid_word(self) -> None:
        with pytest.raises(DiceError):
            parse("roll some dice")

    def test_invalid_zero_dice(self) -> None:
        with pytest.raises(DiceError):
            parse("0d6")

    def test_invalid_zero_sides(self) -> None:
        with pytest.raises(DiceError):
            parse("2d0")

    def test_invalid_empty(self) -> None:
        with pytest.raises(DiceError):
            parse("")

    def test_too_many_dice(self) -> None:
        with pytest.raises(DiceError, match="Too many dice"):
            parse("101d6")

    def test_too_many_sides(self) -> None:
        with pytest.raises(DiceError, match="Too many sides"):
            parse("2d1001")


class TestRoll:
    def test_d6_in_range(self) -> None:
        for _ in range(20):
            assert 1 <= roll("d6") <= 6

    def test_2d6_in_range(self) -> None:
        for _ in range(20):
            assert 2 <= roll("2d6") <= 12

    def test_modifier_applied(self) -> None:
        for _ in range(20):
            result = roll("1d1+5")
            assert result == 6  # 1d1 always 1, plus 5

    def test_negative_modifier(self) -> None:
        for _ in range(20):
            result = roll("1d1-1")
            assert result == 0  # 1d1 always 1, minus 1

    def test_invalid_notation_raises(self) -> None:
        with pytest.raises(DiceError):
            roll("bad notation")
