"""LLM factory — creates provider-specific LLM instances for browser-use."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def create_llm(provider: str, model: str | None = None, api_key: str | None = None, **kwargs):
    """Create an LLM instance for the given provider.

    Returns a chat model instance compatible with browser-use Agent.
    """
    if provider in ("claude", "anthropic"):
        return _create_anthropic(model, api_key=api_key, **kwargs)
    elif provider == "openai":
        return _create_openai(model, api_key=api_key, **kwargs)
    elif provider == "deepseek":
        return _create_deepseek(model, api_key=api_key, **kwargs)
    elif provider == "groq":
        return _create_groq(model, api_key=api_key, **kwargs)
    elif provider == "ollama":
        return _create_ollama(model, **kwargs)
    else:
        raise ValueError(
            f"Unsupported LLM provider: '{provider}'. "
            f"Use one of: openai, anthropic, deepseek, groq, ollama"
        )


def _create_anthropic(model: str | None = None, api_key: str | None = None, **kwargs):
    from browser_use import ChatAnthropic

    extra = {}
    if api_key:
        extra["api_key"] = api_key
    return ChatAnthropic(model=model or "claude-sonnet-4-20250514", **extra, **kwargs)


def _create_openai(model: str | None = None, api_key: str | None = None, **kwargs):
    from browser_use import ChatOpenAI

    extra = {}
    if api_key:
        extra["api_key"] = api_key
    return ChatOpenAI(model=model or "gpt-4o-mini", **extra, **kwargs)


def _create_groq(model: str | None = None, api_key: str | None = None, **kwargs):
    from browser_use import ChatOpenAI

    resolved_key = api_key or os.environ.get("GROQ_API_KEY", "")
    return ChatOpenAI(
        model=model or "meta-llama/llama-4-scout-17b-16e-instruct",
        base_url="https://api.groq.com/openai/v1",
        api_key=resolved_key,
        dont_force_structured_output=True,
        **kwargs,
    )


def _create_deepseek(model: str | None = None, api_key: str | None = None, **kwargs):
    from browser_use import ChatOpenAI

    resolved_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
    return ChatOpenAI(
        model=model or "deepseek-v4-pro",
        base_url="https://api.deepseek.com/v1",
        api_key=resolved_key,
        dont_force_structured_output=True,
        **kwargs,
    )


def _create_ollama(model: str | None = None, base_url: str | None = None, **kwargs):
    from browser_use import ChatOpenAI

    url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    return ChatOpenAI(
        model=model or "llama3",
        base_url=f"{url}/v1",
        api_key="ollama",
        **kwargs,
    )
