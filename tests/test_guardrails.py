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

        state = checker.record_action(state, "click", "http://x.com", was_successful=False, duration_seconds=1.0)
        assert state.frustration_level == min(100, 15 * expected_multiplier)

    def test_frustration_decrease_on_success(self):
        checker = GuardrailChecker()
        state = GuardrailState(frustration_level=20.0)
        state = checker.record_action(state, "click", "http://x.com", was_successful=True, duration_seconds=1.0)
        assert state.frustration_level == 15.0

    def test_stuck_detection(self):
        # conscientiousness=25 → stuck_threshold = 4 + int(25/25) = 5
        checker = GuardrailChecker(conscientiousness=25)
        state = GuardrailState(last_page_urls=["http://x.com"] * 5)
        result = checker.check(state)
        assert result.should_stop is True
        assert "Stuck" in (result.reason or "")

    def test_repeated_action_detection(self):
        # neuroticism=50 → max_repeated_actions = max(3, 7 - int(50/25)) = 5
        checker = GuardrailChecker(neuroticism=50)
        state = GuardrailState(
            last_actions=["click_button"] * 5,
            last_page_urls=["http://same-page.com"] * 5,
        )
        result = checker.check(state)
        assert result.should_stop is True
        assert "repeated" in (result.reason or "").lower()

    def test_repeated_action_different_pages_not_flagged(self):
        """Same action on DIFFERENT pages is productive browsing, not stuck."""
        checker = GuardrailChecker(neuroticism=50)
        state = GuardrailState(
            last_actions=["click_button"] * 5,
            last_page_urls=[
                "http://page1.com", "http://page2.com", "http://page3.com",
                "http://page4.com", "http://page5.com",
            ],
        )
        result = checker.check(state)
        assert result.should_stop is False

    def test_scroll_repeat_not_flagged(self):
        """Scroll is a benign repeatable action — should not trigger guardrail."""
        checker = GuardrailChecker()
        state = GuardrailState(last_actions=["scroll"] * 10)
        result = checker.check(state)
        assert result.should_stop is False

    def test_high_neuroticism_lower_thresholds(self):
        """Anxious persona (neuroticism=90) should have tighter guardrails."""
        anxious = GuardrailChecker(neuroticism=90)
        calm = GuardrailChecker(neuroticism=20)
        assert anxious.max_consecutive_failures <= calm.max_consecutive_failures
        assert anxious.max_repeated_actions <= calm.max_repeated_actions
        assert anxious.frustration_abandon_threshold < calm.frustration_abandon_threshold

    def test_high_conscientiousness_higher_stuck_tolerance(self):
        """Careful persona persists longer before stuck detection."""
        careful = GuardrailChecker(conscientiousness=90)
        careless = GuardrailChecker(conscientiousness=20)
        assert careful.stuck_threshold > careless.stuck_threshold

    def test_implicit_failure_on_same_page(self):
        """Being stuck on same page 3x should count as failure for frustration."""
        checker = GuardrailChecker()
        state = GuardrailState()
        # 3 successful actions on same page → implicit failure on 3rd
        state = checker.record_action(state, "click", "http://x.com", was_successful=True, duration_seconds=1)
        assert state.frustration_level == 0  # first success
        state = checker.record_action(state, "click", "http://x.com", was_successful=True, duration_seconds=1)
        assert state.frustration_level == 0  # second success
        state = checker.record_action(state, "click", "http://x.com", was_successful=True, duration_seconds=1)
        assert state.frustration_level > 0  # stuck detected → frustration

    def test_scroll_repeat_no_implicit_failure(self):
        """Scrolling repeatedly should NOT trigger implicit failure."""
        checker = GuardrailChecker()
        state = GuardrailState()
        for _ in range(4):
            state = checker.record_action(state, "scroll", "http://x.com", was_successful=True, duration_seconds=1)
        # Scroll is benign — frustration should be 0 (4 successes = 0 accumulated)
        assert state.frustration_level == 0


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

    def test_anxious_persona_baseline_skeptical(self):
        """High neuroticism persona should be skeptical/anxious even at 0 frustration."""
        emotion = GuardrailChecker.infer_emotion(
            frustration_level=0, neuroticism=90, conscientiousness=50,
        )
        assert emotion in ("skeptical", "anxious")

    def test_low_tech_baseline_uncertain(self):
        """Low tech literacy should show confusion/skepticism."""
        emotion = GuardrailChecker.infer_emotion(
            frustration_level=0, tech_literacy=20,
        )
        assert emotion in ("confused", "skeptical")

    def test_impulsive_baseline_delighted(self):
        """Low conscientiousness + high extraversion = delighted/confident."""
        emotion = GuardrailChecker.infer_emotion(
            frustration_level=0, conscientiousness=20, extraversion=85,
        )
        assert emotion in ("delighted", "confident")
