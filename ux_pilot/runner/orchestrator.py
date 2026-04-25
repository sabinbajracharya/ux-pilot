"""Orchestrator — runs multiple personas sequentially against same URL+task."""

from __future__ import annotations

from typing import Callable

from rich.console import Console

from ux_pilot.analysis.models import ActionEntry, RunResult
from ux_pilot.config import Settings
from ux_pilot.personas.loader import PersonaTemplate
from ux_pilot.personas.prompt_builder import PersonaPromptBuilder


async def run_multi_persona(
    url: str,
    task: str,
    personas: list[PersonaTemplate],
    settings: Settings,
    console: Console,
    success_criteria: str | None = None,
    on_step: Callable[[str, ActionEntry], None] | None = None,
) -> list[RunResult]:
    """Run multiple personas sequentially against the same URL + task.

    Sequential to avoid LLM rate limits. Returns list of RunResult.
    """
    from ux_pilot.runner.agent import AgentRunner

    results: list[RunResult] = []
    prompt_builder = PersonaPromptBuilder()

    for i, template in enumerate(personas, 1):
        console.print(f"\n[bold cyan]━━━ Run {i}/{len(personas)}: {template.name} ━━━[/]")

        system_prompt = prompt_builder.build(
            traits=template.traits,
            task_description=task,
            success_criteria=success_criteria,
            demographics=dict(template.demographics) if template.demographics else None,
            goals=list(template.goals) if template.goals else None,
            target_url=url,
        )

        def _on_step(entry: ActionEntry, _name: str = template.name) -> None:
            if on_step:
                on_step(_name, entry)

        runner = AgentRunner(
            target_url=url,
            task_description=task,
            settings=settings,
            system_prompt=system_prompt,
            persona_name=template.name,
            traits=dict(template.traits),
            success_criteria=success_criteria,
            on_step=_on_step,
        )

        result = await runner.run()
        results.append(result)

        status = "✅" if result.task_completed else "❌"
        console.print(
            f"[dim]{status} {template.name}: {result.total_steps} steps, "
            f"{result.total_duration_seconds:.0f}s, frustration {result.frustration_level:.0f}%[/]"
        )

    return results
