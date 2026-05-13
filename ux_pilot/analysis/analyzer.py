"""Post-run AI analyzer — generates summary and UX recommendations via LLM."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from ux_pilot.analysis.models import Recommendation, RunResult

logger = logging.getLogger(__name__)


def _strip_json_fences(text: str) -> str:
    """Remove markdown code fences from LLM output."""
    return re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip(), flags=re.MULTILINE).strip()


def _parse_json(text: str) -> dict:
    """Best-effort JSON extraction from LLM output."""
    try:
        return json.loads(_strip_json_fences(text))
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {}


def _build_litellm_model(provider: str, model: str | None) -> str:
    """Build litellm model string (e.g. 'deepseek/deepseek-chat').

    Falls back to provider-appropriate defaults when model is not specified.
    """
    resolved = model or {
        "openai": "gpt-4o-mini",
        "anthropic": "claude-sonnet-4-20250514",
        "deepseek": "deepseek-chat",
        "groq": "llama-3.3-70b-versatile",
        "ollama": "llama3.2",
    }.get(provider, "gpt-4o-mini")

    if resolved.startswith(f"{provider}/"):
        return resolved
    return f"{provider}/{resolved}"


@dataclass
class AnalysisResult:
    """Result of post-run AI analysis."""

    summary: str = ""
    recommendations: list[Recommendation] = None  # type: ignore[assignment]
    satisfaction_score: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []


async def analyze_run(
    result: RunResult,
    provider: str = "openai",
    model: str | None = None,
    api_key: str | None = None,
) -> AnalysisResult:
    """Run post-completion AI analysis: summary + recommendations.

    Makes 1 LLM call with a structured prompt to get both summary and recommendations.
    """
    try:
        from litellm import acompletion
    except ImportError:
        logger.warning("litellm not installed, skipping analysis")
        return AnalysisResult(summary="LLM not available for analysis")

    litellm_model = _build_litellm_model(provider, model)

    # Build context from run data
    actions_text = "\n".join(
        f"  Step {a.sequence}: [{a.emotion}] {a.action_type} — "
        f"{'✓' if a.was_successful else '✗ FAILED'} — {a.description[:100]}"
        for a in result.actions
    )

    emotion_journey = " → ".join(result.emotion_journey) if result.emotion_journey else "N/A"
    friction_text = "\n".join(f"  • {fp}" for fp in result.friction_points) if result.friction_points else "None"

    system_prompt = """You are a world-class UX researcher. Analyze an AI persona's browsing session and provide:
1. A narrative summary (2-3 sentences, from the persona's perspective)
2. 3-5 prioritized UX improvement recommendations with evidence
3. A satisfaction score (0-100)

Respond in JSON ONLY — no markdown, no explanation:
{
  "summary": "Narrative summary...",
  "satisfactionScore": 65,
  "recommendations": [
    {
      "title": "Short title",
      "description": "What to fix and why",
      "priority": "high|medium|low",
      "evidence": "Which steps/behaviors support this"
    }
  ]
}"""

    user_prompt = f"""Persona: {result.persona_name}
Target URL: {result.target_url}
Task: {result.task_description}
Task completed: {'Yes' if result.task_completed else 'No'}
Total steps: {result.total_steps}
Duration: {result.total_duration_seconds:.1f}s
Final frustration: {result.frustration_level:.0f}/100
Emotion journey: {emotion_journey}

Actions:
{actions_text}

Friction points:
{friction_text}

Provide a UX analysis from the persona's perspective."""

    try:
        kwargs = {"model": litellm_model, "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ], "temperature": 0.7, "max_tokens": 2000}

        if api_key:
            kwargs["api_key"] = api_key

        response = await acompletion(**kwargs)
        content = response.choices[0].message.content
        input_tokens = response.usage.prompt_tokens or 0
        output_tokens = response.usage.completion_tokens or 0

        parsed = _parse_json(content)

        recommendations = []
        for r in parsed.get("recommendations", []):
            recommendations.append(Recommendation(
                title=r.get("title", ""),
                description=r.get("description", ""),
                priority=r.get("priority", "medium"),
                evidence=r.get("evidence", ""),
            ))

        return AnalysisResult(
            summary=parsed.get("summary", content[:500]),
            recommendations=recommendations,
            satisfaction_score=parsed.get("satisfactionScore", 0),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    except Exception as e:
        logger.error("Analysis LLM call failed: %s", e)
        return AnalysisResult(summary=f"Analysis failed: {e}")
