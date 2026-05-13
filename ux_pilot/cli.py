"""ux-pilot CLI — AI personas that simulate real humans browsing your website."""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Annotated, Optional, TYPE_CHECKING

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from ux_pilot import __version__
from ux_pilot.runner.commands import run_single, run_multi, run_instances

if TYPE_CHECKING:
    from ux_pilot.personas.loader import PersonaTemplate

# Configure root logger with Rich handler for visible log output
logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=Console(stderr=True), rich_tracebacks=True, show_time=False)],
)
logger = logging.getLogger("ux_pilot")

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
        typer.Option("--llm-provider", help="LLM provider: openai, anthropic, deepseek, groq, ollama"),
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
    instances: Annotated[
        int,
        typer.Option("--instances", "-n", help="Run the same persona N times for statistical validity"),
    ] = 1,
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

    # Validate API key (ollama uses local server, no key needed)
    if settings.llm_provider not in ("ollama",) and not settings.get_api_key():
        provider_env = settings.llm_provider.upper() + "_API_KEY"
        console.print(
            f"[bold red]Error:[/] No API key found for provider '{settings.llm_provider}'.\n"
            f"Set it via:\n"
            f"  • Environment variable: [cyan]{provider_env}[/] or [cyan]UX_PILOT_LLM_API_KEY[/]\n"
            f"  • Config file: [cyan]~/.ux-pilot/config.yaml[/]\n"
            f"  • Or use a local model: [cyan]--llm-provider ollama[/]"
        )
        raise typer.Exit(1)

    # Resolve persona(s)
    persona_names = persona if persona else [None]
    is_multi = len(persona_names) > 1 or instances > 1

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

    if instances > 1:
        run_instances(templates[0], url, task, settings, console, instances,
                      success_criteria=success_criteria, output=output, no_save=no_save)
    elif is_multi:
        run_multi(templates, url, task, settings, console,
                  success_criteria=success_criteria, output=output, no_save=no_save)
    else:
        run_single(templates[0], url, task, settings, console,
                   success_criteria=success_criteria, output=output, no_save=no_save)


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


# ── benchmark ─────────────────────────────────────────────────────────────

@app.command()
def benchmark(
    personas: Annotated[
        list[str],
        typer.Option("--persona", "-p", help="Personas to test (repeatable, default: all)"),
    ] = None,
    scenario: Annotated[
        Optional[list[str]],
        typer.Option("--scenario", help="Scenarios to run (repeatable, default: all built-in)"),
    ] = None,
    instances: Annotated[
        int,
        typer.Option("--instances", "-n", help="Runs per scenario-persona pair"),
    ] = 1,
    llm_provider: Annotated[
        Optional[str],
        typer.Option("--llm-provider", help="LLM provider"),
    ] = None,
    llm_model: Annotated[
        Optional[str],
        typer.Option("--llm-model", help="LLM model name"),
    ] = None,
    output: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Directory to save benchmark report"),
    ] = None,
) -> None:
    """Run predefined benchmark scenarios against personas and generate a comparison report."""
    from ux_pilot.config import Settings
    from ux_pilot.benchmark import (
        BUILT_IN_SCENARIOS, run_benchmark, print_benchmark_report, export_benchmark_json,
    )
    from ux_pilot.personas.catalog import CATALOG

    if not _check_playwright():
        raise typer.Exit(1)

    settings = Settings.load(llm_provider=llm_provider, llm_model=llm_model)

    if settings.llm_provider not in ("ollama",) and not settings.get_api_key():
        console.print(f"[bold red]Error:[/] No API key for '{settings.llm_provider}'")
        raise typer.Exit(1)

    # Resolve scenarios
    scenarios = BUILT_IN_SCENARIOS
    if scenario:
        names = set(scenario)
        scenarios = [s for s in BUILT_IN_SCENARIOS if s.name in names]
        if not scenarios:
            console.print(f"[bold red]Error:[/] No matching scenarios. Available: {[s.name for s in BUILT_IN_SCENARIOS]}")
            raise typer.Exit(1)

    # Resolve personas
    persona_names = personas if personas else [p.name for p in CATALOG[:6]]  # Default: first 6
    console.print(f"[bold]🚀 Benchmark: {len(scenarios)} scenarios × {len(persona_names)} personas × {instances} instances[/]")
    console.print(f"[dim]LLM: {settings.llm_provider}/{settings.llm_model or 'default'}[/]")
    console.print()

    results = asyncio.run(run_benchmark(
        scenarios=scenarios,
        personas=persona_names,
        settings=settings,
        console=console,
        instances=instances,
    ))

    print_benchmark_report(console, results)

    if output:
        path = export_benchmark_json(results, output)
        console.print(f"[dim]📄 Report saved to {path}[/]")


if __name__ == "__main__":
    app()
