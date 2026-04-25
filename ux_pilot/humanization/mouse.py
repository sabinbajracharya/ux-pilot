"""Human-like mouse movement via CDP Input.dispatchMouseEvent.

Research basis:
- Fitts' Law (1954): MT = a + b * log2(D/W + 1)
- Ghost Cursor: Bezier curves with random control points
- Iliou et al. (2021): constant acceleration = bot indicator
- Milisavljevic et al. (2021): eye leads mouse by ~300ms
"""

from __future__ import annotations

import math
import random

from ux_pilot.humanization.profile import HumanizationProfile


def fitts_movement_time(distance: float, target_width: float) -> float:
    """Calculate movement time using Fitts' Law.

    Formula: MT = a + b * log2(D/W + 1)
    a ≈ 50ms base, b ≈ 150ms per bit of difficulty.
    """
    if distance <= 0 or target_width <= 0:
        return 0.05
    a = 0.050
    b = 0.150
    return a + b * math.log2(distance / target_width + 1)


def _cubic_bezier(
    t: float,
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
) -> tuple[float, float]:
    """Evaluate cubic Bezier curve at parameter t."""
    u = 1 - t
    x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
    y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
    return (x, y)


def _ease_in_out(t: float) -> float:
    """Smooth ease-in-out timing function. NOT linear — linear = bot indicator."""
    return t * t * (3 - 2 * t)


def _random_control_points(
    start: tuple[float, float],
    end: tuple[float, float],
    spread: float,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Generate 2 Bezier control points on the same side (Ghost Cursor method)."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]

    # Perpendicular direction
    length = math.hypot(dx, dy) or 1
    perp_x = -dy / length
    perp_y = dx / length

    # Both control points on same side (more human-like)
    side = random.choice([-1, 1])
    offset1 = side * random.uniform(spread * 0.3, spread)
    offset2 = side * random.uniform(spread * 0.1, spread * 0.7)

    cp1 = (
        start[0] + dx * 0.25 + perp_x * offset1,
        start[1] + dy * 0.25 + perp_y * offset1,
    )
    cp2 = (
        start[0] + dx * 0.75 + perp_x * offset2,
        start[1] + dy * 0.75 + perp_y * offset2,
    )
    return cp1, cp2


def generate_mouse_path(
    start: tuple[float, float],
    end: tuple[float, float],
    profile: HumanizationProfile,
    target_width: float = 20.0,
) -> list[tuple[float, float, float]]:
    """Generate human-like mouse path using cubic Bezier curves.

    Returns list of (x, y, timestamp_seconds) points.

    Research:
    - Ghost Cursor: 2-3 random control points, one side only
    - Fitts' Law: point density increases near target (deceleration)
    - Iliou et al.: constant acceleration = bot indicator (96.2% detection)
    """
    distance = math.hypot(end[0] - start[0], end[1] - start[1])
    if distance < 1:
        return [(end[0], end[1], 0.05)]

    # Total movement time from Fitts' Law, scaled by persona
    total_time = fitts_movement_time(distance, target_width)
    total_time *= profile.mouse_speed_multiplier

    # Control points
    cp1, cp2 = _random_control_points(start, end, profile.mouse_spread)

    # Number of points: ~1 per 5px, minimum 10
    num_points = max(10, int(distance / 5))
    points: list[tuple[float, float, float]] = []

    for i in range(num_points + 1):
        t = i / num_points
        t_eased = _ease_in_out(t)

        x, y = _cubic_bezier(t_eased, start, cp1, cp2, end)

        # Motor noise jitter — increases near target (micro-corrections)
        jitter_scale = 0.5 + 1.5 * t
        x += random.gauss(0, jitter_scale * profile.mouse_jitter)
        y += random.gauss(0, jitter_scale * profile.mouse_jitter)

        # Timestamp with Fitts-style acceleration/deceleration
        timestamp = total_time * _ease_in_out(t)
        points.append((x, y, timestamp))

    # Overshoot for small targets
    if target_width < 30 and random.random() < profile.overshoot_probability:
        last = points[-1]
        overshoot_dist = random.uniform(3, 10)
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        norm = math.hypot(dx, dy) or 1
        ox = end[0] + (dx / norm) * overshoot_dist
        oy = end[1] + (dy / norm) * overshoot_dist
        points.append((ox, oy, last[2] + 0.03))
        # Correct back
        points.append((end[0] + random.gauss(0, 1), end[1] + random.gauss(0, 1), last[2] + 0.08))

    return points


def should_misclick(
    target_width: float,
    target_height: float,
    profile: HumanizationProfile,
) -> bool:
    """Determine if this click should be a misclick.

    Research: inversely proportional to target size (Fitts' Law) and tech literacy.
    """
    base_rate = profile.misclick_rate
    size_modifier = 1.0
    if target_width < 20 or target_height < 20:
        size_modifier = 3.0
    elif target_width < 40 or target_height < 40:
        size_modifier = 1.5
    return random.random() < (base_rate * size_modifier)
