"""Tests for Settings configuration."""

import os

import pytest

from ux_pilot.config import Settings


class TestSettings:
    def test_defaults_are_none(self):
        """Provider and model must be explicitly set — no defaults."""
        settings = Settings()
        assert settings.llm_provider is None
        assert settings.llm_model is None
        assert settings.llm_base_url is None
        assert settings.max_actions == 50
        assert settings.headed is False

    def test_load_with_overrides(self):
        settings = Settings.load(llm_provider="anthropic", llm_model="claude-sonnet-4-20250514")
        assert settings.llm_provider == "anthropic"
        assert settings.llm_model == "claude-sonnet-4-20250514"

    def test_validate_llm_missing_provider(self):
        settings = Settings()
        with pytest.raises(ValueError, match="No LLM provider specified"):
            settings.validate_llm()

    def test_validate_llm_missing_model(self):
        settings = Settings(llm_provider="deepseek")
        with pytest.raises(ValueError, match="No LLM model specified"):
            settings.validate_llm()

    def test_validate_llm_custom_requires_base_url(self):
        settings = Settings(llm_provider="custom", llm_model="my-model")
        with pytest.raises(ValueError, match="llm-base-url is required"):
            settings.validate_llm()

    def test_validate_llm_custom_with_base_url_passes(self):
        settings = Settings(
            llm_provider="custom", llm_model="my-model",
            llm_base_url="https://my-api.com/v1",
        )
        settings.validate_llm()  # Should not raise

    def test_validate_llm_known_provider_passes(self):
        settings = Settings(llm_provider="deepseek", llm_model="deepseek-chat")
        settings.validate_llm()  # Should not raise

    def test_get_api_key_from_field(self):
        settings = Settings(llm_api_key="sk-test")
        assert settings.get_api_key() == "sk-test"

    def test_get_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "sk-env-test")
        settings = Settings()
        assert settings.get_api_key() == "sk-env-test"

    def test_get_api_key_field_priority(self, monkeypatch):
        """llm_api_key field takes priority over env var."""
        monkeypatch.setenv("LLM_API_KEY", "sk-env")
        settings = Settings(llm_api_key="sk-field")
        assert settings.get_api_key() == "sk-field"

    def test_llm_base_url_passed_through(self):
        settings = Settings.load(llm_base_url="https://custom-api.com/v1")
        assert settings.llm_base_url == "https://custom-api.com/v1"
