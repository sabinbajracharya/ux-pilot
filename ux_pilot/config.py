"""Configuration management with cascade: CLI args > env vars > config file > defaults."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_DIR = Path.home() / ".ux-pilot"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

# Supported LLM providers and their known API base URLs.
KNOWN_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "ollama": "http://localhost:11434/v1",
}

# Suggested models shown in error messages when no model is specified.
SUGGESTED_MODELS: dict[str, list[str]] = {
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
    "anthropic": ["claude-sonnet-4-20250514", "claude-3-5-sonnet-latest"],
    "deepseek": ["deepseek-chat", "deepseek-reasoner"],
    "groq": ["meta-llama/llama-4-scout-17b-16e-instruct", "llama-3.3-70b-versatile"],
    "ollama": ["llama3.2", "llama3", "mistral"],
}


def _load_yaml_config() -> dict[str, Any]:
    """Load settings from ~/.ux-pilot/config.yaml if it exists."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            data = yaml.safe_load(f) or {}
            return data
    return {}


class Settings(BaseSettings):
    """Application settings with env var + config file support."""

    model_config = SettingsConfigDict(
        env_prefix="UX_PILOT_",
        env_file=".env",
        extra="ignore",
    )

    # LLM configuration — no defaults; must be explicitly provided.
    llm_provider: str | None = Field(
        default=None,
        description="LLM provider: openai, anthropic, deepseek, groq, ollama, custom",
    )
    llm_model: str | None = Field(
        default=None,
        description="Model name (required, no default)",
    )
    llm_api_key: str | None = Field(
        default=None,
        description="API key (reads UX_PILOT_LLM_API_KEY env var)",
    )
    llm_base_url: str | None = Field(
        default=None,
        description="Base URL override for LLM provider API (required for custom provider)",
    )

    # Browser settings
    headed: bool = Field(default=False, description="Show browser window during run")

    # Execution limits
    max_actions: int = Field(default=50, description="Maximum actions per run")
    max_duration_minutes: int = Field(default=5, description="Maximum run duration in minutes")

    # Output
    output_dir: str | None = Field(default=None, description="Directory to save results")

    @classmethod
    def load(cls, **cli_overrides: Any) -> Settings:
        """Load settings with full cascade: CLI > env > config file > defaults."""
        yaml_config = _load_yaml_config()
        # Filter out None CLI overrides so they don't mask yaml/env values
        filtered_cli = {k: v for k, v in cli_overrides.items() if v is not None}
        merged = {**yaml_config, **filtered_cli}
        return cls(**merged)

    def get_api_key(self) -> str | None:
        """Resolve API key from settings or LLM_API_KEY env var."""
        if self.llm_api_key:
            return self.llm_api_key
        return os.environ.get("LLM_API_KEY")

    def validate_llm(self) -> None:
        """Validate LLM configuration. Raises ValueError with helpful message on failure.

        Called early in CLI commands to fail fast before browser/network setup.
        """
        # Provider is required
        if not self.llm_provider:
            raise ValueError(
                "No LLM provider specified.\n"
                "Specify one via:\n"
                "  --llm-provider <name>\n"
                "  UX_PILOT_LLM_PROVIDER environment variable\n"
                "  llm_provider in ~/.ux-pilot/config.yaml\n"
                "Supported providers: openai, anthropic, deepseek, groq, ollama\n"
                "(or 'custom' with --llm-base-url for any OpenAI-compatible API)"
            )

        # Model is required
        if not self.llm_model:
            suggestions = SUGGESTED_MODELS.get(self.llm_provider, [])
            hint = ""
            if suggestions:
                hint = f"\nSuggested models for '{self.llm_provider}': {', '.join(suggestions)}"
            raise ValueError(
                f"No LLM model specified for provider '{self.llm_provider}'.\n"
                f"Specify one via:\n"
                f"  --llm-model <name>\n"
                f"  UX_PILOT_LLM_MODEL environment variable\n"
                f"  llm_model in ~/.ux-pilot/config.yaml{hint}"
            )

        # Custom provider requires base URL
        if self.llm_provider == "custom" and not self.llm_base_url:
            raise ValueError(
                "--llm-base-url is required when using --llm-provider custom.\n"
                "Example: --llm-provider custom --llm-base-url https://my-api.com/v1 --llm-model my-model"
            )
