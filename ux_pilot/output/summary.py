"""Post-run Rich summary panels — beautiful result display."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ux_pilot.analysis.models import EMOTION_EMOJI, RunResult


def print_summary(console: Console, result: RunResult) -> None:
    """Print a rich post-run summary with result, emotions, and friction."""
    parts: list[str] = []

    # Result header
    status = "✅ Task completed" if result.task_completed else "❌ Task not completed"
    parts.append(f"[bold]{status}[/]")
    if result.failure_reason:
        parts.append(f"[yellow]⚠️  {result.failure_reason}[/]")
    parts.append(
        f"[dim]{result.total_steps} steps │ {result.total_duration_seconds:.1f}s │ "
        f"~${result.cost.estimated_cost_usd:.4f}[/]"
    )

    # Humanization overhead (cognitive delays + CDP injection)
    if result.humanization_time_ms > 0:
        h_sec = result.humanization_time_ms / 1000
        pct = (h_sec / result.total_duration_seconds * 100) if result.total_duration_seconds > 0 else 0
        parts.append(f"[dim]Humanization: {h_sec:.1f}s ({pct:.0f}% of runtime)[/]")

    if result.satisfaction_score:
        parts.append(f"[bold]Satisfaction:[/] {result.satisfaction_score}/100")

    # Summary text
    if result.summary:
        parts.append("")
        parts.append(f"[bold]Summary:[/] {result.summary[:300]}")

    # Emotion journey
    if result.emotion_journey:
        parts.append("")
        emojis = " → ".join(
            EMOTION_EMOJI.get(e, "😐") for e in result.emotion_journey
        )
        parts.append(f"[bold]Emotions:[/] {emojis}")

    # Notable inner thoughts (persona monologues from actions)
    notable_monologues = [
        a.monologue for a in result.actions
        if a.monologue and len(a.monologue) > 10
    ][-3:]  # Last 3 meaningful monologues
    if notable_monologues:
        parts.append("")
        parts.append("[bold]Notable thoughts:[/]")
        for m in notable_monologues:
            parts.append(f'  [dim italic]"💭 {m[:120]}"[/]')

    # Frustration
    frust = result.frustration_level
    width = 15
    filled = int(frust / 100 * width)
    color = "red" if frust >= 60 else ("yellow" if frust >= 30 else "green")
    bar = f"[{color}]{'▰' * filled}[/][dim]{'▱' * (width - filled)}[/]"
    parts.append(f"[bold]Frustration:[/] {bar} {frust:.0f}%")

    # Friction points
    if result.friction_points:
        parts.append("")
        parts.append("[bold yellow]⚡ Friction points:[/]")
        for fp in result.friction_points[:5]:
            parts.append(f"  • {fp}")

    console.print()
    console.print(Panel(
        "\n".join(parts),
        title=f"[bold] 🎭 {result.persona_name} — Results [/]",
        border_style="cyan",
    ))

    # Recommendations (separate panels)
    if result.recommendations:
        _print_recommendations(console, result.recommendations)

    console.print()


def _print_recommendations(console: Console, recommendations: list) -> None:
    """Print recommendation panels with priority colors."""
    from ux_pilot.analysis.models import Recommendation

    priority_style = {"high": "red", "medium": "yellow", "low": "green"}
    priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}

    for rec in recommendations:
        color = priority_style.get(rec.priority, "white")
        icon = priority_icon.get(rec.priority, "•")
        content = rec.description
        if rec.evidence:
            content += f"\n[dim]Evidence: {rec.evidence}[/]"
        console.print(Panel(
            content,
            title=f"[bold {color}]{icon} {rec.priority.upper()}: {rec.title}[/]",
            border_style=color,
        ))
