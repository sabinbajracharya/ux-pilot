"""CDP-level humanization injector — realistic mouse, typing, scroll at browser level.

Injects persona-profiled physical interactions via Playwright's mouse/keyboard
APIs and Chrome DevTools Protocol. Different personas physically interact
differently — a Senior User has a jittery mouse, a Power Admin is precise.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any

from ux_pilot.humanization.profile import HumanizationProfile
from ux_pilot.humanization.mouse import generate_mouse_path
from ux_pilot.humanization.typing import generate_keystroke_sequence
from ux_pilot.humanization.scrolling import generate_inertia_deltas

logger = logging.getLogger(__name__)


class HumanizationInjector:
    """Injects human-like physical interactions into browser sessions.

    Called after each browser-use step to add ambient human behavior:
    - Mouse fidgeting (post-click resting positions)
    - Micro-scroll adjustments
    - Humanized typing (character-by-character with errors)
    """

    def __init__(self, profile: HumanizationProfile):
        self._profile = profile
        self._mouse_x: float = 500
        self._mouse_y: float = 400
        self._frustration_modifier = 1.0
        self._step_count = 0

    def update_frustration(self, level: float) -> None:
        """Frustration speeds up movements, increases jitter (less careful)."""
        if level > 60:
            self._frustration_modifier = 0.7
        elif level > 30:
            self._frustration_modifier = 0.85
        else:
            self._frustration_modifier = 1.0

    async def inject_post_action(
        self,
        page: Any,
        action_type: str,
        was_successful: bool,
    ) -> None:
        """Inject human-like behavior after a browser-use action completes."""
        self._step_count += 1

        if action_type == "click":
            await self._fidget_mouse(page)
        elif action_type == "scroll":
            await self._micro_scroll(page)
        elif action_type == "type":
            await self._post_type_behavior(page)

        # Ambient: move mouse slightly every few steps (humans don't stay still)
        if self._step_count % 3 == 0:
            await self._ambient_mouse_move(page)

    # NOT CURRENTLY WIRED — browser-use controls typing internally via its own
    # action execution (page.fill / page.keyboard.type). There is no callback or
    # hook in browser-use's Agent API to intercept or replace typing actions with
    # custom keystroke sequences. If browser-use adds a pre-type hook or allows
    # custom action handlers, wire this to replace instant typing with
    # persona-profiled keystrokes (QWERTY-adjacent typos, corrections, dwell timing).
    async def inject_humanized_type(self, page: Any, text: str) -> None:
        """Type text character-by-character with realistic timing and errors.

        Replaces instant page.fill() with persona-profiled keystrokes.
        """
        if not text:
            return

        keystrokes = generate_keystroke_sequence(
            text,
            self._profile,
        )

        for ks in keystrokes:
            # Sleep for inter-key delay before pressing
            await asyncio.sleep(ks["delay_before"] * self._frustration_modifier)
            try:
                await page.keyboard.press(ks["key"])
                # Hold the key for dwell time
                await asyncio.sleep(ks["dwell"] * self._frustration_modifier)
            except Exception:
                pass  # Page may have navigated away

    async def _fidget_mouse(self, page: Any) -> None:
        """After a click, move the mouse to a slightly different position.

        Humans don't leave the cursor exactly on the click target.
        Low-tech users have larger fidget radius.
        """
        jitter = self._profile.mouse_jitter * (1.0 / self._frustration_modifier)
        target_x = self._mouse_x + random.uniform(-jitter * 2, jitter * 2)
        target_y = self._mouse_y + random.uniform(-jitter * 2, jitter * 2)

        try:
            viewport = page.viewport_size or {"width": 1280, "height": 800}
            target_x = max(10, min(viewport["width"] - 10, target_x))
            target_y = max(10, min(viewport["height"] - 10, target_y))

            steps = max(3, int(abs(target_x - self._mouse_x) / 10))
            await page.mouse.move(target_x, target_y, steps=steps)
            self._mouse_x, self._mouse_y = target_x, target_y
        except Exception:
            pass

    async def _micro_scroll(self, page: Any) -> None:
        """Add micro-scroll adjustments after main scroll action.

        Humans rarely scroll exactly once — they micro-adjust.
        Uses inertia physics (acceleration → deceleration) for realism.
        """
        micro_adjustments = random.randint(1, 3)
        for _ in range(micro_adjustments):
            delta = random.randint(-15, 15)
            if abs(delta) >= 8:
                # Use inertia deltas for noticeable adjustments
                for step_delta in generate_inertia_deltas(delta):
                    try:
                        await page.mouse.wheel(0, step_delta)
                        await asyncio.sleep(0.015)
                    except Exception:
                        break
            else:
                try:
                    await page.mouse.wheel(0, delta)
                except Exception:
                    break
            await asyncio.sleep(random.uniform(0.1, 0.3))

    async def _post_type_behavior(self, page: Any) -> None:
        """After typing, humans often pause or look around."""
        # Small pause after typing (processing what was typed)
        await asyncio.sleep(random.uniform(0.2, 0.5))

    async def _ambient_mouse_move(self, page: Any) -> None:
        """Move mouse slightly to a random position (ambient fidgeting)."""
        try:
            viewport = page.viewport_size or {"width": 1280, "height": 800}
            target_x = random.randint(100, viewport["width"] - 100)
            target_y = random.randint(100, viewport["height"] - 100)

            # Use Bezier path from mouse.py for realistic movement
            path = generate_mouse_path(
                start_x=self._mouse_x, start_y=self._mouse_y,
                end_x=target_x, end_y=target_y,
                speed_px_per_s=500 * self._profile.mouse_speed_multiplier,
                jitter_px=self._profile.mouse_jitter,
            )

            for point in path:
                await page.mouse.move(point.x, point.y, steps=1)
                delay = 0.008 * self._frustration_modifier  # ~120Hz with modifier
                await asyncio.sleep(delay)

            self._mouse_x, self._mouse_y = target_x, target_y
        except Exception:
            pass


async def get_page_from_agent(agent: Any) -> Any | None:
    """Safely extract Playwright page from a browser-use Agent instance."""
    try:
        session = getattr(agent, "browser_session", None)
        if session:
            return await session.get_current_page()
    except Exception:
        pass
    return None
