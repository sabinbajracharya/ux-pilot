"""AgentRunner — wraps browser-use Agent for a single persona run."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Callable

import json

from ux_pilot.analysis.models import ActionEntry, RunResult
from ux_pilot.config import Settings
from ux_pilot.humanization.profile import HumanizationProfile
from ux_pilot.personas.state_generator import PersonaStateGenerator
from ux_pilot.personas.translator import PersonaRuleset, TraitTranslator
from ux_pilot.runner.guardrails import GuardrailChecker, GuardrailState
from ux_pilot.runner.hooks import HumanizationHooks
from ux_pilot.runner.llm_factory import create_llm
from ux_pilot.runner.state import RunState
from ux_pilot.runner.tracking import TokenTrackingWrapper

logger = logging.getLogger(__name__)

# Lightweight prompt for LLM-driven persona state (emotion + monologue).
# Sent every 3 steps — costs ~$0.0001 per call at DeepSeek V4 Pro 75% discount.
_PERSONA_STATE_PROMPT = """You are a {persona_name}. Your traits:
{traits_summary}

You are browsing {current_url}. Your task: {task}
Recent actions:
{recent_actions}
Current frustration: {frustration}%

Based on your personality, how do you feel RIGHT NOW? Respond with JSON only:
{{"emotion": "<neutral|confident|confused|skeptical|anxious|frustrated|impatient|delighted>",
 "monologue": "<one sentence inner thought, in character, be specific about what you see/feel>",
 "frustrationDelta": <integer between -10 and +20>}}"""

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

# Interval (steps) between LLM-driven persona state updates
_PERSONA_STATE_INTERVAL = 2


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
        ruleset: PersonaRuleset | None = None,
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
        conscientiousness = self._traits.get("conscientiousness", 50)
        self._guardrail_checker = GuardrailChecker(
            max_actions=settings.max_actions,
            max_duration_seconds=settings.max_duration_minutes * 60,
            neuroticism=neuroticism,
            conscientiousness=conscientiousness,
        )
        self._hooks = HumanizationHooks(self._profile)
        self._should_stop = False
        self._stop_reason: str | None = None

        # Persona ruleset for context-aware monologue generation
        if ruleset:
            self._ruleset = ruleset
        else:
            translator = TraitTranslator()
            self._ruleset = translator.translate(self._traits)

        # LLM-driven persona state generator (emotion + monologue, every 3 steps)
        self._state_generator = PersonaStateGenerator(
            persona_name=persona_name,
            traits=self._traits,
            ruleset=self._ruleset,
            task=task_description,
        )
        self._raw_llm = None  # Set in _execute after LLM creation

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
        self._raw_llm = create_llm(
            provider=self.settings.llm_provider,
            model=self.settings.llm_model,
            api_key=api_key,
        )
        llm = TokenTrackingWrapper(self._raw_llm, self._state.token_acc)

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

        # Update guardrail state (frustration tracking + implicit stuck detection)
        step_duration = time.monotonic() - step_start
        self._guardrail_state = self._guardrail_checker.record_action(
            self._guardrail_state, action_type, page_url, was_successful, step_duration,
        )

        # Update humanization hooks with current frustration
        self._hooks.update_frustration(self._guardrail_state.frustration_level)

        # Base emotion from rules (used as fallback and as input to LLM)
        base_emotion = GuardrailChecker.infer_emotion(
            self._guardrail_state.frustration_level,
            neuroticism=self._traits.get("neuroticism", 50),
            conscientiousness=self._traits.get("conscientiousness", 50),
            attention_span=self._traits.get("attention_span", 50),
            extraversion=self._traits.get("extraversion", 50),
            tech_literacy=self._traits.get("tech_literacy", 50),
        )

        # LLM-driven persona state every N steps for richer emotion + monologue
        emotion = base_emotion
        monologue = self._generate_monologue(base_emotion, action_type, description)

        if self._state.step_count % _PERSONA_STATE_INTERVAL == 0 and self._state.actions:
            state = await self._maybe_generate_llm_state(page_url, base_emotion)
            if state:
                emotion = state.get("emotion", base_emotion)
                monologue = state.get("monologue", monologue)
                # Apply LLM-suggested frustration delta
                delta = state.get("frustrationDelta", 0)
                if delta != 0 and hasattr(self._guardrail_state, "frustration_level"):
                    self._guardrail_state.frustration_level = max(
                        0, min(100, self._guardrail_state.frustration_level + delta)
                    )
                    self._hooks.update_frustration(self._guardrail_state.frustration_level)

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

    async def _maybe_generate_llm_state(self, page_url: str | None, base_emotion: str) -> dict | None:
        """Call LLM for rich persona state. Returns None on failure."""
        try:
            recent = [
                {"type": a.action_type, "desc": a.description}
                for a in self._state.actions[-3:]
            ]
            prompt = self._state_generator.build_prompt(
                current_url=page_url,
                recent_actions=recent,
                frustration=self._guardrail_state.frustration_level,
                current_emotion=base_emotion,
            )
            # Use raw LLM (bypassing token tracker) for state generation
            return await PersonaStateGenerator.call_llm(
                self._raw_llm, prompt
            )
        except Exception as e:
            logger.debug("LLM state generation skipped: %s", e)
            return None

    async def _check_should_stop(self) -> bool:
        """browser-use callback: should the agent stop early?"""
        return self._should_stop

    def _generate_monologue(self, emotion: str, action_type: str, description: str) -> str:
        """Generate persona-specific inner monologue from ruleset triggers or context."""
        monologue_triggers: list[str] = []
        for rule in self._ruleset.rules:
            monologue_triggers.extend(rule.monologue_triggers)

        # Match trigger to current context using PersonaStateGenerator
        from ux_pilot.personas.state_generator import PersonaStateGenerator
        triggers = PersonaStateGenerator.pick_relevant_triggers(
            monologue_triggers, emotion, action_type
        )
        if triggers:
            import random
            return random.choice(triggers)

        # Fallback: compose from persona archetype + emotional state
        frustration = self._guardrail_state.frustration_level

        fallbacks = {
            "frustrated": "This isn't working the way I expected...",
            "impatient": "Let's move on already, this is taking too long...",
            "anxious": "I hope I'm not making a mistake here...",
            "confused": "Where do I go from here? This is confusing...",
            "skeptical": "I'm not sure I trust this...",
            "delighted": "Oh, that was easy and pleasant!",
            "confident": "I know exactly what to do next.",
        }
        if emotion in fallbacks:
            return fallbacks[emotion]
        if frustration > 30:
            return f"This is getting a bit frustrating... ({description[:70]})"
        return description[:100] if description else "Let me see what's on this page..."

    async def _on_done(self, history: Any) -> None:
        """Callback when agent finishes."""
        logger.info(
            "Agent completed: %d steps, successful=%s",
            len(history.history) if history else 0,
            history.is_successful() if history else False,
        )
