"""Decision timing — delays based on Hick's Law and persona traits.

Research basis:
- Hick's Law (1952): RT = a + b * log2(n + 1), a≈50ms, b≈150ms
- NNGroup: page evaluation 3-5s, form field 2-5s
- Google (2018): 3s page load tolerance
- Milisavljevic (2021): eye leads mouse by ~300ms
"""

from __future__ import annotations

import math
import random

from ux_pilot.humanization.profile import HumanizationProfile


def decision_delay(num_choices: int, profile: HumanizationProfile) -> float:
    """How long to deliberate before clicking.

    Hick's Law: RT = a + b * log2(n + 1)
    Modified by decision speed and neuroticism (overwhelm).
    """
    a = 0.050  # 50ms base
    b = 0.150  # 150ms per bit
    base_time = a + b * math.log2(max(1, num_choices) + 1)

    # Decision Speed 0-100 maps to multiplier 3.0x → 0.5x
    speed_multiplier = 3.0 - (profile.decision_speed / 100) * 2.5

    # High neuroticism + many choices = overwhelm
    if num_choices > 5 and profile.neuroticism > 60:
        speed_multiplier *= 1.0 + (profile.neuroticism - 60) / 100

    return max(0.1, base_time * speed_multiplier + random.gauss(0, 0.2))


def page_evaluation_delay(profile: HumanizationProfile) -> float:
    """Time spent scanning page before first interaction.

    Research: 3-5s for above-fold evaluation (NNGroup).
    Three factors influence delay:
    - High attention_span → reads more content (longer)
    - High conscientiousness → checks everything carefully (longer)
    - Low tech_literacy → struggles to understand modern UI patterns (longer)
    """
    base = random.uniform(3.0, 5.0)
    modifier = (
        1.0
        + (profile.attention_span / 200)
        + (profile.conscientiousness / 200)
        + ((100 - profile.tech_literacy) / 200)
    )
    return base * modifier


def reading_delay(text_length: int, profile: HumanizationProfile) -> float:
    """Time to read a text block.

    Average web reading speed: ~250 words/minute = ~4.2 words/second.
    """
    words = text_length / 5
    base_time = words / 4.2

    # Attention span: 0-100 → read 30%-120% of full time
    attention_modifier = 0.3 + (profile.attention_span / 100) * 0.9
    return max(0.3, base_time * attention_modifier)


def form_field_delay(profile: HumanizationProfile) -> float:
    """Delay per form field. Research: 2-5s per field (UX benchmarks)."""
    base = random.uniform(2.0, 5.0)
    tech_modifier = 1.5 - (profile.tech_literacy / 100)
    return max(0.5, base * tech_modifier)


def pre_submit_hesitation(profile: HumanizationProfile) -> float:
    """Pause before clicking submit/purchase/confirm.

    High neuroticism = anxious pause. High conscientiousness = review pause.
    """
    base = random.uniform(0.5, 1.5)
    if profile.neuroticism > 60:
        base += random.uniform(1.0, 4.0)
    if profile.conscientiousness > 60:
        base += random.uniform(1.0, 3.0)
    return base


def eye_mouse_lead_delay() -> float:
    """Eye leads mouse by ~300ms (Milisavljevic 2021). Add before mouse movement."""
    return random.gauss(0.3, 0.05)
