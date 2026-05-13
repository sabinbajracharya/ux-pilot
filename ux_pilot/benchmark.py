"""Benchmark mode — run predefined scenarios and generate comparison reports."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


@dataclass
class BenchmarkScenario:
    name: str
    url: str
    task: str
    description: str = ""
    expected_personas_succeed: list[str] = field(default_factory=list)
    expected_personas_struggle: list[str] = field(default_factory=list)


@dataclass
class ScenarioResult:
    scenario: str
    persona: str
    completed: bool
    steps: int
    duration: float
    satisfaction: int
    frustration: float
    stop_reason: str = ""


BUILT_IN_SCENARIOS: list[BenchmarkScenario] = [
    BenchmarkScenario(
        name="quick-find",
        url="https://books.toscrape.com",
        task="Find a book under £15 and tell me its title.",
        description="Simple single-page task — should be easy for fast decision-makers.",
        expected_personas_succeed=["Impulse Shopper", "Tech-Savvy Professional"],
        expected_personas_struggle=["Careful Researcher", "Senior User"],
    ),
    BenchmarkScenario(
        name="compare-and-choose",
        url="https://books.toscrape.com",
        task="Browse the mystery category. Look at the details of at least 2 different books. Compare their prices and pick the best one. Explain your choice.",
        description="Multi-step comparison — methodical personas should excel.",
        expected_personas_succeed=["Careful Researcher", "Price Hunter"],
        expected_personas_struggle=["Impulse Shopper", "Social Media Scroller"],
    ),
    BenchmarkScenario(
        name="anxious-checkout",
        url="https://books.toscrape.com",
        task="Find a book you like. Imagine you need to buy it as a gift. You're worried about picking the wrong thing — read the description carefully before deciding.",
        description="Gift-shopping with anxiety — tests emotional response.",
        expected_personas_succeed=["Brand Loyal Enthusiast"],
        expected_personas_struggle=["Anxious First-Timer", "Privacy-Conscious User"],
    ),
    BenchmarkScenario(
        name="budget-shopping",
        url="https://books.toscrape.com",
        task="You have exactly £20 to spend. Find a book under £20. Then check if there's an even cheaper option. Pick the cheapest one you can find.",
        description="Budget-constrained shopping — price sensitivity test.",
        expected_personas_succeed=["Price Hunter", "Weekend Deal Hunter"],
        expected_personas_struggle=["Brand Loyal Enthusiast", "Power Admin"],
    ),
    BenchmarkScenario(
        name="exploration",
        url="https://books.toscrape.com",
        task="Explore the website freely. Look at different categories. Find something interesting that you weren't looking for. Tell me what you discovered.",
        description="Open exploration — tests openness and curiosity.",
        expected_personas_succeed=["Social Media Scroller", "Tech-Savvy Professional"],
        expected_personas_struggle=["Senior User", "Anxious First-Timer"],
    ),
]


async def run_benchmark(
    scenarios: list[BenchmarkScenario],
    personas: list[str],
    settings,
    console: Console,
    instances: int = 1,
) -> list[ScenarioResult]:
    """Run all scenarios against all personas. Returns flat list of results."""
    from ux_pilot.personas.loader import load_persona
    from ux_pilot.personas.prompt_builder import PersonaPromptBuilder
    from ux_pilot.runner.agent import AgentRunner

    all_results: list[ScenarioResult] = []

    for scenario in scenarios:
        console.print(f"\n[bold]📋 Scenario: {scenario.name}[/] — {scenario.description}")
        console.print(f"[dim]   URL: {scenario.url}[/]")

        for persona_name in personas:
            console.print(f"[dim]   🎭 {persona_name}...[/]", end=" ")

            try:
                template = load_persona(name=persona_name)
            except (ValueError, FileNotFoundError):
                console.print("[red]NOT FOUND[/]")
                continue

            prompt_builder = PersonaPromptBuilder()
            system_prompt = prompt_builder.build(
                traits=template.traits,
                task_description=scenario.task,
                demographics=dict(template.demographics) if template.demographics else None,
                goals=list(template.goals) if template.goals else None,
                target_url=scenario.url,
            )

            for i in range(instances):
                runner = AgentRunner(
                    target_url=scenario.url,
                    task_description=scenario.task,
                    settings=settings,
                    system_prompt=system_prompt,
                    persona_name=template.name,
                    traits=dict(template.traits),
                )
                result = await runner.run()

                # Run post-completion analysis for satisfaction score
                try:
                    from ux_pilot.analysis.analyzer import analyze_run
                    analysis = await analyze_run(
                        result=result, provider=settings.llm_provider,
                        model=settings.llm_model, api_key=settings.get_api_key(),
                    )
                    if analysis.satisfaction_score:
                        result.satisfaction_score = analysis.satisfaction_score
                except Exception:
                    pass  # Analysis is best-effort in benchmark mode

                all_results.append(ScenarioResult(
                    scenario=scenario.name,
                    persona=template.name,
                    completed=result.task_completed,
                    steps=result.total_steps,
                    duration=result.total_duration_seconds,
                    satisfaction=result.satisfaction_score,
                    frustration=result.frustration_level,
                    stop_reason=result.failure_reason or "",
                ))
                status = "✅" if result.task_completed else "❌"
                console.print(f"{status} ({result.total_steps} steps, {result.total_duration_seconds:.0f}s)")

    return all_results


def print_benchmark_report(console: Console, results: list[ScenarioResult]) -> None:
    """Print a comprehensive benchmark comparison report."""
    if not results:
        console.print("[dim]No results to report.[/]")
        return

    # Per-scenario summary
    scenarios = sorted(set(r.scenario for r in results))
    personas = sorted(set(r.persona for r in results))

    console.print()
    console.print(Panel("[bold]📊 Benchmark Report[/]", border_style="cyan"))

    # Completion rate table
    table = Table(title="Completion Rate by Scenario & Persona")
    table.add_column("Scenario", style="bold")
    for p in personas:
        table.add_column(p, justify="center", width=max(10, len(p) + 2))

    for scenario in scenarios:
        row = [scenario]
        for persona in personas:
            matches = [r for r in results if r.scenario == scenario and r.persona == persona]
            if matches:
                completed = sum(1 for r in matches if r.completed)
                row.append(f"[{'green' if completed > 0 else 'red'}]{completed}/{len(matches)}[/]")
            else:
                row.append("—")
        table.add_row(*row)

    console.print(table)

    # Stats table
    stats_table = Table(title="Average Metrics per Persona")
    stats_table.add_column("Persona", style="bold")
    stats_table.add_column("Avg Steps", justify="right")
    stats_table.add_column("Avg Time", justify="right")
    stats_table.add_column("Avg Frustration", justify="right")
    stats_table.add_column("Avg Satisfaction", justify="right")
    stats_table.add_column("Completion Rate", justify="right")

    for persona in personas:
        matches = [r for r in results if r.persona == persona]
        if matches:
            avg_steps = sum(r.steps for r in matches) / len(matches)
            avg_time = sum(r.duration for r in matches) / len(matches)
            avg_frust = sum(r.frustration for r in matches) / len(matches)
            avg_sat = sum(r.satisfaction for r in matches) / len(matches)
            comp_rate = sum(1 for r in matches if r.completed) / len(matches) * 100
            stats_table.add_row(
                persona,
                f"{avg_steps:.1f}",
                f"{avg_time:.0f}s",
                f"{avg_frust:.0f}%",
                f"{avg_sat:.0f}",
                f"{comp_rate:.0f}%",
            )

    console.print(stats_table)

    # Persona-specific findings
    console.print()
    console.print("[bold]Persona-Specific Findings:[/]")
    for scenario in sorted(set(r.scenario for r in results)):
        scenario_results = [r for r in results if r.scenario == scenario]
        console.print(f"  [bold]{scenario}:[/]")
        # Best and worst persona for this scenario
        best = max(scenario_results, key=lambda r: (r.completed, -r.frustration, r.satisfaction))
        worst = max(scenario_results, key=lambda r: (not r.completed, r.frustration, -r.satisfaction))
        if best.completed and not worst.completed:
            console.print(f"    [green]Best: {best.persona}[/] (completed in {best.steps} steps) vs [red]Worst: {worst.persona}[/] (failed: {worst.stop_reason})")
        elif best.completed and worst.completed:
            console.print(f"    [green]Fastest: {best.persona}[/] ({best.steps} steps, {best.duration:.0f}s) — [yellow]Slowest: {worst.persona}[/] ({worst.steps} steps, {worst.duration:.0f}s)")
        elif not best.completed:
            console.print(f"    [red]All personas failed this scenario[/] — likely a site accessibility issue")

    # Key insights
    console.print()
    console.print("[bold]Key Insights:[/]")
    for persona in personas:
        matches = [r for r in results if r.persona == persona]
        if not matches:
            continue
        avg_frust = sum(r.frustration for r in matches) / len(matches)
        avg_steps = sum(r.steps for r in matches) / len(matches)
        comp_rate = sum(1 for r in matches if r.completed) / len(matches) * 100

        if comp_rate >= 50 and avg_frust <= 30:
            console.print(f"  [green]✓ {persona}:[/] Consistently successful, low frustration ({avg_frust:.0f}%)")
        elif comp_rate >= 50 and avg_frust > 30:
            console.print(f"  [yellow]△ {persona}:[/] Succeeds but with high frustration ({avg_frust:.0f}%) — UX friction likely")
        elif comp_rate < 50 and avg_frust > 50:
            console.print(f"  [red]✗ {persona}:[/] Frequently abandons tasks ({avg_frust:.0f}% frustration) — major UX barriers")
        else:
            console.print(f"  [dim]— {persona}:[/] Mixed results ({comp_rate:.0f}% completion)")


def export_benchmark_json(results: list[ScenarioResult], output_dir: str) -> str:
    """Export benchmark results as JSON."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"benchmark_{timestamp}.json")
    data = [
        {
            "scenario": r.scenario,
            "persona": r.persona,
            "completed": r.completed,
            "steps": r.steps,
            "duration": r.duration,
            "satisfaction": r.satisfaction,
            "frustration": r.frustration,
            "stop_reason": r.stop_reason,
        }
        for r in results
    ]
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path
