"""Tests for PersonaPromptBuilder."""

from ux_pilot.personas.prompt_builder import PersonaPromptBuilder
from ux_pilot.personas.traits import TRAIT_NAMES


def _default_traits(**overrides: int) -> dict[str, int]:
    traits = {name: 50 for name in TRAIT_NAMES}
    traits.update(overrides)
    return traits


class TestPersonaPromptBuilder:
    def setup_method(self):
        self.builder = PersonaPromptBuilder()

    def test_build_with_defaults(self):
        prompt = self.builder.build(
            traits=_default_traits(),
            task_description="Browse the homepage",
        )
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_build_includes_task(self):
        task = "Find the pricing page and compare plans"
        prompt = self.builder.build(
            traits=_default_traits(),
            task_description=task,
        )
        assert task in prompt

    def test_build_includes_url(self):
        url = "https://example.com"
        prompt = self.builder.build(
            traits=_default_traits(),
            task_description="Browse",
            target_url=url,
        )
        assert "example.com" in prompt

    def test_build_with_high_neuroticism(self):
        low_n = self.builder.build(
            traits=_default_traits(neuroticism=10),
            task_description="Browse",
        )
        high_n = self.builder.build(
            traits=_default_traits(neuroticism=90),
            task_description="Browse",
        )
        assert low_n != high_n

    def test_build_with_demographics(self):
        prompt = self.builder.build(
            traits=_default_traits(),
            task_description="Browse",
            demographics={"occupation": "software engineer"},
        )
        assert "software engineer" in prompt
