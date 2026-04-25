"""Tests for humanization modules."""

from ux_pilot.humanization.mouse import generate_mouse_path
from ux_pilot.humanization.profile import HumanizationProfile
from ux_pilot.humanization.scrolling import generate_scroll_plan
from ux_pilot.humanization.timing import decision_delay
from ux_pilot.humanization.typing import generate_keystroke_sequence
from ux_pilot.personas.traits import TRAIT_NAMES


def _traits(**overrides: int) -> dict[str, int]:
    traits = {name: 50 for name in TRAIT_NAMES}
    traits.update(overrides)
    return traits


class TestHumanizationProfile:
    def test_profile_from_persona(self):
        profile = HumanizationProfile.from_persona(_traits())
        assert 0.6 <= profile.mouse_speed_multiplier <= 1.8
        assert 0.08 <= profile.base_inter_key_delay <= 0.22
        assert 250 <= profile.scroll_speed <= 700
        assert 0 <= profile.decision_speed <= 100

    def test_low_tech_slow_mouse(self):
        profile = HumanizationProfile.from_persona(_traits(tech_literacy=10))
        assert profile.mouse_speed_multiplier > 1.0

    def test_high_tech_fast_mouse(self):
        profile = HumanizationProfile.from_persona(_traits(tech_literacy=90))
        assert profile.mouse_speed_multiplier < 1.0


class TestDecisionDelay:
    def test_decision_delay_positive(self):
        profile = HumanizationProfile.from_persona(_traits())
        for _ in range(20):
            delay = decision_delay(3, profile)
            assert delay > 0


class TestKeystrokeSequence:
    def test_keystroke_sequence_length(self):
        profile = HumanizationProfile.from_persona(_traits(tech_literacy=50))
        text = "hello"
        events = generate_keystroke_sequence(text, profile)
        # At minimum, one event per character (corrections add more)
        assert len(events) >= len(text)
        assert all("key" in e for e in events)


class TestScrollPlan:
    def test_scroll_plan_no_scroll_needed(self):
        profile = HumanizationProfile.from_persona(_traits())
        plan = generate_scroll_plan(viewport_height=800, page_height=600, profile=profile)
        assert plan == []


class TestMousePath:
    def test_mouse_path_generates_points(self):
        profile = HumanizationProfile.from_persona(_traits())
        points = generate_mouse_path(start=(0, 0), end=(200, 300), profile=profile)
        assert len(points) > 0
        assert all(len(p) == 3 for p in points)
