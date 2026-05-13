"""Mutable run state — tracks actions, emotions, and costs during a live run."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from ux_pilot.analysis.models import ActionEntry, CostInfo


@dataclass
class RunState:
    """Accumulated state during a single agent run."""

    step_count: int = 0
    start_time: float = field(default_factory=time.monotonic)
    actions: list[ActionEntry] = field(default_factory=list)
    emotion_journey: list[str] = field(default_factory=list)
    friction_points: list[str] = field(default_factory=list)
    token_acc: dict[str, int] = field(default_factory=lambda: {"input": 0, "output": 0})
    humanization_time_ms: float = 0.0

    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.start_time

    @property
    def cost(self) -> CostInfo:
        input_t = self.token_acc["input"]
        output_t = self.token_acc["output"]
        # Rough estimate: $0.15/1M input, $0.60/1M output (gpt-4o-mini pricing)
        est = (input_t * 0.15 + output_t * 0.60) / 1_000_000
        return CostInfo(input_tokens=input_t, output_tokens=output_t, estimated_cost_usd=est)
