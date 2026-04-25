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

    # LLM configuration
    llm_provider: str = Field(default="openai", description="LLM provider: openai, anthropic, groq, ollama")
    llm_model: str | None = Field(default=None, description="Model name (provider-specific default if not set)")
    llm_api_key: str | None = Field(default=None, description="API key (also reads OPENAI_API_KEY etc.)")

    # Browser settings
    headed: bool = Field(default=False, description="Show browser window during run")

    # Execution limits
    max_actions: int = Field(default=50, description="Maximum actions per run")
    max_duration_minutes: int = Field(default=5, description="Maximum run duration in minutes")

    # Output
    output_dir: str | None = Field(default=None, description="Directory to save results")

    # Ollama-specific
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama server URL")

    @classmethod
    def load(cls, **cli_overrides: Any) -> Settings:
        """Load settings with full cascade: CLI > env > config file > defaults."""
        yaml_config = _load_yaml_config()
        # Filter out None CLI overrides so they don't mask yaml/env values
        filtered_cli = {k: v for k, v in cli_overrides.items() if v is not None}
        merged = {**yaml_config, **filtered_cli}
        return cls(**merged)

    def get_api_key(self) -> str | None:
        """Resolve API key from settings or provider-specific env vars."""
        if self.llm_api_key:
            return self.llm_api_key
        provider_env_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "groq": "GROQ_API_KEY",
        }
        env_var = provider_env_map.get(self.llm_provider)
        if env_var:
            return os.environ.get(env_var)
        return None
