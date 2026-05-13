"""Integration tests for CLI command implementations."""

import os

import pytest
from ux_pilot.analysis.models import RunResult
from ux_pilot.personas.loader import PersonaTemplate

# Sample persona for testing
SAMPLE_TRAITS = {
    "openness": 50, "conscientiousness": 70, "extraversion": 50,
    "agreeableness": 50, "neuroticism": 40,
    "tech_literacy": 60, "decision_speed": 50,
    "attention_span": 70, "price_sensitivity": 30,
}

SAMPLE_TEMPLATE = PersonaTemplate(
    name="Test Persona",
    description="A test persona",
    category="Test",
    traits=SAMPLE_TRAITS,
)


class TestAnalyzeResult:
    def test_handles_missing_model(self):
        """analyze_result should handle missing model gracefully (analysis is best-effort)."""
        from ux_pilot.runner.commands import analyze_result
        from ux_pilot.config import Settings
        from rich.console import Console

        settings = Settings(llm_provider="openai", llm_model=None)
        result = RunResult(
            persona_name="Test", target_url="http://x.com",
            task_description="test", task_completed=True,
            summary="Done", total_steps=2, total_duration_seconds=10,
        )
        console = Console(width=80, force_terminal=True, color_system=None)
        # Should not crash — analysis gracefully skips when model is missing
        analyze_result(result, settings, console)


class TestSaveToHistory:
    def test_save_does_not_crash(self, tmp_path):
        """save_to_history should handle missing DB gracefully."""
        from ux_pilot.runner.commands import save_to_history
        from rich.console import Console

        result = RunResult(
            persona_name="Test", target_url="http://x.com",
            task_description="test", task_completed=True,
            summary="Done", total_steps=2, total_duration_seconds=10,
        )
        console = Console(width=80, force_terminal=True, color_system=None)
        save_to_history(result, console)  # Should not crash


class TestRunSingleSetup:
    def test_settings_load_cli_overrides(self):
        """CLI overrides should take precedence over defaults."""
        from ux_pilot.config import Settings

        settings = Settings.load(
            llm_provider="deepseek",
            llm_model="deepseek-chat",
            max_actions=30,
        )
        assert settings.llm_provider == "deepseek"
        assert settings.llm_model == "deepseek-chat"
        assert settings.max_actions == 30

    def test_settings_api_key_resolution(self):
        """get_api_key should resolve from LLM_API_KEY env var."""
        from ux_pilot.config import Settings

        os.environ["LLM_API_KEY"] = "test-key"
        try:
            settings = Settings(llm_provider="deepseek", llm_model="deepseek-chat")
            assert settings.get_api_key() == "test-key"
        finally:
            del os.environ["LLM_API_KEY"]
