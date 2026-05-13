"""CLI command implementations — extracted from cli.py to keep entry point lean."""

from __future__ import annotations

import asyncio

from rich.console import Console
from rich.panel import Panel

from ux_pilot.analysis.models import RunResult
from ux_pilot.config import Settings
from ux_pilot.personas.loader import PersonaTemplate
from ux_pilot.personas.prompt_builder import PersonaPromptBuilder
from ux_pilot.personas.traits import TRAIT_EMOJI, TRAIT_SHORT


def run_single(
    template: PersonaTemplate,
    url: str,
    task: str,
    settings: Settings,
    console: Console,
    success_criteria: str | None = None,
    output: str | None = None,
    no_save: bool = False,
) -> None:
    """Run a single persona with live dashboard."""
    from ux_pilot.output.live import LiveDashboard
    from ux_pilot.output.summary import print_summary
    from ux_pilot.runner.agent import AgentRunner

    prompt_builder = PersonaPromptBuilder()
    system_prompt = prompt_builder.build(
        traits=template.traits,
        task_description=task,
        success_criteria=success_criteria,
        demographics=dict(template.demographics) if template.demographics else None,
        goals=list(template.goals) if template.goals else None,
        target_url=url,
    )

    console.print()
    console.print(f"[bold cyan]🎭 Persona:[/] {template.name} ({template.category})")
    console.print(f"[dim]   {template.description}[/]")

    top_traits = sorted(template.traits.items(), key=lambda t: abs(t[1] - 50), reverse=True)[:4]
    trait_summary = " · ".join(
        f"{TRAIT_EMOJI.get(k, '•')} {v} {TRAIT_SHORT.get(k, k)}" for k, v in top_traits
    )
    console.print(f"[dim]   Traits: {trait_summary}[/]")
    console.print(f"[bold cyan]🌐 URL:[/]     {url}")
    console.print(f"[bold cyan]📋 Task:[/]    {task}")
    console.print(f"[dim]LLM: {settings.llm_provider}/{settings.llm_model or 'default'} │ "
                  f"Max: {settings.max_actions} actions, {settings.max_duration_minutes}min[/]")
    console.print()

    dashboard = LiveDashboard(
        console=console,
        persona_name=template.name,
        target_url=url,
        task=task,
        trait_summary=trait_summary,
        max_actions=settings.max_actions,
        max_duration_minutes=settings.max_duration_minutes,
    )

    runner = AgentRunner(
        target_url=url,
        task_description=task,
        settings=settings,
        system_prompt=system_prompt,
        persona_name=template.name,
        traits=dict(template.traits),
        success_criteria=success_criteria,
        on_step=lambda entry: dashboard.update(
            entry,
            elapsed_seconds=runner._state.elapsed_seconds,
            cost_usd=runner._state.cost.estimated_cost_usd,
        ),
    )

    console.print("[dim]Starting browser...[/]")
    dashboard.start()
    try:
        result = asyncio.run(runner.run())
    finally:
        dashboard.stop()

    analyze_result(result, settings, console)
    print_summary(console, result)

    if not no_save:
        save_to_history(result, console)
    if output:
        from ux_pilot.output.export import export_json, export_markdown
        export_json(result, output, console)
        export_markdown(result, output, console)


def run_multi(
    templates: list[PersonaTemplate],
    url: str,
    task: str,
    settings: Settings,
    console: Console,
    success_criteria: str | None = None,
    output: str | None = None,
    no_save: bool = False,
) -> None:
    """Run multiple personas concurrently with comparison table."""
    from ux_pilot.runner.orchestrator import run_multi_persona
    from ux_pilot.output.comparison import print_comparison
    from ux_pilot.output.summary import print_summary

    console.print(f"\n[bold cyan]🎭 Multi-persona run: {len(templates)} personas[/]")
    console.print(f"[bold cyan]🌐 URL:[/]  {url}")
    console.print(f"[bold cyan]📋 Task:[/] {task}")
    console.print()

    results = asyncio.run(run_multi_persona(
        url=url, task=task, personas=templates, settings=settings, console=console,
        success_criteria=success_criteria,
    ))

    for result in results:
        analyze_result(result, settings, console)

    print_comparison(console, results)

    for result in results:
        print_summary(console, result)
        if not no_save:
            save_to_history(result, console)

    if output:
        from ux_pilot.output.export import export_json, export_markdown
        for result in results:
            export_json(result, output, console)
            export_markdown(result, output, console)


def run_instances(
    template: PersonaTemplate,
    url: str,
    task: str,
    settings: Settings,
    console: Console,
    count: int,
    success_criteria: str | None = None,
    output: str | None = None,
    no_save: bool = False,
) -> None:
    """Run the same persona N times and aggregate results."""
    from ux_pilot.output.comparison import print_comparison
    from ux_pilot.output.summary import print_summary
    from ux_pilot.runner.agent import AgentRunner

    console.print(f"\n[bold cyan]🎭 {template.name}: {count} instances[/]")
    console.print(f"[dim]Non-deterministic LLM behavior — each run may differ.[/]\n")

    prompt_builder = PersonaPromptBuilder()
    system_prompt = prompt_builder.build(
        traits=template.traits, task_description=task,
        success_criteria=success_criteria,
        demographics=dict(template.demographics) if template.demographics else None,
        goals=list(template.goals) if template.goals else None,
        target_url=url,
    )

    results: list[RunResult] = []
    for i in range(1, count + 1):
        console.print(f"[bold]Instance {i}/{count}:[/]")
        runner = AgentRunner(
            target_url=url, task_description=task, settings=settings,
            system_prompt=system_prompt,
            persona_name=f"{template.name} (run {i})",
            traits=dict(template.traits),
            success_criteria=success_criteria,
        )
        result = asyncio.run(runner.run())
        results.append(result)
        status = "✅" if result.task_completed else "❌"
        console.print(f"[dim]{status} Run {i}: {result.total_steps} steps, {result.total_duration_seconds:.0f}s[/]")

    completed = sum(1 for r in results if r.task_completed)
    avg_steps = sum(r.total_steps for r in results) / len(results)
    avg_duration = sum(r.total_duration_seconds for r in results) / len(results)
    avg_satisfaction = sum(r.satisfaction_score for r in results) / len(results)

    console.print()
    console.print(Panel(
        f"[bold]Aggregate ({count} instances)[/]\n"
        f"  Completion: [bold]{completed}/{count}[/] ({completed/count*100:.0f}%)\n"
        f"  Avg steps: {avg_steps:.1f}  |  Avg time: {avg_duration:.1f}s\n"
        f"  Avg satisfaction: {avg_satisfaction:.0f}/100",
        title=f"🎭 {template.name}", border_style="cyan",
    ))

    for result in results:
        analyze_result(result, settings, console)
    print_comparison(console, results)
    for result in results:
        print_summary(console, result)
        if not no_save:
            save_to_history(result, console)
    if output:
        from ux_pilot.output.export import export_json, export_markdown
        for result in results:
            export_json(result, output, console)
            export_markdown(result, output, console)


def analyze_result(result: RunResult, settings: Settings, console: Console) -> None:
    """Run post-completion AI analysis on a result."""
    console.print(f"[dim]Analyzing {result.persona_name}...[/]")
    try:
        from ux_pilot.analysis.analyzer import analyze_run
        analysis = asyncio.run(analyze_run(
            result=result,
            provider=settings.llm_provider,
            model=settings.llm_model,
            api_key=settings.get_api_key(),
        ))
        if analysis.summary:
            result.summary = analysis.summary
        if analysis.recommendations:
            result.recommendations = analysis.recommendations
        if analysis.satisfaction_score:
            result.satisfaction_score = analysis.satisfaction_score
        result.cost.input_tokens += analysis.input_tokens
        result.cost.output_tokens += analysis.output_tokens
        est = (analysis.input_tokens * 0.15 + analysis.output_tokens * 0.60) / 1_000_000
        result.cost.estimated_cost_usd += est
    except Exception as e:
        console.print(f"[dim yellow]Analysis skipped: {e}[/]")


def save_to_history(result: RunResult, console: Console) -> None:
    """Save result to SQLite history."""
    try:
        from ux_pilot.storage.history import save_run
        run_id = save_run(result)
        console.print(f"[dim]💾 Saved to history (ID: {run_id})[/]")
    except Exception as e:
        console.print(f"[dim yellow]History save failed: {e}[/]")
