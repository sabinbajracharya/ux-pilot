"""ux-pilot CLI — AI personas that simulate real humans browsing your website."""

from __future__ import annotations

import asyncio
import sys
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from ux_pilot import __version__

app = typer.Typer(
    name="ux-pilot",
    help="AI personas that simulate real humans browsing your website — find UX friction from the command line.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
personas_app = typer.Typer(help="List and inspect built-in personas.")
app.add_typer(personas_app, name="personas")
history_app = typer.Typer(help="View past run history.")
app.add_typer(history_app, name="history")

console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"ux-pilot [bold cyan]v{__version__}[/]")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-v", help="Show version and exit.", callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    """ux-pilot — AI-powered UX testing from the command line."""


# ── personas list ──────────────────────────────────────────────────────────

@personas_app.command("list")
def personas_list() -> None:
    """List all built-in personas with trait summaries."""
    from ux_pilot.personas.catalog import CATALOG
    from ux_pilot.personas.traits import TRAIT_EMOJI, TRAIT_SHORT, trait_level_label

    table = Table(title="Built-in Personas", show_lines=True)
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Name", style="bold")
    table.add_column("Category", style="cyan")
    table.add_column("Key Traits")
    table.add_column("Description", max_width=50)

    for i, p in enumerate(CATALOG, 1):
        # Show the 4 most extreme traits (furthest from 50)
        sorted_traits = sorted(
            p.traits.items(),
            key=lambda t: abs(t[1] - 50),
            reverse=True,
        )[:4]
        trait_str = " · ".join(
            f"{TRAIT_EMOJI.get(k, '•')} {p.traits[k]} {TRAIT_SHORT.get(k, k)}"
            for k, _ in sorted_traits
        )
        table.add_row(str(i), p.name, p.category, trait_str, p.description[:50] + "...")

    console.print(table)


# ── personas show ──────────────────────────────────────────────────────────

@personas_app.command("show")
def personas_show(
    name: Annotated[str, typer.Argument(help="Persona name or number")],
) -> None:
    """Show detailed info about a specific persona."""
    from ux_pilot.personas.loader import _resolve_from_catalog
    from ux_pilot.personas.traits import TRAIT_EMOJI, OCEAN_TRAITS, BROWSING_TRAITS, trait_level_label

    try:
        persona = _resolve_from_catalog(name)
    except ValueError as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1)

    lines = [f"[bold]{persona.name}[/] ({persona.category})", f"[dim]{persona.description}[/]", ""]

    lines.append("[bold]OCEAN Traits:[/]")
    for t in OCEAN_TRAITS:
        v = persona.traits.get(t, 50)
        bar = _trait_bar(v)
        lines.append(f"  {TRAIT_EMOJI.get(t, '•')} {t:<20} {bar} {v:>3} ({trait_level_label(v)})")

    lines.append("")
    lines.append("[bold]Browsing Traits:[/]")
    for t in BROWSING_TRAITS:
        v = persona.traits.get(t, 50)
        bar = _trait_bar(v)
        lines.append(f"  {TRAIT_EMOJI.get(t, '•')} {t:<20} {bar} {v:>3} ({trait_level_label(v)})")

    if persona.goals:
        lines.append("")
        lines.append("[bold]Goals:[/]")
        for g in persona.goals:
            lines.append(f"  • {g}")

    console.print(Panel("\n".join(lines), title=f"🎭 {persona.name}", border_style="cyan"))


def _trait_bar(value: int, width: int = 20) -> str:
    """Render a compact visual bar for a 0-100 value."""
    filled = int(value / 100 * width)
    return f"[green]{'▰' * filled}[/][dim]{'▱' * (width - filled)}[/]"


def _frustration_bar(level: float, width: int = 5) -> str:
    """Compact frustration indicator: green→yellow→red."""
    filled = int(level / 100 * width)
    if level >= 60:
        color = "red"
    elif level >= 30:
        color = "yellow"
    else:
        color = "green"
    return f"[{color}]{'▰' * filled}[/][dim]{'▱' * (width - filled)}[/] [dim]{level:.0f}%[/]"


# ── run ────────────────────────────────────────────────────────────────────

@app.command()
def run(
    url: Annotated[str, typer.Option("--url", "-u", help="Target website URL to test")],
    task: Annotated[str, typer.Option("--task", "-t", help="Task for the persona to perform")],
    persona: Annotated[
        Optional[list[str]],
        typer.Option("--persona", "-p", help="Persona name or number (repeatable for comparison)"),
    ] = None,
    persona_file: Annotated[
        Optional[str],
        typer.Option("--persona-file", help="Load custom persona from YAML file"),
    ] = None,
    trait: Annotated[
        Optional[list[str]],
        typer.Option("--trait", help="Override trait value (e.g. neuroticism=80)"),
    ] = None,
    success_criteria: Annotated[
        Optional[str],
        typer.Option("--success-criteria", "-s", help="Optional success criteria for task evaluation"),
    ] = None,
    llm_provider: Annotated[
        Optional[str],
        typer.Option("--llm-provider", help="LLM provider: openai, anthropic, groq, ollama"),
    ] = None,
    llm_model: Annotated[
        Optional[str],
        typer.Option("--llm-model", help="LLM model name"),
    ] = None,
    headed: Annotated[
        bool,
        typer.Option("--headed/--headless", help="Show browser window"),
    ] = False,
    max_actions: Annotated[
        Optional[int],
        typer.Option("--max-actions", help="Maximum number of actions"),
    ] = None,
    max_duration: Annotated[
        Optional[int],
        typer.Option("--max-duration", help="Maximum duration in minutes"),
    ] = None,
    output: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Directory to save results"),
    ] = None,
    no_save: Annotated[
        bool,
        typer.Option("--no-save", help="Don't save to history"),
    ] = False,
) -> None:
    """Run an AI persona against a website to find UX issues."""
    from ux_pilot.config import Settings
    from ux_pilot.personas.loader import load_persona
    from ux_pilot.personas.prompt_builder import PersonaPromptBuilder

    # Check for Playwright
    if not _check_playwright():
        raise typer.Exit(1)

    # Load settings
    settings = Settings.load(
        llm_provider=llm_provider,
        llm_model=llm_model,
        headed=headed if headed else None,
        max_actions=max_actions,
        max_duration_minutes=max_duration,
        output_dir=output,
    )

    # Validate API key
    if settings.llm_provider != "ollama" and not settings.get_api_key():
        console.print(
            f"[bold red]Error:[/] No API key found for provider '{settings.llm_provider}'.\n"
            f"Set it via:\n"
            f"  • Environment variable: [cyan]UX_PILOT_LLM_API_KEY[/] or [cyan]OPENAI_API_KEY[/]\n"
            f"  • Config file: [cyan]~/.ux-pilot/config.yaml[/]\n"
            f"  • CLI flag: [cyan]--llm-provider ollama[/] (for local models)"
        )
        raise typer.Exit(1)

    # Resolve persona(s)
    persona_names = persona if persona else [None]
    is_multi = len(persona_names) > 1

    templates = []
    for pname in persona_names:
        try:
            tmpl = load_persona(
                name=pname,
                persona_file=persona_file if not is_multi else None,
                trait_overrides=trait if not is_multi else None,
            )
            templates.append(tmpl)
        except (ValueError, FileNotFoundError) as e:
            console.print(f"[bold red]Error:[/] {e}")
            raise typer.Exit(1)

    if is_multi:
        # Multi-persona comparison mode
        _run_multi(templates, url, task, settings, success_criteria, output, no_save)
    else:
        _run_single(templates[0], url, task, settings, success_criteria, output, no_save)


def _check_playwright() -> bool:
    """Check if Playwright and chromium are available."""
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        console.print(
            "[bold red]Error:[/] Playwright is not installed.\n"
            "Install it with:\n"
            "  [cyan]pip install playwright[/]\n"
            "  [cyan]playwright install chromium[/]"
        )
        return False


def _run_single(template, url, task, settings, success_criteria, output, no_save):
    """Run a single persona with live dashboard."""
    from ux_pilot.personas.prompt_builder import PersonaPromptBuilder
    from ux_pilot.personas.traits import TRAIT_EMOJI, TRAIT_SHORT
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

    # Display run header
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
    console.print(f"[dim]LLM: {settings.llm_provider}/{settings.llm_model or 'default'} │ Max: {settings.max_actions} actions, {settings.max_duration_minutes}min[/]")
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

    _analyze_result(result, settings)
    print_summary(console, result)

    if not no_save:
        _save_to_history(result)
    if output:
        from ux_pilot.output.export import export_json, export_markdown
        export_json(result, output, console)
        export_markdown(result, output, console)


def _run_multi(templates, url, task, settings, success_criteria, output, no_save):
    """Run multiple personas sequentially with comparison table."""
    from ux_pilot.runner.orchestrator import run_multi_persona
    from ux_pilot.output.comparison import print_comparison
    from ux_pilot.output.summary import print_summary

    console.print(f"\n[bold cyan]🎭 Multi-persona run: {len(templates)} personas[/]")
    console.print(f"[bold cyan]🌐 URL:[/]  {url}")
    console.print(f"[bold cyan]📋 Task:[/] {task}")
    console.print()

    results = asyncio.run(run_multi_persona(
        url=url,
        task=task,
        personas=templates,
        settings=settings,
        console=console,
        success_criteria=success_criteria,
    ))

    # Analyze each result
    for result in results:
        _analyze_result(result, settings)

    # Print comparison table
    print_comparison(console, results)

    # Print individual summaries
    for result in results:
        print_summary(console, result)
        if not no_save:
            _save_to_history(result)

    if output:
        from ux_pilot.output.export import export_json, export_markdown
        for result in results:
            export_json(result, output, console)
            export_markdown(result, output, console)


def _analyze_result(result, settings):
    """Run post-completion AI analysis on a result."""
    console.print(f"[dim]Analyzing {result.persona_name}...[/]")
    try:
        from ux_pilot.analysis.analyzer import analyze_run
        analysis = asyncio.run(analyze_run(
            result=result,
            provider=settings.llm_provider,
            model=settings.llm_model or "gpt-4o-mini",
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


def _save_to_history(result):
    """Save result to SQLite history."""
    try:
        from ux_pilot.storage.history import save_run
        run_id = save_run(result)
        console.print(f"[dim]💾 Saved to history (ID: {run_id})[/]")
    except Exception as e:
        console.print(f"[dim yellow]History save failed: {e}[/]")


# ── history commands ───────────────────────────────────────────────────────

@history_app.command("list")
def history_list(
    limit: Annotated[int, typer.Option("--limit", "-n", help="Number of runs to show")] = 20,
) -> None:
    """List past runs from history."""
    from ux_pilot.storage.history import list_runs

    runs = list_runs(limit=limit)
    if not runs:
        console.print("[dim]No runs in history yet.[/]")
        return

    table = Table(title="Run History", show_lines=True)
    table.add_column("ID", style="dim", width=4)
    table.add_column("Date", width=16)
    table.add_column("Persona", style="bold")
    table.add_column("URL", max_width=30)
    table.add_column("Result", justify="center", width=8)
    table.add_column("Steps", justify="right", width=5)
    table.add_column("Cost", justify="right", width=8)

    for r in runs:
        status = "[green]✅[/]" if r["task_completed"] else "[red]❌[/]"
        date = r["created_at"][:16] if r["created_at"] else "—"
        url_short = (r["target_url"] or "")[:30]
        cost = f"${r['cost_usd']:.4f}" if r.get("cost_usd") else "—"
        table.add_row(str(r["id"]), date, r["persona_name"], url_short, status, str(r["total_steps"]), cost)

    console.print(table)


@history_app.command("show")
def history_show(
    run_id: Annotated[int, typer.Argument(help="Run ID to show")],
) -> None:
    """Show details of a past run."""
    from ux_pilot.storage.history import get_run

    run = get_run(run_id)
    if not run:
        console.print(f"[bold red]Error:[/] Run {run_id} not found")
        raise typer.Exit(1)

    lines = [
        f"[bold]{run['persona_name']}[/]",
        f"URL: {run['target_url']}",
        f"Task: {run['task_description']}",
        f"Result: {'✅ Completed' if run['task_completed'] else '❌ Not completed'}",
        f"Steps: {run['total_steps']} │ Duration: {run['total_duration_seconds']:.1f}s",
        f"Frustration: {run['frustration_level']:.0f}%",
        f"Score: {run['satisfaction_score']}/100",
        f"Date: {run['created_at']}",
    ]

    if run.get("friction_points"):
        lines.append("")
        lines.append("[bold yellow]Friction:[/]")
        for fp in run["friction_points"][:5]:
            lines.append(f"  • {fp}")

    if run.get("recommendations"):
        lines.append("")
        lines.append("[bold]Recommendations:[/]")
        for rec in run["recommendations"][:5]:
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec.get("priority", ""), "•")
            lines.append(f"  {icon} {rec.get('title', '')}")
            if rec.get("description"):
                lines.append(f"    {rec['description'][:100]}")

    console.print(Panel("\n".join(lines), title=f"Run #{run_id}", border_style="cyan"))


if __name__ == "__main__":
    app()
