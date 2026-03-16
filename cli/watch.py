"""
cli/watch.py — Watch mode for RepoRadar.

Re-runs analysis on a repo at a fixed interval, showing a live dashboard
that updates in place using rich Live. Highlights score changes between runs.
"""

import time
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

if TYPE_CHECKING:
    from core.analyzer import AnalysisResult

console = Console()


def _score_delta_str(current: float, previous: Optional[float]) -> str:
    """Format a score delta string with color and arrow."""
    if previous is None:
        return ""
    delta = current - previous
    if abs(delta) < 0.1:
        return " [dim](→ no change)[/dim]"
    arrow = "↑" if delta > 0 else "↓"
    color = "green" if delta > 0 else "red"
    return f" [{color}]({arrow}{abs(delta):.1f})[/{color}]"


def _build_watch_panel(
    result: "AnalysisResult",
    previous: Optional["AnalysisResult"],
    run_count: int,
    interval: int,
    next_run_in: int,
) -> Panel:
    """Build the live-updating rich panel for watch mode."""
    from core.scorer import get_score_color, get_score_label
    from core.verdict import get_verdict_emoji, get_verdict_color

    score_color = get_score_color(result.score)
    verdict_color = get_verdict_color(result.verdict)
    verdict_emoji = get_verdict_emoji(result.verdict)
    score_label = get_score_label(result.score)
    prev_score = previous.score if previous else None
    delta = _score_delta_str(result.score, prev_score)

    # Header
    header = Text()
    header.append(f"  {verdict_emoji} ", style="bold")
    header.append(f"{result.owner}/{result.repo}", style="bold white")
    header.append(f"\n  Score: ", style="dim")
    header.append(f"{result.score:.1f}/100", style=f"bold {score_color}")
    header.append(f"  ({score_label})", style=score_color)
    header.append(delta)
    header.append(f"\n  Verdict: ", style="dim")
    header.append(f"{result.verdict.upper()}", style=f"bold {verdict_color}")
    header.append(f"\n  Last checked: {result.analyzed_at}", style="dim")
    if result.cached:
        header.append("  [cached]", style="dim yellow")
    header.append(f"\n  Run #{run_count}  •  Next refresh in {next_run_in}s  •  Ctrl+C to stop", style="dim")

    # Signal table
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan", expand=False)
    table.add_column("Signal", min_width=22)
    table.add_column("Value", justify="center", min_width=12)
    table.add_column("Score", justify="center", min_width=8)

    VERDICT_COLORS = {"good": "green", "warning": "yellow", "bad": "red"}
    VERDICT_ICONS = {"good": "✅", "warning": "⚠️", "bad": "❌"}

    prev_signals = {s.name: s for s in previous.signals} if previous else {}

    for s in result.signals:
        v_color = VERDICT_COLORS.get(s.verdict, "white")
        v_icon = VERDICT_ICONS.get(s.verdict, "")
        score_pct = s.score * 100

        # Show delta vs previous run for each signal
        signal_delta = ""
        if s.name in prev_signals:
            prev_sig_score = prev_signals[s.name].score * 100
            diff = score_pct - prev_sig_score
            if abs(diff) >= 1:
                arr = "↑" if diff > 0 else "↓"
                sc = "green" if diff > 0 else "red"
                signal_delta = f" [{sc}]{arr}{abs(diff):.0f}[/{sc}]"

        table.add_row(
            f"{s.label}",
            f"[{v_color}]{s.value}[/{v_color}]",
            f"[{v_color}]{v_icon} {score_pct:.0f}[/{v_color}]{signal_delta}",
        )

    from rich.columns import Columns
    from rich.console import Group
    content = Group(header, table)
    return Panel(content, title="[bold]⟳ RepoRadar Watch[/bold]", border_style=verdict_color)


def run_watch(
    owner: str,
    repo: str,
    interval: int,
    analyzer,
    tier: str,
) -> int:
    """Run continuous watch mode, refreshing every `interval` seconds.

    Args:
        owner: GitHub username or org.
        repo: Repository name.
        interval: Seconds between re-checks.
        analyzer: Initialized RepoAnalyzer instance.
        tier: Subscription tier string.

    Returns:
        Exit code.
    """
    from core.github_client import RepoNotFoundError, RateLimitExceededError

    console.print(
        f"\n[bold cyan]⟳ Watching[/bold cyan] [white]{owner}/{repo}[/white] "
        f"[dim]— refreshing every {interval}s — Ctrl+C to stop[/dim]\n"
    )

    previous: Optional["AnalysisResult"] = None
    run_count = 0

    try:
        while True:
            run_count += 1

            # Run analysis
            try:
                with console.status(f"[dim]Fetching {owner}/{repo}…[/dim]"):
                    result = analyzer.analyze(owner, repo)
            except RepoNotFoundError:
                console.print(f"[red]Repository not found:[/red] {owner}/{repo}")
                return 1
            except RateLimitExceededError as exc:
                console.print(f"[yellow]Rate limit hit, waiting…[/yellow] {exc}")
                time.sleep(60)
                continue
            except Exception as exc:
                console.print(f"[red]Analysis error:[/red] {exc}")
                time.sleep(interval)
                continue

            # Countdown + live panel
            with Live(
                _build_watch_panel(result, previous, run_count, interval, interval),
                console=console,
                refresh_per_second=1,
                transient=False,
            ) as live:
                for remaining in range(interval, 0, -1):
                    live.update(
                        _build_watch_panel(result, previous, run_count, interval, remaining)
                    )
                    time.sleep(1)

            previous = result

    except KeyboardInterrupt:
        console.print("\n[dim]Watch stopped.[/dim]")
        return 0