"""PersonaHumanizationProfile — maps persona traits to concrete timing/error parameters.

All parameter ranges are research-backed. See docs/research/implementation-spec.md Section 8.
"""

from __future__ import annotations

from dataclasses import dataclass


def _lerp(trait_value: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    """Linear interpolation from trait range to parameter range."""
    t = (trait_value - in_min) / (in_max - in_min)
    t = max(0.0, min(1.0, t))
    return out_min + t * (out_max - out_min)


@dataclass
class HumanizationProfile:
    """All humanization parameters derived from persona traits.

    Each parameter has a research citation for its range.
    See docs/research/implementation-spec.md Section 12 for full table.
    """

    # Mouse (Fitts' Law, Ghost Cursor, Iliou 2021)
    mouse_speed_multiplier: float   # 0.6 (fast) to 1.8 (slow)
    mouse_jitter: float             # 0.5 (precise) to 2.5 (erratic) pixels
    mouse_spread: float             # Bezier control point spread: 60-180px
    overshoot_probability: float    # 0.02 to 0.12 (small targets)
    misclick_rate: float            # 0.005 to 0.05

    # Typing (KeyRecs 2023)
    base_inter_key_delay: float     # 0.08 to 0.22 seconds
    inter_key_variance: float       # 0.02 to 0.07 seconds
    typing_error_rate: float        # 0.01 to 0.08
    correction_rate: float          # 0.60 to 0.90

    # Scrolling (NNGroup attention)
    scroll_speed: float             # pixels/second: 250-700
    reading_speed_multiplier: float # 0.3 (skimmer) to 1.5 (thorough)
    scroll_back_probability: float  # 0.02 to 0.12 per scroll action
    max_scroll_depth_fraction: float  # 0.35 to 0.90 of page

    # Timing (Hick's Law, NNGroup)
    decision_speed: float           # From persona trait (0-100)
    conscientiousness: float        # For deliberation scaling
    neuroticism: float              # For overwhelm with many choices
    attention_span: float           # For reading time scaling
    openness: float                 # For exploration probability
    tech_literacy: float            # For form speed, shortcut usage

    @classmethod
    def from_persona(cls, traits: dict) -> HumanizationProfile:
        """Map persona traits to concrete humanization parameters."""
        tech = traits.get("tech_literacy", 50)
        consc = traits.get("conscientiousness", 50)
        neuro = traits.get("neuroticism", 50)
        attention = traits.get("attention_span", 50)
        openness = traits.get("openness", 50)
        decision = traits.get("decision_speed", 50)

        return cls(
            # Mouse: tech literacy determines precision
            # Research: Fitts' Law + inverse of tech comfort
            mouse_speed_multiplier=_lerp(tech, 0, 100, 1.8, 0.6),
            mouse_jitter=_lerp(tech, 0, 100, 2.5, 0.5),
            mouse_spread=_lerp(tech, 0, 100, 180, 60),
            overshoot_probability=_lerp(tech, 0, 100, 0.12, 0.02),
            misclick_rate=_lerp(tech, 0, 100, 0.05, 0.005),

            # Typing: tech literacy determines speed and errors
            # Research: KeyRecs — casual typing 150-250 CPM, 2-8% error
            base_inter_key_delay=_lerp(tech, 0, 100, 0.22, 0.08),
            inter_key_variance=_lerp(tech, 0, 100, 0.07, 0.02),
            typing_error_rate=_lerp(tech, 0, 100, 0.08, 0.01),
            correction_rate=_lerp(tech, 0, 100, 0.60, 0.90),

            # Scrolling: attention span + conscientiousness
            # Research: NNGroup — 57% above fold, scanning vs reading
            scroll_speed=_lerp(attention, 0, 100, 700, 250),
            reading_speed_multiplier=_lerp(attention, 0, 100, 0.3, 1.5),
            scroll_back_probability=_lerp(neuro, 0, 100, 0.02, 0.12),
            max_scroll_depth_fraction=_lerp(attention, 0, 100, 0.35, 0.90),

            # Timing: direct from traits
            decision_speed=decision,
            conscientiousness=consc,
            neuroticism=neuro,
            attention_span=attention,
            openness=openness,
            tech_literacy=tech,
        )
