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


class GuardrailChecker:
    """Checks guardrails after each browser-use step.

    Guardrails:
    1. Max actions — agent hit step limit
    2. Max duration — campaign time limit exceeded
    3. Consecutive failures — 5+ failed actions in a row
    4. Frustration threshold — frustration >= persona's threshold
    5. Stuck detection — same page/action repeated N times
    """

    def __init__(
        self,
        max_actions: int = 50,
        max_duration_seconds: float = 300,
        max_consecutive_failures: int = 5,
        stuck_threshold: int = 4,
        max_repeated_actions: int = 3,
        frustration_abandon_threshold: float = 70.0,
        neuroticism: int = 50,
    ):
        self.max_actions = max_actions
        self.max_duration_seconds = max_duration_seconds
        self.max_consecutive_failures = max_consecutive_failures
        self.stuck_threshold = stuck_threshold
        self.max_repeated_actions = max_repeated_actions
        # Neuroticism adjusts abandonment threshold (research: Section 8)
        # High N = lower threshold, High C = higher threshold
        self.frustration_abandon_threshold = frustration_abandon_threshold
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

        # 6. Repeated actions
        if len(state.last_actions) >= self.max_repeated_actions:
            recent = state.last_actions[-self.max_repeated_actions:]
            if len(set(recent)) == 1:
                return GuardrailResult(
                    should_stop=True, reason="Same action repeated"
                )

        return GuardrailResult(should_stop=False)

    def record_action(
        self, state: GuardrailState, action_type: str, page_url: str | None,
        was_successful: bool, duration_seconds: float
    ) -> GuardrailState:
        """Update state after an action. Returns updated state."""
        state.action_count += 1
        state.elapsed_seconds += duration_seconds

        if was_successful:
            state.consecutive_failures = 0
            # Success reduces frustration (research: -5 per success)
            state.frustration_level = max(0, state.frustration_level - 5)
        else:
            state.consecutive_failures += 1
            # Failure increases frustration (research: +15 per error × neuroticism multiplier)
            state.frustration_level = min(
                100, state.frustration_level + 15 * self.frustration_multiplier
            )

        # Track for stuck detection
        state.last_page_urls.append(page_url)
        if len(state.last_page_urls) > self.stuck_threshold + 2:
            state.last_page_urls = state.last_page_urls[-(self.stuck_threshold + 2):]

        state.last_actions.append(action_type)
        if len(state.last_actions) > self.max_repeated_actions + 2:
            state.last_actions = state.last_actions[-(self.max_repeated_actions + 2):]

        return state

    @staticmethod
    def infer_emotion(
        frustration_level: float,
        neuroticism: float = 50,
        conscientiousness: float = 50,
        attention_span: float = 50,
    ) -> str:
        """Map frustration + personality traits to emotional state.

        High frustration always overrides. At low frustration, personality
        determines the baseline: high-N personas stay anxious/skeptical;
        low-N + high-C personas feel confident/delighted; low attention
        spans produce impatience even when nothing is wrong.
        """
        # Frustration-driven negative emotions
        if frustration_level >= 80:
            return "frustrated"
        if frustration_level >= 60:
            return "impatient"
        if frustration_level >= 40:
            return "anxious"
        if frustration_level >= 20:
            return "confused"

        # Low frustration — personality sets the baseline
        # Short attention spans produce restlessness/impatience unprompted
        if attention_span <= 30 and frustration_level > 2:
            return "impatient"
        # High neuroticism: worried/skeptical even when things go right
        if neuroticism >= 70:
            return "anxious" if frustration_level > 5 else "skeptical"
        # Low neuroticism + conscientious: calm and in-control
        if neuroticism <= 30 and conscientiousness >= 60:
            return "delighted" if frustration_level == 0 else "confident"
        # Default mid-range states
        if frustration_level <= 5:
            return "confident"
        return "neutral"
