"""Human-like scroll simulation.

Research basis:
- NNGroup: 57% viewing time above fold, 17% second screenful
- Scroll pauses are the best predictor of reading comprehension
- Inertia-based: smooth acceleration/deceleration
"""

from __future__ import annotations

import random

from ux_pilot.humanization.profile import HumanizationProfile

# NNGroup attention distribution
ATTENTION_ABOVE_FOLD = 0.57
ATTENTION_SECOND_SCREEN = 0.17


def generate_scroll_plan(
    viewport_height: int,
    page_height: int,
    profile: HumanizationProfile,
) -> list[dict]:
    """Generate a scroll plan with human-like behavior.

    Returns list of {"delta_y": int, "pause_after": float} steps.
    """
    if page_height <= viewport_height:
        return []

    max_scroll = int(page_height * profile.max_scroll_depth_fraction)
    current_y = 0
    steps: list[dict] = []

    while current_y < max_scroll:
        # Variable scroll amount: 50-400px per event
        remaining = max_scroll - current_y
        if remaining < 50:
            break
        scroll_amount = random.randint(50, min(400, remaining))

        current_y += scroll_amount

        # Reading pause based on page position (NNGroup attention data)
        screenfuls = current_y / viewport_height
        if screenfuls < 1:
            # Above fold: 2.5x attention → longer pauses
            pause = random.uniform(1.5, 4.0) * profile.reading_speed_multiplier
        elif screenfuls < 2:
            # Second screenful: moderate attention
            pause = random.uniform(0.8, 2.5) * profile.reading_speed_multiplier
        else:
            # Below: diminishing attention
            pause = random.uniform(0.3, 1.0) * profile.reading_speed_multiplier

        steps.append({"delta_y": scroll_amount, "pause_after": pause})

        # Scroll-back probability (higher neuroticism = more re-reading)
        if random.random() < profile.scroll_back_probability:
            back_amount = random.randint(50, min(200, current_y))
            current_y -= back_amount
            re_read_pause = random.uniform(1.0, 3.0) * profile.reading_speed_multiplier
            steps.append({"delta_y": -back_amount, "pause_after": re_read_pause})

    return steps


def generate_inertia_deltas(scroll_amount: int) -> list[int]:
    """Break a single scroll into multiple small deltas with inertia.

    Simulates mousewheel with acceleration then deceleration.
    """
    if abs(scroll_amount) < 20:
        return [scroll_amount]

    sign = 1 if scroll_amount > 0 else -1
    total = abs(scroll_amount)
    deltas: list[int] = []
    remaining = total

    # Phase 1: acceleration (increasing deltas)
    # Phase 2: deceleration (decreasing deltas)
    num_steps = max(3, total // 40)
    mid = num_steps // 2

    for i in range(num_steps):
        if remaining <= 0:
            break
        if i <= mid:
            # Accelerating
            frac = (i + 1) / (mid + 1)
            delta = max(5, int(total / num_steps * frac * 2))
        else:
            # Decelerating
            frac = (num_steps - i) / (num_steps - mid)
            delta = max(5, int(total / num_steps * frac * 2))

        delta = min(delta, remaining)
        deltas.append(delta * sign)
        remaining -= delta

    if remaining > 0:
        deltas.append(remaining * sign)

    return deltas
