"""Export run results to JSON and Markdown files."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from rich.console import Console

from ux_pilot.analysis.models import RunResult


def export_json(result: RunResult, output_dir: str, console: Console) -> Path:
    """Save run results as JSON."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = path / f"ux-pilot_{timestamp}.json"

    with open(filename, "w") as f:
        json.dump(result.to_dict(), f, indent=2)

    console.print(f"[green]📁 JSON saved:[/] {filename}")
    return filename


def export_markdown(result: RunResult, output_dir: str, console: Console) -> Path:
    """Save run results as a Markdown report."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = path / f"ux-pilot_{timestamp}.md"

    lines = [
        f"# UX Pilot Report — {result.persona_name}",
        "",
        f"**URL:** {result.target_url}  ",
        f"**Task:** {result.task_description}  ",
        f"**Date:** {result.started_at.strftime('%Y-%m-%d %H:%M')}  ",
        f"**Result:** {'✅ Completed' if result.task_completed else '❌ Not completed'}  ",
        f"**Steps:** {result.total_steps} | **Duration:** {result.total_duration_seconds:.1f}s | "
        f"**Cost:** ~${result.cost.estimated_cost_usd:.4f}  ",
        f"**Frustration:** {result.frustration_level:.0f}/100  ",
        "",
    ]

    if result.summary:
        lines += ["## Summary", "", result.summary, ""]

    if result.emotion_journey:
        lines += ["## Emotion Journey", "", " → ".join(result.emotion_journey), ""]

    if result.recommendations:
        lines += ["## Recommendations", ""]
        priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        for r in result.recommendations:
            icon = priority_icon.get(r.priority, "•")
            lines += [
                f"### {icon} {r.priority.upper()}: {r.title}",
                "",
                r.description,
                "",
            ]
            if r.evidence:
                lines += [f"**Evidence:** {r.evidence}", ""]

    if result.friction_points:
        lines += ["## Friction Points", ""]
        for fp in result.friction_points:
            lines += [f"- {fp}"]
        lines += [""]

    if result.actions:
        lines += ["## Action Log", "", "| # | Emotion | Action | Success | URL |",
                   "|---|---------|--------|---------|-----|"]
        for a in result.actions:
            status = "✓" if a.was_successful else "✗"
            url_short = (a.page_url or "")[:40]
            lines.append(f"| {a.sequence} | {a.emotion} | {a.action_type} | {status} | {url_short} |")
        lines += [""]

    with open(filename, "w") as f:
        f.write("\n".join(lines))

    console.print(f"[green]📄 Report saved:[/] {filename}")
    return filename
