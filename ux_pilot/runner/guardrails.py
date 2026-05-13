"""Guardrail checker — determines when an agent run should stop.

Research basis:
- Baymard (2026): 70% cart abandonment → abandonment_threshold=70
- Google (2018): 40% abandon at >3s load
- Frustration: +15 per error, -5 per success, Neuroticism multiplier
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GuardrailResult:
    should_stop: bool
    reason: str | None = None


@dataclass
class GuardrailState:
    """Accumulated state tracked across agent steps."""

    action_count: int = 0
    elapsed_seconds: float = 0.0
    consecutive_failures: int = 0
    frustration_level: float = 0.0
    last_page_urls: list[str] = field(default_factory=list)
    last_actions: list[str] = field(default_factory=list)


# Actions that legitimately repeat during browsing (not a sign of being stuck)
_BENIGN_REPEATABLE_ACTIONS = {"scroll", "wait", "navigate", "go_back"}


class GuardrailChecker:
    """Checks guardrails after each browser-use step.

    Thresholds are persona-aware — scaled by OCEAN traits so different
    personas fail at realistic rates (an anxious novice abandons faster
    than a persistent researcher).

    Guardrails:
    1. Max actions — agent hit step limit
    2. Max duration — campaign time limit exceeded
    3. Consecutive failures — scaled by neuroticism
    4. Frustration threshold — frustration >= persona's threshold
    5. Stuck detection — same page repeated N times (scaled by conscientiousness)
    6. Repeated actions — same non-benign action repeated (scaled by neuroticism)
    """

    def __init__(
        self,
        max_actions: int = 50,
        max_duration_seconds: float = 300,
        neuroticism: int = 50,
        conscientiousness: int = 50,
    ):
        self.max_actions = max_actions
        self.max_duration_seconds = max_duration_seconds

        # High neuroticism → fewer tolerated failures (3-6 range)
        self.max_consecutive_failures = max(3, 6 - int(neuroticism / 25))

        # High conscientiousness → higher stuck tolerance (4-7 range)
        self.stuck_threshold = 4 + int(conscientiousness / 25)

        # High neuroticism → fewer tolerated repeats (3-7 range for non-benign actions)
        self.max_repeated_actions = max(3, 7 - int(neuroticism / 25))

        # High neuroticism → lower frustration abandonment threshold
        # Baymard (2026): 70% base; high-N lowers it, high-C raises it
        self.frustration_abandon_threshold = 70.0 - (neuroticism - 50) * 0.3

        # Frustration multiplier: neuroticism 0-100 → multiplier 1.0-2.0
        self.frustration_multiplier = 1.0 + (neuroticism / 100)

    def check(self, state: GuardrailState) -> GuardrailResult:
        """Run all guardrail checks. Returns first triggered or pass."""

        # 1. Max actions
        if state.action_count >= self.max_actions:
            return GuardrailResult(should_stop=True, reason="Max actions reached")

        # 2. Max duration
        if state.elapsed_seconds >= self.max_duration_seconds:
            return GuardrailResult(should_stop=True, reason="Duration limit exceeded")

        # 3. Consecutive failures
        if state.consecutive_failures >= self.max_consecutive_failures:
            return GuardrailResult(
                should_stop=True, reason="Too many consecutive failures"
            )

        # 4. Frustration threshold
        if state.frustration_level >= self.frustration_abandon_threshold:
            return GuardrailResult(
                should_stop=True, reason="Frustration threshold exceeded"
            )

        # 5. Stuck detection — same page URL repeated
        if len(state.last_page_urls) >= self.stuck_threshold:
            recent = state.last_page_urls[-self.stuck_threshold:]
            if len(set(recent)) == 1 and recent[0] is not None:
                return GuardrailResult(
                    should_stop=True, reason="Stuck on same page"
                )

        # 6. Repeated actions (skip benign repeatable actions like scroll)
        if len(state.last_actions) >= self.max_repeated_actions:
            recent = state.last_actions[-self.max_repeated_actions:]
            if len(set(recent)) == 1 and recent[0] not in _BENIGN_REPEATABLE_ACTIONS:
                return GuardrailResult(
                    should_stop=True, reason="Same action repeated"
                )

        return GuardrailResult(should_stop=False)

    def record_action(
        self, state: GuardrailState, action_type: str, page_url: str | None,
        was_successful: bool, duration_seconds: float
    ) -> GuardrailState:
        """Update state after an action. Returns updated state.

        Automatically detects implicit failures: stuck on same page or
        repeating a non-benign action — these count as unsuccessful for
        frustration accumulation even if browser-use reports no error.
        """
        state.action_count += 1
        state.elapsed_seconds += duration_seconds

        # Track for stuck/repetition detection
        state.last_page_urls.append(page_url)
        if len(state.last_page_urls) > self.stuck_threshold + 2:
            state.last_page_urls = state.last_page_urls[-(self.stuck_threshold + 2):]

        state.last_actions.append(action_type)
        if len(state.last_actions) > self.max_repeated_actions + 2:
            state.last_actions = state.last_actions[-(self.max_repeated_actions + 2):]

        # Detect implicit failure: repeating the same non-benign action on the
        # same page suggests being stuck (e.g., clicking a broken button 3x).
        # Benign actions (scroll, wait, navigate) are excluded.
        if (
            not was_successful
            or action_type in _BENIGN_REPEATABLE_ACTIONS
            or len(state.last_actions) < 3
        ):
            pass  # No implicit failure check needed
        else:
            recent_actions = state.last_actions[-3:]
            if len(set(recent_actions)) == 1:
                was_successful = False

        # Apply frustration delta
        if was_successful:
            state.consecutive_failures = 0
            state.frustration_level = max(0, state.frustration_level - 5)
        else:
            state.consecutive_failures += 1
            state.frustration_level = min(
                100, state.frustration_level + 15 * self.frustration_multiplier
            )

        return state

    @staticmethod
    def infer_emotion(
        frustration_level: float,
        neuroticism: float = 50,
        conscientiousness: float = 50,
        attention_span: float = 50,
        extraversion: float = 50,
        tech_literacy: float = 50,
    ) -> str:
        """Map frustration + personality traits to emotional state.

        High frustration overrides baseline. At low frustration, personality
        determines the default emotional state — this is how different personas
        show different emotions even when nothing goes wrong.
        """
        # Frustration-driven negative emotions (overrides personality)
        if frustration_level >= 80:
            return "frustrated"
        if frustration_level >= 60:
            return "impatient"
        if frustration_level >= 40:
            return "anxious"
        if frustration_level >= 20:
            return "confused"

        # Low frustration — personality sets the baseline emotion
        # High neuroticism: baseline anxiety/skepticism
        if neuroticism >= 75:
            return "anxious" if frustration_level > 5 else "skeptical"
        if neuroticism >= 60:
            return "skeptical" if frustration_level <= 5 else "anxious"
        # Low conscientiousness + high extraversion: excitable but scattered
        if conscientiousness <= 35 and extraversion >= 65:
            return "delighted" if frustration_level <= 3 else "confident"
        # Low tech literacy: uncertain, easily confused
        if tech_literacy <= 30:
            return "confused" if frustration_level > 5 else "skeptical"
        # Short attention span: restless/impatient baseline
        if attention_span <= 35:
            return "impatient" if frustration_level > 3 else "confident"
        # Low neuroticism + high conscientiousness: calm confidence
        if neuroticism <= 30 and conscientiousness >= 60:
            return "delighted" if frustration_level <= 3 else "confident"
        # High extraversion: enthusiastic
        if extraversion >= 75:
            return "delighted" if frustration_level <= 5 else "confident"
        # Default
        if frustration_level <= 5:
            return "confident"
        return "neutral"
