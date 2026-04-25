"""AgentRunner — wraps browser-use Agent for a single persona run."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Callable

from ux_pilot.analysis.models import ActionEntry, RunResult
from ux_pilot.config import Settings
from ux_pilot.humanization.profile import HumanizationProfile
from ux_pilot.runner.guardrails import GuardrailChecker, GuardrailState
from ux_pilot.runner.hooks import HumanizationHooks
from ux_pilot.runner.llm_factory import create_llm
from ux_pilot.runner.state import RunState

logger = logging.getLogger(__name__)

# Maps browser-use action class names to our ActionType strings
_ACTION_TYPE_MAP: dict[str, str] = {
    "GoToUrlAction": "navigate",
    "ClickElementAction": "click",
    "InputTextAction": "type",
    "ScrollAction": "scroll",
    "DoneAction": "done",
    "SearchGoogleAction": "navigate",
    "GoBackAction": "go_back",
    "SelectDropdownOptionAction": "select",
    "SendKeysAction": "key_press",
    "HoverElementAction": "hover",
    "WaitAction": "wait",
    "ExtractPageContentAction": "screenshot",
}


def _wrap_llm_for_token_tracking(llm: Any, acc: dict[str, int]) -> None:
    """Wrap browser-use LLM's ainvoke to accumulate token usage."""
    original_ainvoke = llm.ainvoke

    async def _tracked_ainvoke(messages: Any, output_format: Any = None, **kwargs: Any) -> Any:
        result = await original_ainvoke(messages, output_format=output_format, **kwargs)
        if result and getattr(result, "usage", None):
            acc["input"] += getattr(result.usage, "prompt_tokens", 0) or 0
            acc["output"] += getattr(result.usage, "completion_tokens", 0) or 0
        return result

    llm.ainvoke = _tracked_ainvoke


def _extract_action_type(agent_output: Any) -> str:
    """Extract action type string from browser-use agent output."""
    if not agent_output:
        return "unknown"

    actions = getattr(agent_output, "actions", None) or []
    for action in actions:
        for action_cls_name, action_type in _ACTION_TYPE_MAP.items():
            if hasattr(action, "model_fields"):
                for field_name in action.model_fields:
                    val = getattr(action, field_name, None)
                    if val is not None and type(val).__name__ == action_cls_name:
                        return action_type
            if type(action).__name__ == action_cls_name:
                return action_type
    return "unknown"


def _format_description(agent_output: Any) -> str:
    """Extract a human-readable description from agent output."""
    if not agent_output:
        return ""
    thinking = getattr(agent_output, "thinking", None)
    if thinking:
        return str(thinking)[:200]
    next_goal = getattr(agent_output, "next_goal", None)
    if next_goal:
        return str(next_goal)[:200]
    return ""


class AgentRunner:
    """Runs a single browser-use agent with a persona system prompt."""

    def __init__(
        self,
        target_url: str,
        task_description: str,
        settings: Settings,
        system_prompt: str = "",
        persona_name: str = "Default User",
        traits: dict[str, int] | None = None,
        success_criteria: str | None = None,
        on_step: Callable[[ActionEntry], None] | None = None,
    ):
        self.target_url = target_url
        self.task_description = task_description
        self.success_criteria = success_criteria
        self.settings = settings
        self.system_prompt = system_prompt
        self.persona_name = persona_name
        self._on_step = on_step
        self._state = RunState()

        # Humanization + guardrails (persona-aware)
        self._traits = traits or {}
        neuroticism = self._traits.get("neuroticism", 50)
        self._profile = HumanizationProfile.from_persona(self._traits)
        self._guardrail_state = GuardrailState()
        self._guardrail_checker = GuardrailChecker(
            max_actions=settings.max_actions,
            max_duration_seconds=settings.max_duration_minutes * 60,
            neuroticism=neuroticism,
        )
        self._hooks = HumanizationHooks(self._profile)
        self._should_stop = False
        self._stop_reason: str | None = None

    async def run(self) -> RunResult:
        """Execute the agent run and return structured results."""
        self._state = RunState()
        self._guardrail_state = GuardrailState()
        self._should_stop = False
        self._stop_reason = None
        started_at = datetime.now()

        try:
            result = await self._execute()
        except asyncio.TimeoutError:
            result = {
                "taskCompleted": False,
                "summary": "Duration limit exceeded",
                "failureReason": "timeout",
            }
        except Exception as e:
            logger.exception("Agent run failed: %s", e)
            result = {
                "taskCompleted": False,
                "summary": f"Error: {e}",
                "failureReason": str(e),
            }

        # If guardrails stopped the run, override result
        if self._stop_reason and not result.get("failureReason"):
            result["taskCompleted"] = False
            result["failureReason"] = self._stop_reason
            if "summary" not in result or result["summary"] == "No result":
                result["summary"] = f"Run stopped: {self._stop_reason}"

        return RunResult(
            persona_name=self.persona_name,
            target_url=self.target_url,
            task_description=self.task_description,
            success_criteria=self.success_criteria,
            task_completed=result.get("taskCompleted", False),
            summary=result.get("summary", ""),
            failure_reason=result.get("failureReason"),
            total_steps=self._state.step_count,
            total_duration_seconds=self._state.elapsed_seconds,
            actions=list(self._state.actions),
            cost=self._state.cost,
            emotion_journey=list(self._state.emotion_journey),
            friction_points=list(self._state.friction_points),
            frustration_level=self._guardrail_state.frustration_level,
            started_at=started_at,
        )

    async def _execute(self) -> dict[str, Any]:
        """Run browser-use agent with callbacks."""
        try:
            from browser_use import Agent, BrowserProfile
        except ImportError:
            raise RuntimeError(
                "browser-use is not installed. Install with:\n"
                "  pip install 'browser-use>=0.12.0'\n"
                "Then install Playwright:\n"
                "  playwright install chromium"
            )

        api_key = self.settings.get_api_key()
        llm = create_llm(
            provider=self.settings.llm_provider,
            model=self.settings.llm_model,
            api_key=api_key,
        )
        _wrap_llm_for_token_tracking(llm, self._state.token_acc)

        browser_kwargs: dict[str, Any] = {"headless": not self.settings.headed}

        initial_actions: list[dict[str, Any]] = []
        if self.target_url:
            initial_actions.append({"navigate": {"url": self.target_url}})

        agent = Agent(
            task=self.task_description,
            llm=llm,
            browser_profile=BrowserProfile(**browser_kwargs),
            extend_system_message=self.system_prompt or None,
            message_compaction=True,
            initial_actions=initial_actions or None,
            use_judge=bool(self.success_criteria),
            ground_truth=self.success_criteria,
            register_new_step_callback=self._on_new_step,
            register_done_callback=self._on_done,
            register_should_stop_callback=self._check_should_stop,
        )

        max_duration = self.settings.max_duration_minutes * 60
        history = await asyncio.wait_for(
            agent.run(max_steps=self.settings.max_actions),
            timeout=max_duration,
        )

        task_completed = history.is_successful() or False
        summary = history.final_result() or "No result"
        return {
            "taskCompleted": task_completed,
            "summary": summary,
            "totalSteps": history.number_of_steps(),
        }

    async def _on_new_step(self, browser_state: Any, agent_output: Any, step_number: int) -> None:
        """Callback after each browser-use step — tracks guardrails and emotions."""
        self._state.step_count += 1
        step_start = time.monotonic()

        page_url = browser_state.url if browser_state else None
        action_type = _extract_action_type(agent_output)
        description = _format_description(agent_output)
        was_successful = True
        if agent_output and hasattr(agent_output, "error") and agent_output.error:
            was_successful = False

        # Update guardrail state (frustration tracking)
        step_duration = time.monotonic() - step_start
        self._guardrail_state = self._guardrail_checker.record_action(
            self._guardrail_state, action_type, page_url, was_successful, step_duration,
        )

        # Update humanization hooks with current frustration
        self._hooks.update_frustration(self._guardrail_state.frustration_level)

        # Infer emotion from frustration + personality
        emotion = GuardrailChecker.infer_emotion(
            self._guardrail_state.frustration_level,
            neuroticism=self._traits.get("neuroticism", 50),
            conscientiousness=self._traits.get("conscientiousness", 50),
            attention_span=self._traits.get("attention_span", 50),
        )

        # Build monologue based on emotion and action
        monologue = self._generate_monologue(emotion, action_type, description)

        entry = ActionEntry(
            sequence=self._state.step_count,
            action_type=action_type,
            page_url=page_url,
            description=description,
            was_successful=was_successful,
            emotion=emotion,
            frustration_level=self._guardrail_state.frustration_level,
            monologue=monologue,
        )

        self._state.actions.append(entry)
        self._state.emotion_journey.append(emotion)

        # Track friction points (high frustration moments)
        if self._guardrail_state.frustration_level >= 40 and was_successful is False:
            friction = f"Step {self._state.step_count}: {action_type} failed on {page_url or 'unknown'}"
            self._state.friction_points.append(friction)

        # Check guardrails
        result = self._guardrail_checker.check(self._guardrail_state)
        if result.should_stop:
            self._should_stop = True
            self._stop_reason = result.reason
            logger.info("Guardrail triggered: %s", result.reason)

        # Apply humanization delay (thinking pause between steps)
        await self._hooks.on_step_end(None)

        if self._on_step:
            self._on_step(entry)

    async def _check_should_stop(self, browser_state: Any) -> bool:
        """browser-use callback: should the agent stop early?"""
        return self._should_stop

    def _generate_monologue(self, emotion: str, action_type: str, description: str) -> str:
        """Generate a short inner monologue based on current emotional state."""
        frustration = self._guardrail_state.frustration_level

        if emotion == "frustrated":
            return "This is really frustrating... nothing seems to work right."
        if emotion == "impatient":
            return "Come on, this is taking too long..."
        if emotion == "anxious":
            return "I'm not sure if I'm doing this right..."
        if emotion == "confused":
            return "Wait, where am I supposed to go from here?"
        if emotion == "skeptical":
            return "Hmm, I'm not fully trusting this..."
        if emotion == "delighted":
            return "Nice, this is working smoothly!"
        if emotion == "confident":
            return "OK, I know what to do here."
        if frustration > 0:
            return f"Let me figure this out... ({description[:80]})"
        return description[:100] if description else "Looking around..."

    async def _on_done(self, history: Any) -> None:
        """Callback when agent finishes."""
        logger.info(
            "Agent completed: %d steps, successful=%s",
            len(history.history) if history else 0,
            history.is_successful() if history else False,
        )
