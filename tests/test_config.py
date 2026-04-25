"""Tests for Settings configuration."""

from ux_pilot.config import Settings


class TestSettings:
    def test_default_settings(self):
        settings = Settings()
        assert settings.llm_provider == "openai"
        assert settings.max_actions == 50
        assert settings.headed is False

    def test_load_with_overrides(self):
        settings = Settings.load(llm_provider="anthropic", llm_model="claude-sonnet-4-20250514")
        assert settings.llm_provider == "anthropic"
        assert settings.llm_model == "claude-sonnet-4-20250514"
