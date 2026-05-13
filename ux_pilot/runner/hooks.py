"""Humanization timing delays between browser-use steps based on persona profile.

on_step_start and on_step_end are called manually from AgentRunner._on_new_step
(browser-use does not expose pre/post-step hooks). on_step_start fires after a
step completes but before the next one is decided — simulating the cognitive
pause to digest the page. on_step_end adds a post-processing pause.
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

from ux_pilot.humanization.profile import HumanizationProfile
from ux_pilot.humanization.timing import (
    decision_delay,
    page_evaluation_delay,
    eye_mouse_lead_delay,
)

logger = logging.getLogger(__name__)


class HumanizationHooks:
    """Add human-like cognitive and post-action delays between agent steps.

    Called manually from AgentRunner._on_new_step (not via browser-use callbacks):
    - on_step_start: pre-decision delays (page evaluation, Hick's Law, eye-mouse lead)
    - on_step_end: post-action delays (reading, processing pause)
    """

    def __init__(self, profile: HumanizationProfile):
        self.profile = profile
        self._step_count = 0
        self._last_url: str | None = None
        self._frustration_modifier = 1.0

    def update_frustration(self, frustration_level: float) -> None:
        """Update behavior modifiers based on current frustration.

        Research (Section 8.3): Frustration increases speed, reduces accuracy.
        """
        if frustration_level > 60:
            self._frustration_modifier = 0.7
        elif frustration_level > 30:
            self._frustration_modifier = 0.85
        else:
            self._frustration_modifier = 1.0

    async def on_step_start(self, agent: Any) -> None:
        """Called before each browser-use action.

        Adds human-like delays:
        - Page evaluation on new URLs (3-5s, NNGroup)
        - Decision delay scaled by Hick's Law
        - Eye-mouse lead time (~300ms, Milisavljevic 2021)
        """
        self._step_count += 1

        # Check for new page via agent history (no browser internals access)
        current_url = self._get_url_from_history(agent)

        if current_url and current_url != self._last_url:
            delay = page_evaluation_delay(self.profile) * self._frustration_modifier
            logger.debug("Page evaluation delay: %.2fs", delay)
            await asyncio.sleep(delay)
            self._last_url = current_url

        # Decision delay (Hick's Law)
        num_elements = self._estimate_interactive_elements(agent)
        delay = decision_delay(num_elements, self.profile) * self._frustration_modifier
        logger.debug("Decision delay (n=%d): %.2fs", num_elements, delay)
        await asyncio.sleep(delay)

        # Eye-mouse lead (~300ms)
        await asyncio.sleep(eye_mouse_lead_delay())

    async def on_step_end(self, agent: Any) -> None:
        """Called after each browser-use action.

        Adds post-action delays: reading time, occasional thinking pause.
        """
        pause = random.uniform(0.3, 1.0) * self._frustration_modifier
        await asyncio.sleep(pause)

        # Every 5th step: self-check pause
        if self._step_count % 5 == 0:
            await asyncio.sleep(random.uniform(0.5, 1.5))

    def _get_url_from_history(self, agent: Any) -> str | None:
        """Extract current URL from agent's history (no browser internals)."""
        try:
            if agent.history and agent.history.history:
                last = agent.history.history[-1]
                if last.state:
                    return last.state.url
        except Exception:
            pass
        return None

    def _estimate_interactive_elements(self, agent: Any) -> int:
        """Estimate number of interactive elements on current page."""
        try:
            if agent.history and agent.history.history:
                last = agent.history.history[-1]
                if last.state and hasattr(last.state, "interacted_element"):
                    return 10
        except Exception:
            pass
        return 5
