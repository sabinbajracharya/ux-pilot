"""Multi-persona comparison table display."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from ux_pilot.analysis.models import EMOTION_EMOJI, RunResult


def print_comparison(console: Console, results: list[RunResult]) -> None:
    """Print a side-by-side comparison table for multiple persona runs."""
    if len(results) < 2:
        return

    table = Table(title="🎭 Multi-Persona Comparison", show_lines=True)
    table.add_column("Persona", style="bold")
    table.add_column("Complete", justify="center")
    table.add_column("Score", justify="center")
    table.add_column("Steps", justify="right")
    table.add_column("Time", justify="right")
    table.add_column("Frustration", justify="center")
    table.add_column("Top Friction")

    for r in results:
        complete = "[green]✅ Yes[/]" if r.task_completed else "[red]❌ No[/]"
        score = f"{r.satisfaction_score}/100" if r.satisfaction_score else "—"
        time_str = f"{r.total_duration_seconds:.0f}s"

        # Frustration bar
        frust = r.frustration_level
        color = "red" if frust >= 60 else ("yellow" if frust >= 30 else "green")
        frust_str = f"[{color}]{frust:.0f}%[/]"

        # Top friction point
        top_friction = r.friction_points[0][:30] if r.friction_points else "—"

        table.add_row(
            r.persona_name,
            complete,
            score,
            str(r.total_steps),
            time_str,
            frust_str,
            top_friction,
        )

    console.print()
    console.print(table)
    console.print()
