"""
cli/output.py — Rich-formatted terminal output for RepoRadar CLI.

All terminal rendering lives here. No plain print() calls — use rich exclusively.
"""

import json
from typing import TYPE_CHECKING, List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

if TYPE_CHECKING:
    from core.analyzer import AnalysisResult

from core.scorer import get_score_label, get_score_color
from core.verdict import get_verdict_emoji, get_verdict_color

console = Console()


def render_result(result: "AnalysisResult", tier: str) -> None:
    """Render a full analysis result to the terminal.

    Shows score, verdict, signal breakdown, recommendations, and watermark (free tier).

    Args:
        result: Completed AnalysisResult.
        tier: 'free' or 'paid'.
    """
    score_color = get_score_color(result.score)
    verdict_color = get_verdict_color(result.verdict)
    verdict_emoji = get_verdict_emoji(result.verdict)
    score_label = get_score_label(result.score)

    # Header panel
    header = Text()
    header.append(f"  {verdict_emoji} ", style="bold")
    header.append(f"{result.owner}/{result.repo}", style="bold white")
    header.append(f"\n  Score: ", style="dim")
    header.append(f"{result.score:.1f}/100", style=f"bold {score_color}")
    header.append(f"  ({score_label})", style=score_color)
    header.append(f"\n  Verdict: ", style="dim")
    header.append(f"{result.verdict.upper()}", style=f"bold {verdict_color}")
    header.append(f"\n  {result.url}", style="dim cyan")
    header.append(f"\n  Analyzed: {result.analyzed_at}", style="dim")
    if result.cached:
        header.append("  [cached]", style="dim yellow")

    console.print(Panel(header, title="[bold]RepoRadar Analysis[/bold]", border_style=verdict_color))

    # Signal table
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan", expand=False)
    table.add_column("Signal", min_width=22)
    table.add_column("Value", justify="center", min_width=12)
    table.add_column("Score", justify="center", min_width=8)
    table.add_column("Detail", min_width=36)

    VERDICT_COLORS = {"good": "green", "warning": "yellow", "bad": "red"}
    VERDICT_ICONS = {"good": "✅", "warning": "⚠️", "bad": "❌"}

    for s in result.signals:
        v_color = VERDICT_COLORS.get(s.verdict, "white")
        v_icon = VERDICT_ICONS.get(s.verdict, "")
        tier_badge = "" if s.is_free_tier else " [dim][paid][/dim]"
        table.add_row(
            f"{s.label}{tier_badge}",
            f"[{v_color}]{s.value}[/{v_color}]",
            f"[{v_color}]{v_icon} {s.score * 100:.0f}[/{v_color}]",
            f"[dim]{s.detail[:60]}{'…' if len(s.detail) > 60 else ''}[/dim]",
        )

    console.print(table)

    # Recommendations
    recommendations = result.report.get("recommendations", [])
    if recommendations:
        console.print("\n[bold]Recommendations:[/bold]")
        for rec in recommendations:
            console.print(f"  {rec}")

    # Summary
    summary = result.report.get("summary", "")
    if summary:
        console.print(f"\n[dim]{summary}[/dim]")

    # Duration
    console.print(f"\n[dim]Analysis took {result.duration_ms}ms[/dim]")

    # Free tier watermark
    if tier != "paid":
        console.print(
            "\n[dim italic]RepoRadar Free — upgrade for full report (all 8 signals, "
            "JSON/Markdown export, history) at reporadar.dev[/dim italic]"
        )


def render_bulk_results(results: List["AnalysisResult"]) -> None:
    """Render a summary table for multiple bulk analysis results.

    Args:
        results: List of completed AnalysisResult objects.
    """
    table = Table(
        title="[bold]RepoRadar Bulk Analysis[/bold]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Repository", min_width=30)
    table.add_column("Score", justify="center", min_width=8)
    table.add_column("Label", min_width=14)
    table.add_column("Verdict", justify="center", min_width=10)
    table.add_column("Cached", justify="center", min_width=7)

    VERDICT_COLORS = {"alive": "green", "uncertain": "yellow", "dead": "red"}

    for r in results:
        v_color = VERDICT_COLORS.get(r.verdict, "white")
        score_color = get_score_color(r.score)
        emoji = get_verdict_emoji(r.verdict)
        table.add_row(
            f"{r.owner}/{r.repo}",
            f"[{score_color}]{r.score:.1f}[/{score_color}]",
            get_score_label(r.score),
            f"[{v_color}]{emoji} {r.verdict.upper()}[/{v_color}]",
            "✓" if r.cached else "–",
        )

    console.print(table)
    console.print(f"\n[dim]Checked {len(results)} repositories.[/dim]")


def render_json(result: "AnalysisResult") -> None:
    """Render a full analysis result as formatted JSON.

    Args:
        result: Completed AnalysisResult.
    """
    output = {
        "owner": result.owner,
        "repo": result.repo,
        "url": result.url,
        "score": result.score,
        "score_label": get_score_label(result.score),
        "verdict": result.verdict,
        "verdict_emoji": get_verdict_emoji(result.verdict),
        "tier": result.tier,
        "cached": result.cached,
        "analyzed_at": result.analyzed_at,
        "duration_ms": result.duration_ms,
        "signals": [
            {
                "name": s.name,
                "label": s.label,
                "score": round(s.score * 100, 1),
                "weight": s.weight,
                "value": s.value,
                "verdict": s.verdict,
                "detail": s.detail,
                "is_free_tier": s.is_free_tier,
            }
            for s in result.signals
        ],
        "summary": result.report.get("summary", ""),
        "recommendations": result.report.get("recommendations", []),
    }
    console.print_json(json.dumps(output, indent=2))


def render_markdown(result: "AnalysisResult") -> str:
    """Build a Markdown-formatted report string for a result.

    Args:
        result: Completed AnalysisResult.

    Returns:
        Markdown string.
    """
    score_label = get_score_label(result.score)
    verdict_emoji = get_verdict_emoji(result.verdict)
    lines = [
        f"# RepoRadar Report: {result.owner}/{result.repo}",
        "",
        f"**Score:** {result.score:.1f}/100 ({score_label})  ",
        f"**Verdict:** {verdict_emoji} {result.verdict.upper()}  ",
        f"**URL:** {result.url}  ",
        f"**Analyzed:** {result.analyzed_at}  ",
        f"**Tier:** {result.tier}  ",
        "",
        "## Signals",
        "",
        "| Signal | Value | Score | Detail |",
        "|--------|-------|-------|--------|",
    ]
    for s in result.signals:
        tier_note = "" if s.is_free_tier else " *(paid)*"
        lines.append(
            f"| {s.label}{tier_note} | {s.value} | {s.score * 100:.0f}/100 | {s.detail} |"
        )

    lines += [
        "",
        "## Summary",
        "",
        result.report.get("summary", ""),
        "",
        "## Recommendations",
        "",
    ]
    for rec in result.report.get("recommendations", []):
        lines.append(f"- {rec}")

    lines += [
        "",
        "---",
        f"*Generated by RepoRadar — reporadar.dev*",
    ]
    return "\n".join(lines)


def render_upgrade_prompt(feature: str, message: str) -> None:
    """Display a styled upgrade prompt when a paid feature is accessed on free tier.

    Args:
        feature: The feature name that requires upgrade.
        message: The full upgrade message to display.
    """
    console.print(
        Panel(
            f"[yellow]🔒 {message}[/yellow]",
            title=f"[bold yellow]Upgrade Required: {feature}[/bold yellow]",
            border_style="yellow",
        )
    )


def render_history(entries: List[dict]) -> None:
    """Render a history table to the terminal.

    Args:
        entries: List of history entry dicts from audit_log.get_history().
    """
    if not entries:
        console.print("[dim]No history entries found.[/dim]")
        return

    table = Table(
        title="[bold]RepoRadar History[/bold]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Date", min_width=12)
    table.add_column("Repository", min_width=28)
    table.add_column("Score", justify="center", min_width=8)
    table.add_column("Verdict", justify="center", min_width=10)
    table.add_column("Tier", justify="center", min_width=6)
    table.add_column("Duration", justify="right", min_width=9)

    VERDICT_COLORS = {"alive": "green", "uncertain": "yellow", "dead": "red"}

    for e in entries:
        ts = e.get("timestamp", "")[:10]
        repo = e.get("repo", "")
        score = e.get("score", 0)
        verdict = e.get("verdict", "")
        tier = e.get("tier", "free")
        duration_ms = e.get("duration_ms", 0)
        v_color = VERDICT_COLORS.get(verdict, "white")
        score_color = get_score_color(float(score))

        table.add_row(
            ts,
            repo,
            f"[{score_color}]{score:.1f}[/{score_color}]",
            f"[{v_color}]{verdict.upper()}[/{v_color}]",
            tier,
            f"{duration_ms}ms",
        )

    console.print(table)


def render_history_stats(stats: dict) -> None:
    """Render history statistics as a rich panel.

    Args:
        stats: Stats dict from audit_log.get_history_stats().
    """
    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column("Key", style="bold cyan")
    table.add_column("Value")

    table.add_row("Total entries", str(stats.get("total_entries", 0)))
    table.add_row("Unique repos", str(stats.get("unique_repos", 0)))
    table.add_row("Most checked", stats.get("most_checked_repo", "—"))
    table.add_row("Average score", f"{stats.get('avg_score', 0.0):.1f}/100")
    table.add_row("Oldest entry", stats.get("oldest_entry", "—")[:10] or "—")
    table.add_row("Newest entry", stats.get("newest_entry", "—")[:10] or "—")

    console.print(Panel(table, title="[bold]History Stats[/bold]", border_style="cyan"))


def render_trend(trend: dict, repo: str) -> None:
    """Render a score trend sparkline for a repository.

    Uses Unicode block characters: ▁▂▃▄▅▆▇█

    Args:
        trend: Trend dict from audit_log.get_trend().
        repo: Repository slug string.
    """
    BLOCKS = "▁▂▃▄▅▆▇█"

    entries = trend.get("entries", [])
    scores = [e.get("score", 0) for e in entries if isinstance(e.get("score"), (int, float))]

    if not scores:
        console.print("[dim]No scores to display.[/dim]")
        return

    # Normalize scores to block indices
    min_s = min(scores)
    max_s = max(scores)
    rng = max_s - min_s if max_s != min_s else 1

    sparkline = ""
    for s in scores:
        idx = int((s - min_s) / rng * (len(BLOCKS) - 1))
        sparkline += BLOCKS[idx]

    trend_label = trend.get("trend", "stable")
    score_change = trend.get("score_change", 0.0)
    trend_color = {"improving": "green", "declining": "red", "stable": "yellow"}.get(
        trend_label, "white"
    )
    arrow = {"improving": "↑", "declining": "↓", "stable": "→"}.get(trend_label, "")

    console.print(f"\n[bold]Score trend for[/bold] [cyan]{repo}[/cyan]")
    console.print(f"  [bold]{sparkline}[/bold]")
    console.print(
        f"  [{trend_color}]{arrow} {trend_label.capitalize()} "
        f"({score_change:+.1f} pts, {len(scores)} checks)[/{trend_color}]"
    )
    console.print(
        f"  [dim]Range: {min_s:.1f}–{max_s:.1f} | "
        f"Latest: {scores[-1]:.1f}/100[/dim]\n"
    )