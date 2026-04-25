"""Data models for run state, actions, and results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class ActionType(StrEnum):
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    HOVER = "hover"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    FORM_SUBMIT = "form_submit"
    ERROR = "error"
    SELECT = "select"
    KEY_PRESS = "key_press"
    GO_BACK = "go_back"
    DONE = "done"
    FAILED = "failed"
    UNKNOWN = "unknown"


class EmotionalState(StrEnum):
    NEUTRAL = "neutral"
    CONFIDENT = "confident"
    CONFUSED = "confused"
    FRUSTRATED = "frustrated"
    DELIGHTED = "delighted"
    ANXIOUS = "anxious"
    SKEPTICAL = "skeptical"
    IMPATIENT = "impatient"


EMOTION_EMOJI: dict[str, str] = {
    "neutral": "😐",
    "confident": "😊",
    "confused": "😕",
    "frustrated": "😤",
    "delighted": "😄",
    "anxious": "😟",
    "skeptical": "🤨",
    "impatient": "😤",
}


@dataclass
class ActionEntry:
    """A single action taken by the agent."""

    sequence: int
    action_type: str
    page_url: str | None = None
    description: str = ""
    was_successful: bool = True
    emotion: str = "neutral"
    frustration_level: float = 0.0
    monologue: str = ""
    duration_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "actionType": self.action_type,
            "pageUrl": self.page_url,
            "description": self.description,
            "wasSuccessful": self.was_successful,
            "emotion": self.emotion,
            "frustrationLevel": self.frustration_level,
            "monologue": self.monologue,
            "durationMs": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Recommendation:
    """A single UX improvement recommendation."""

    title: str
    description: str
    priority: str  # "high", "medium", "low"
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "evidence": self.evidence,
        }


@dataclass
class CostInfo:
    """Token usage and cost tracking."""

    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "inputTokens": self.input_tokens,
            "outputTokens": self.output_tokens,
            "estimatedCostUsd": round(self.estimated_cost_usd, 6),
        }


@dataclass
class RunResult:
    """Complete result of a single agent run."""

    persona_name: str
    target_url: str
    task_description: str
    success_criteria: str | None = None
    task_completed: bool = False
    satisfaction_score: int = 0
    summary: str = ""
    failure_reason: str | None = None
    total_steps: int = 0
    total_duration_seconds: float = 0.0
    actions: list[ActionEntry] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)
    cost: CostInfo = field(default_factory=CostInfo)
    emotion_journey: list[str] = field(default_factory=list)
    friction_points: list[str] = field(default_factory=list)
    frustration_level: float = 0.0
    started_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "personaName": self.persona_name,
            "targetUrl": self.target_url,
            "taskDescription": self.task_description,
            "successCriteria": self.success_criteria,
            "taskCompleted": self.task_completed,
            "satisfactionScore": self.satisfaction_score,
            "summary": self.summary,
            "failureReason": self.failure_reason,
            "totalSteps": self.total_steps,
            "totalDurationSeconds": round(self.total_duration_seconds, 2),
            "actions": [a.to_dict() for a in self.actions],
            "recommendations": [r.to_dict() for r in self.recommendations],
            "cost": self.cost.to_dict(),
            "emotionJourney": self.emotion_journey,
            "frictionPoints": self.friction_points,
            "frustrationLevel": round(self.frustration_level, 1),
            "startedAt": self.started_at.isoformat(),
        }
