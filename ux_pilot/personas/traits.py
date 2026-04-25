"""Trait definitions and validation for the 9-trait persona system."""

from __future__ import annotations

TRAIT_NAMES = [
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "neuroticism",
    "tech_literacy",
    "decision_speed",
    "attention_span",
    "price_sensitivity",
]

OCEAN_TRAITS = TRAIT_NAMES[:5]
BROWSING_TRAITS = TRAIT_NAMES[5:]

TRAIT_EMOJI: dict[str, str] = {
    "openness": "🔓",
    "conscientiousness": "🔍",
    "extraversion": "💬",
    "agreeableness": "🤝",
    "neuroticism": "😰",
    "tech_literacy": "📱",
    "decision_speed": "⚡",
    "attention_span": "👁",
    "price_sensitivity": "💰",
}

TRAIT_SHORT: dict[str, str] = {
    "openness": "open",
    "conscientiousness": "consc",
    "extraversion": "extra",
    "agreeableness": "agree",
    "neuroticism": "neuro",
    "tech_literacy": "tech",
    "decision_speed": "speed",
    "attention_span": "attn",
    "price_sensitivity": "price",
}


def validate_traits(traits: dict[str, int]) -> dict[str, int]:
    """Validate trait values are 0-100 and fill defaults for missing traits."""
    result = {}
    for name in TRAIT_NAMES:
        val = traits.get(name, 50)
        if not isinstance(val, (int, float)):
            raise ValueError(f"Trait '{name}' must be a number, got {type(val).__name__}")
        val = int(val)
        if val < 0 or val > 100:
            raise ValueError(f"Trait '{name}' must be 0-100, got {val}")
        result[name] = val
    return result


def trait_level_label(value: int) -> str:
    """Human-readable level for a 0-100 trait value."""
    if value <= 29:
        return "Low"
    elif value <= 49:
        return "Med-Low"
    elif value <= 74:
        return "Med-High"
    else:
        return "High"
