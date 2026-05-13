"""Tests for CDP humanization injector."""

import pytest
from ux_pilot.humanization.injector import HumanizationInjector
from ux_pilot.humanization.profile import HumanizationProfile


class TestHumanizationInjector:
    @pytest.fixture
    def injector(self):
        profile = HumanizationProfile.from_persona({
            "tech_literacy": 20, "neuroticism": 80,
            "attention_span": 30, "decision_speed": 25,
        })
        return HumanizationInjector(profile)

    def test_frustration_modifier_speeds_up(self, injector):
        injector.update_frustration(70)
        assert injector._frustration_modifier == 0.7

    def test_frustration_modifier_normal(self, injector):
        injector.update_frustration(20)
        assert injector._frustration_modifier == 1.0

    def test_step_count_increments(self, injector):
        assert injector._step_count == 0
        # Can't easily test async inject without a real page,
        # but we can verify the state tracking works


class TestInjectorProfiles:
    """Different personas should get different injector behaviors."""

    def test_senior_user_slower_than_admin(self):
        """Senior user (low tech) has higher delay multiplier = slower movement."""
        senior = HumanizationProfile.from_persona({
            "tech_literacy": 20, "neuroticism": 60,
        })
        admin = HumanizationProfile.from_persona({
            "tech_literacy": 95, "neuroticism": 25,
        })
        # multiplier is delay-based: higher = slower. Senior should be slower.
        assert senior.mouse_speed_multiplier > admin.mouse_speed_multiplier
        assert senior.mouse_jitter > admin.mouse_jitter
        assert senior.typing_error_rate > admin.typing_error_rate
