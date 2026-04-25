"""Human-like typing simulation via CDP Input.dispatchKeyEvent.

Research basis: KeyRecs dataset (2023)
- Dwell time: 70-130ms
- Inter-key delay: 100-300ms
- Word boundary pause: 150-500ms
- Error rate: 2-8%
- Correction rate: 60-90%
"""

from __future__ import annotations

import random

from ux_pilot.humanization.profile import HumanizationProfile

# QWERTY adjacent keys for realistic typos
ADJACENT_KEYS: dict[str, list[str]] = {
    "a": ["s", "q", "z", "w"],
    "b": ["v", "n", "g", "h"],
    "c": ["x", "v", "d", "f"],
    "d": ["s", "f", "e", "r", "c", "x"],
    "e": ["w", "r", "d", "s"],
    "f": ["d", "g", "r", "t", "v", "c"],
    "g": ["f", "h", "t", "y", "b", "v"],
    "h": ["g", "j", "y", "u", "n", "b"],
    "i": ["u", "o", "k", "j"],
    "j": ["h", "k", "u", "i", "m", "n"],
    "k": ["j", "l", "i", "o", "m"],
    "l": ["k", "o", "p"],
    "m": ["n", "j", "k"],
    "n": ["b", "m", "h", "j"],
    "o": ["i", "p", "l", "k"],
    "p": ["o", "l"],
    "q": ["w", "a"],
    "r": ["e", "t", "f", "d"],
    "s": ["a", "d", "w", "e", "z", "x"],
    "t": ["r", "y", "g", "f"],
    "u": ["y", "i", "j", "h"],
    "v": ["c", "b", "f", "g"],
    "w": ["q", "e", "a", "s"],
    "x": ["z", "c", "s", "d"],
    "y": ["t", "u", "h", "g"],
    "z": ["a", "x", "s"],
}


def get_adjacent_key(char: str) -> str:
    """Get a random adjacent key on QWERTY for realistic typos."""
    lower = char.lower()
    adjacents = ADJACENT_KEYS.get(lower, [])
    if not adjacents:
        return char
    wrong = random.choice(adjacents)
    return wrong.upper() if char.isupper() else wrong


def generate_keystroke_sequence(
    text: str,
    profile: HumanizationProfile,
) -> list[dict]:
    """Generate a sequence of keystroke events with human-like timing.

    Returns list of {"key": str, "delay_before": float, "dwell": float, "is_correction": bool}

    Research parameters (KeyRecs 2023):
    - Dwell time: 70-130ms (key hold)
    - Inter-key delay: 100-300ms (between keys)
    - Word boundary: 150-500ms (after space/punctuation)
    - Error rate: 2-8% (typos)
    - Correction rate: 60-90% (backspace to fix)
    """
    events: list[dict] = []

    for i, char in enumerate(text):
        # Should we make a typo?
        if char.isalpha() and random.random() < profile.typing_error_rate:
            wrong_char = get_adjacent_key(char)

            # Type wrong key
            events.append({
                "key": wrong_char,
                "delay_before": max(0.04, random.gauss(
                    profile.base_inter_key_delay, profile.inter_key_variance
                )),
                "dwell": max(0.04, random.gauss(0.1, 0.02)),
                "is_correction": False,
            })

            # Correction: backspace + retype (60-90% of the time)
            if random.random() < profile.correction_rate:
                # Notice delay (200-500ms)
                events.append({
                    "key": "Backspace",
                    "delay_before": random.uniform(0.2, 0.5),
                    "dwell": max(0.04, random.gauss(0.08, 0.02)),
                    "is_correction": True,
                })
                # Retype correct key
                events.append({
                    "key": char,
                    "delay_before": max(0.04, random.gauss(0.15, 0.05)),
                    "dwell": max(0.04, random.gauss(0.1, 0.02)),
                    "is_correction": True,
                })
            # else: leave the typo (10-40% of time)
        else:
            # Normal keystroke
            if char == " " or char in ".,;:!?":
                # Word boundary: longer pause (150-500ms)
                delay = random.uniform(0.15, 0.5)
            else:
                # Normal inter-key (gaussian around base delay)
                delay = max(0.04, random.gauss(
                    profile.base_inter_key_delay, profile.inter_key_variance
                ))

            events.append({
                "key": char,
                "delay_before": delay,
                "dwell": max(0.04, random.gauss(0.1, 0.02)),
                "is_correction": False,
            })

    return events


def total_typing_duration(events: list[dict]) -> float:
    """Calculate total duration for a keystroke sequence."""
    return sum(e["delay_before"] + e["dwell"] for e in events)
