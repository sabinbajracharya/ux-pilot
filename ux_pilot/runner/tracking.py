"""Token tracking via composition (not monkey-patching)."""

from __future__ import annotations

from typing import Any


class TokenTrackingWrapper:
    """Wraps an LLM instance to track token usage via ainvoke interception.

    Uses composition — forwards all attribute access to the underlying LLM
    while intercepting ainvoke for token counting.
    """

    def __init__(self, llm: Any, acc: dict[str, int]):
        self._llm = llm
        self._acc = acc

    async def ainvoke(self, messages: Any, output_format: Any = None, **kwargs: Any) -> Any:
        result = await self._llm.ainvoke(messages, output_format=output_format, **kwargs)
        if result and getattr(result, "usage", None):
            self._acc["input"] += getattr(result.usage, "prompt_tokens", 0) or 0
            self._acc["output"] += getattr(result.usage, "completion_tokens", 0) or 0
        return result

    def __getattr__(self, name: str) -> Any:
        return getattr(self._llm, name)
