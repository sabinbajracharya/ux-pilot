"""LLM factory — creates provider-specific LLM instances for browser-use."""

from __future__ import annotations

import logging

from ux_pilot.config import KNOWN_BASE_URLS, SUGGESTED_MODELS

logger = logging.getLogger(__name__)


def create_llm(
    provider: str,
    model: str,
    api_key: str | None = None,
    base_url: str | None = None,
    **kwargs,
):
    """Create an LLM instance for the given provider.

    Returns a chat model instance compatible with browser-use Agent.

    Args:
        provider: LLM provider name (openai, anthropic, deepseek, groq, ollama, custom).
        model: Model name (required, no default).
        api_key: API key for the provider.
        base_url: Base URL override (required for custom, optional for known providers).
    """
    if not model:
        suggestions = SUGGESTED_MODELS.get(provider, [])
        hint = f" Suggested models: {', '.join(suggestions)}" if suggestions else ""
        raise ValueError(
            f"No LLM model specified for provider '{provider}'.{hint}"
        )

    # Anthropic uses its own browser-use wrapper
    if provider in ("claude", "anthropic"):
        return _create_anthropic(model, api_key=api_key, base_url=base_url, **kwargs)

    # All other providers use ChatOpenAI (OpenAI-compatible API)
    return _create_openai_compatible(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        **kwargs,
    )


def _create_anthropic(
    model: str,
    api_key: str | None = None,
    base_url: str | None = None,
    **kwargs,
):
    from browser_use import ChatAnthropic

    extra: dict = {}
    if api_key:
        extra["api_key"] = api_key
    if base_url:
        extra["base_url"] = base_url
    return ChatAnthropic(model=model, **extra, **kwargs)


def _create_openai_compatible(
    provider: str,
    model: str,
    api_key: str | None = None,
    base_url: str | None = None,
    **kwargs,
):
    from browser_use import ChatOpenAI

    # Resolve base URL: explicit override > known provider URL
    resolved_url = base_url or KNOWN_BASE_URLS.get(provider)
    if not resolved_url:
        raise ValueError(
            f"No base URL known for provider '{provider}'.\n"
            f"Provide one via --llm-base-url or set llm_base_url in ~/.ux-pilot/config.yaml\n"
            f"Known providers with pre-mapped URLs: {', '.join(KNOWN_BASE_URLS)}"
        )

    extra: dict = {}
    if api_key:
        extra["api_key"] = api_key

    # Non-OpenAI providers may not support structured output
    if provider not in ("openai",):
        kwargs.setdefault("dont_force_structured_output", True)

    return ChatOpenAI(
        model=model,
        base_url=resolved_url,
        **extra,
        **kwargs,
    )
