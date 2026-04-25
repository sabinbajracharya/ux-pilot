"""Rich Live dashboard — real-time terminal display during agent runs."""

from __future__ import annotations

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ux_pilot.analysis.models import ActionEntry, EMOTION_EMOJI


class LiveDashboard:
    """Real-time Rich Live display during an agent run.

    Shows: persona header, action feed, frustration bar, monologue, stats.
    """

    def __init__(
        self,
        console: Console,
        persona_name: str,
        target_url: str,
        task: str,
        trait_summary: str = "",
        max_actions: int = 50,
        max_duration_minutes: int = 5,
    ):
        self._console = console
        self._persona_name = persona_name
        self._target_url = target_url
        self._task = task
        self._trait_summary = trait_summary
        self._max_actions = max_actions
        self._max_duration_minutes = max_duration_minutes

        self._actions: list[ActionEntry] = []
        self._current_monologue = ""
        self._frustration_level = 0.0
        self._current_emotion = "neutral"
        self._elapsed_seconds = 0.0
        self._cost_usd = 0.0
        self._live: Live | None = None

    def start(self) -> None:
        self._live = Live(
            self._render(),
            console=self._console,
            refresh_per_second=4,
            transient=True,
        )
        self._live.start()

    def stop(self) -> None:
        if self._live:
            self._live.stop()
            self._live = None

    def update(
        self,
        entry: ActionEntry,
        elapsed_seconds: float = 0.0,
        cost_usd: float = 0.0,
    ) -> None:
        self._actions.append(entry)
        self._current_monologue = entry.monologue or ""
        self._frustration_level = entry.frustration_level
        self._current_emotion = entry.emotion
        self._elapsed_seconds = elapsed_seconds
        self._cost_usd = cost_usd
        if self._live:
            self._live.update(self._render())

    def _render(self) -> Panel:
        """Build the full dashboard panel."""
        parts: list = []

        # Header
        parts.append(self._render_header())

        # Frustration bar
        parts.append(self._render_frustration())

        # Action feed (last 8 entries)
        parts.append(self._render_actions())

        # Monologue
        if self._current_monologue:
            parts.append(self._render_monologue())

        # Stats footer
        parts.append(self._render_stats())

        return Panel(
            Group(*parts),
            title="[bold] UX Pilot [/]",
            border_style="cyan",
        )

    def _render_header(self) -> Text:
        text = Text()
        text.append(f"🎭 {self._persona_name}", style="bold")
        text.append(f" → {self._target_url}\n", style="dim")
        text.append(f"Task: {self._task[:80]}", style="")
        if self._trait_summary:
            text.append(f"\n{self._trait_summary}", style="dim")
        return text

    def _render_frustration(self) -> Text:
        level = self._frustration_level
        width = 20
        filled = int(level / 100 * width)

        if level >= 60:
            color = "red"
        elif level >= 30:
            color = "yellow"
        else:
            color = "green"

        emoji = EMOTION_EMOJI.get(self._current_emotion, "😐")
        text = Text()
        text.append("Frustration: ")
        text.append("▰" * filled, style=color)
        text.append("▱" * (width - filled), style="dim")
        text.append(f" {level:.0f}%  {emoji} {self._current_emotion}")
        return text

    def _render_actions(self) -> Table:
        table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
        table.add_column("num", width=4, style="dim")
        table.add_column("em", width=3)
        table.add_column("type", width=10, style="bold")
        table.add_column("desc", ratio=1)
        table.add_column("url", width=30, style="dim")

        visible = self._actions[-8:]
        for entry in visible:
            emoji = EMOTION_EMOJI.get(entry.emotion, "😐")
            status_mark = "" if entry.was_successful else "[red]✗[/]"
            url_short = (entry.page_url or "")[-30:]
            desc = entry.description[:50] if entry.description else ""
            table.add_row(
                f"#{entry.sequence}",
                emoji,
                f"{status_mark}{entry.action_type}",
                desc,
                url_short,
            )

        return table

    def _render_monologue(self) -> Text:
        text = Text()
        text.append(f'💭 "{self._current_monologue}"', style="italic dim")
        return text

    def _render_stats(self) -> Text:
        steps = len(self._actions)
        elapsed = self._elapsed_seconds
        cost = self._cost_usd

        # Action type counts
        type_counts: dict[str, int] = {}
        for a in self._actions:
            type_counts[a.action_type] = type_counts.get(a.action_type, 0) + 1

        action_summary = " ".join(
            f"{_action_emoji(t)}{c}" for t, c in sorted(type_counts.items(), key=lambda x: -x[1])[:4]
        )

        text = Text()
        text.append(
            f"Steps: {steps}/{self._max_actions} │ "
            f"Time: {elapsed:.0f}s/{self._max_duration_minutes * 60}s │ "
            f"Cost: ~${cost:.4f} │ {action_summary}",
            style="dim",
        )
        return text


def _action_emoji(action_type: str) -> str:
    return {
        "click": "🖱",
        "scroll": "📜",
        "navigate": "🔗",
        "type": "⌨️",
        "hover": "👆",
        "select": "📋",
        "go_back": "↩️",
        "done": "✅",
    }.get(action_type, "•")
