"""Tests for the trait system."""

import pytest

from ux_pilot.personas.traits import (
    TRAIT_EMOJI,
    TRAIT_NAMES,
    TRAIT_SHORT,
    trait_level_label,
    validate_traits,
)


class TestTraitValidation:
    def test_valid_traits_accepted(self):
        traits = {name: 50 for name in TRAIT_NAMES}
        result = validate_traits(traits)
        assert all(0 <= v <= 100 for v in result.values())

    def test_boundary_values(self):
        traits = {"openness": 0, "neuroticism": 100}
        result = validate_traits(traits)
        assert result["openness"] == 0
        assert result["neuroticism"] == 100

    def test_missing_traits_default_to_50(self):
        result = validate_traits({})
        for name in TRAIT_NAMES:
            assert result[name] == 50

    def test_below_zero_raises(self):
        with pytest.raises(ValueError, match="must be 0-100"):
            validate_traits({"openness": -1})

    def test_above_100_raises(self):
        with pytest.raises(ValueError, match="must be 0-100"):
            validate_traits({"openness": 101})

    def test_non_numeric_raises(self):
        with pytest.raises(ValueError, match="must be a number"):
            validate_traits({"openness": "high"})

    def test_float_values_truncated(self):
        result = validate_traits({"openness": 75.9})
        assert result["openness"] == 75


class TestTraitLevelLabels:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (0, "Low"),
            (25, "Low"),
            (50, "Med-High"),
            (75, "High"),
            (100, "High"),
        ],
    )
    def test_trait_level_label(self, value: int, expected: str):
        assert trait_level_label(value) == expected


class TestTraitMetadata:
    def test_all_traits_have_emoji(self):
        for name in TRAIT_NAMES:
            assert name in TRAIT_EMOJI, f"Missing emoji for trait: {name}"
            assert len(TRAIT_EMOJI[name]) > 0

    def test_all_traits_have_short(self):
        for name in TRAIT_NAMES:
            assert name in TRAIT_SHORT, f"Missing short name for trait: {name}"
            assert len(TRAIT_SHORT[name]) > 0
