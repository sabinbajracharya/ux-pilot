"""Tests for LLM-driven persona state generation."""

import pytest
from ux_pilot.personas.state_generator import PersonaStateGenerator, _format_traits_summary
from ux_pilot.personas.translator import TraitTranslator


class TestFormatTraitsSummary:
    def test_sorts_by_extremity(self):
        traits = {"openness": 50, "neuroticism": 95, "tech_literacy": 15}
        summary = _format_traits_summary(traits)
        lines = summary.split("\n")
        # Most extreme first: neuroticism (95) or tech_literacy (15)
        assert "neuroticism" in lines[0] or "tech_literacy" in lines[0]
        # Least extreme last: openness (50)
        assert "openness" in lines[-1]

    def test_includes_level_labels(self):
        summary = _format_traits_summary({"neuroticism": 90, "tech_literacy": 20})
        assert "very high" in summary
        assert "very low" in summary

    def test_limits_to_6_traits(self):
        traits = {name: 50 for name in [
            "openness", "conscientiousness", "extraversion", "agreeableness",
            "neuroticism", "tech_literacy", "decision_speed", "attention_span",
            "price_sensitivity",
        ]}
        summary = _format_traits_summary(traits)
        assert len(summary.split("\n")) == 6


class TestPersonaStateGenerator:
    @pytest.fixture
    def generator(self):
        traits = {"neuroticism": 90, "tech_literacy": 25, "openness": 30, "conscientiousness": 50}
        translator = TraitTranslator()
        ruleset = translator.translate(traits)
        return PersonaStateGenerator(
            persona_name="Anxious First-Timer",
            traits=traits,
            ruleset=ruleset,
            task="Find a mystery book",
        )

    def test_build_prompt_includes_persona_name(self, generator):
        prompt = generator.build_prompt(
            current_url="https://example.com",
            recent_actions=[{"type": "click", "desc": "Clicked mystery category"}],
            frustration=30,
            current_emotion="anxious",
        )
        assert "Anxious First-Timer" in prompt
        assert "neuroticism" in prompt
        assert "mystery book" in prompt

    def test_build_prompt_includes_recent_action(self, generator):
        prompt = generator.build_prompt(
            current_url="https://example.com",
            recent_actions=[{"type": "click", "desc": "Clicked mystery category"}],
            frustration=30,
            current_emotion="anxious",
        )
        assert "Clicked mystery category" in prompt

    def test_compound_label(self, generator):
        assert generator.compound_label is not None

    def test_fallback_state_returns_expected_keys(self, generator):
        result = PersonaStateGenerator.fallback_state("confused", 50, generator._ruleset)
        assert "emotion" in result
        assert "monologue" in result
        assert "frustrationDelta" in result
        assert result["emotion"] == "confused"
