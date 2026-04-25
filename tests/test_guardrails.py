"""Tests for GuardrailChecker."""

from ux_pilot.runner.guardrails import GuardrailChecker, GuardrailState


class TestGuardrailChecker:
    def test_initial_state_no_stop(self):
        checker = GuardrailChecker()
        state = GuardrailState()
        result = checker.check(state)
        assert result.should_stop is False

    def test_max_actions_stop(self):
        checker = GuardrailChecker(max_actions=10)
        state = GuardrailState(action_count=10)
        result = checker.check(state)
        assert result.should_stop is True
        assert "Max actions" in (result.reason or "")

    def test_frustration_accumulation(self):
        neuroticism = 80
        checker = GuardrailChecker(neuroticism=neuroticism)
        state = GuardrailState()
        expected_multiplier = 1.0 + (neuroticism / 100)

        checker.record_action(state, "click", "http://x.com", was_successful=False, duration_seconds=1.0)
        assert state.frustration_level == min(100, 15 * expected_multiplier)

    def test_frustration_decrease_on_success(self):
        checker = GuardrailChecker()
        state = GuardrailState(frustration_level=20.0)
        checker.record_action(state, "click", "http://x.com", was_successful=True, duration_seconds=1.0)
        assert state.frustration_level == 15.0

    def test_stuck_detection(self):
        checker = GuardrailChecker(stuck_threshold=4)
        state = GuardrailState(last_page_urls=["http://x.com"] * 4)
        result = checker.check(state)
        assert result.should_stop is True
        assert "Stuck" in (result.reason or "")

    def test_repeated_action_detection(self):
        checker = GuardrailChecker(max_repeated_actions=3)
        state = GuardrailState(last_actions=["click_button"] * 3)
        result = checker.check(state)
        assert result.should_stop is True
        assert "repeated" in (result.reason or "").lower()


class TestEmotionInference:
    def test_emotion_inference_frustrated(self):
        emotion = GuardrailChecker.infer_emotion(frustration_level=80)
        assert emotion == "frustrated"

    def test_emotion_inference_confident(self):
        emotion = GuardrailChecker.infer_emotion(
            frustration_level=0,
            neuroticism=20,
            conscientiousness=70,
        )
        assert emotion in ("confident", "delighted")
