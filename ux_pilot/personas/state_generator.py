"""LLM-driven persona state generation — rich emotion + monologue per step.

Replaces hardcoded monologues with contextual LLM calls every 3-5 steps.
Costs ~$0.0001 per call at DeepSeek V4 Pro 75% discount.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ux_pilot.personas.translator import PersonaRuleset

logger = logging.getLogger(__name__)

STATE_PROMPT = """You are {persona_name}. Stay in character.

TRAITS: {traits_summary}
ARCHETYPE: {compound_label}
VOICE: {voice_hint}

You are on {current_url}. Your task: {task}

Last actions:
{recent_actions}

Current frustration: {frustration}%
Current emotion: {current_emotion}

Based on your personality and voice, how do you feel RIGHT NOW about what just happened?
Write a natural inner thought — the way a real person talks to themselves.
Be specific: reference what you actually see, prices, page elements, what worked, what didn't.

Respond with JSON only:
{{"emotion": "<neutral|confident|confused|skeptical|anxious|frustrated|impatient|delighted>",
 "monologue": "<1-2 sentences, in character, in your natural voice, specific to what you see/feel>"}}"""


class PersonaStateGenerator:
    """Generates persona-consistent emotional state and monologue via lightweight LLM call."""

    def __init__(self, persona_name: str, traits: dict[str, int], ruleset: PersonaRuleset, task: str):
        self._persona_name = persona_name
        self._task = task
        self._ruleset = ruleset
        self._traits_summary = _format_traits_summary(traits)
        self._voice_hint = _build_voice_hint(traits)

    @property
    def compound_label(self) -> str:
        return self._ruleset.compound_label or "None"

    def build_prompt(
        self,
        current_url: str | None,
        recent_actions: list[dict[str, str]],
        frustration: float,
        current_emotion: str,
    ) -> str:
        actions_text = "\n".join(
            f"- {a['type']}: {a['desc'][:120]}" for a in recent_actions[-3:]
        ) or "(none yet)"

        return STATE_PROMPT.format(
            persona_name=self._persona_name,
            traits_summary=self._traits_summary,
            compound_label=self.compound_label,
            voice_hint=self._voice_hint,
            current_url=current_url or "the page",
            task=self._task,
            recent_actions=actions_text,
            frustration=int(frustration),
            current_emotion=current_emotion,
        )

    @staticmethod
    async def call_llm(llm: Any, prompt: str) -> dict[str, Any] | None:
        """Send a lightweight state-generation call. Returns parsed JSON or None.

        Uses OpenAI-compatible API from the LLM instance (provider-agnostic).
        Falls back to 'deepseek-chat' if the model returns empty responses.
        Costs ~$0.0001 per call.
        """
        try:
            from openai import AsyncOpenAI

            model = getattr(llm, "model", None)
            base_url = getattr(llm, "base_url", None)
            api_key = getattr(llm, "api_key", "no-key")

            if not model:
                return None

            client_kwargs: dict[str, Any] = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url
            client = AsyncOpenAI(**client_kwargs)

            model_to_use = model if "v4-pro" not in str(model) else "deepseek-chat"
            response = await client.chat.completions.create(
                model=model_to_use,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.9,
            )
            text = response.choices[0].message.content or ""
            if not text:
                return None
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text.strip())
        except Exception as e:
            logger.warning("Persona state LLM call failed: %s", e)
            return None

    @staticmethod
    def pick_relevant_triggers(
        triggers: list[str], emotion: str, action_type: str
    ) -> list[str]:
        """Filter monologue triggers to those matching current emotional context."""
        emotion_keywords: dict[str, list[str]] = {
            "frustrated": ["error", "waiting", "stuck", "not working", "slow"],
            "impatient": ["waiting", "slow", "loading", "delay", "taking"],
            "anxious": ["worry", "mistake", "wrong", "unsure", "hesitat"],
            "confused": ["where", "confus", "don't know", "not sure", "unclear"],
            "skeptical": ["fake", "trust", "claim", "scam", "suspicious"],
            "delighted": ["smooth", "easy", "nice", "great", "love"],
            "confident": ["know", "familiar", "easy", "clear"],
        }
        keywords = emotion_keywords.get(emotion, [])
        relevant: list[str] = []
        for trigger in triggers:
            lower = trigger.lower()
            if "→" in trigger:
                _, text = trigger.split("→", 1)
                text = text.strip().strip("'").strip('"')
            else:
                text = trigger
            if any(kw in lower for kw in keywords):
                relevant.append(text)
        return relevant

    @staticmethod
    def fallback_state(emotion: str, frustration: float, ruleset: PersonaRuleset) -> dict[str, Any]:
        """Deterministic fallback when LLM call fails."""
        triggers: list[str] = []
        for rule in ruleset.rules:
            triggers.extend(rule.monologue_triggers)

        compound = f" [{ruleset.compound_label}]" if ruleset.compound_label else ""
        fallbacks = {
            "frustrated": f"This isn't working right{compound}...",
            "impatient": f"Come on, this is taking forever{compound}...",
            "anxious": f"I hope I'm not messing this up{compound}...",
            "confused": f"Where am I supposed to click{compound}?",
            "skeptical": f"I don't trust this{compound}...",
            "delighted": f"Nice, that was smooth{compound}!",
            "confident": f"I know what I'm doing{compound}.",
        }
        return {
            "emotion": emotion,
            "monologue": fallbacks.get(emotion, f"Hmm, let me think{compound}..."),
        }


def _build_voice_hint(traits: dict[str, int]) -> str:
    """Build a voice description for persona-appropriate monologue style."""
    neuroticism = traits.get("neuroticism", 50)
    tech = traits.get("tech_literacy", 50)
    extraversion = traits.get("extraversion", 50)
    age_hint = ""
    if traits.get("decision_speed", 50) <= 30:
        age_hint = " You speak slowly and deliberately."
    if neuroticism >= 75:
        return f"Anxious, self-doubting, worried about mistakes.{age_hint}"
    elif neuroticism >= 55:
        return f"Cautious, notices small issues, occasionally worried.{age_hint}"
    elif neuroticism <= 25:
        return f"Calm, collected, unflappable.{age_hint}"
    if tech <= 30:
        return f"Technologically uncertain, describes things by how they look not proper names.{age_hint}"
    if extraversion >= 75:
        return f"Enthusiastic, social, engaged.{age_hint}"
    return "Natural, conversational tone."


def _format_traits_summary(traits: dict[str, int]) -> str:
    pairs = []
    for name, value in sorted(traits.items(), key=lambda t: abs(t[1] - 50), reverse=True):
        if value >= 75:
            level = "very high"
        elif value >= 60:
            level = "high"
        elif value <= 25:
            level = "very low"
        elif value <= 40:
            level = "low"
        else:
            level = "moderate"
        pairs.append(f"  {name}: {value} ({level})")
    return "\n".join(pairs[:6])
