"""
cli/compare.py — Side-by-side repository comparison for RepoRadar.

Renders two AnalysisResult objects in a rich table with per-signal diffs,
a winner declaration, and a recommendation on which repo to choose.
"""

from typing import TYPE_CHECKING, List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

if TYPE_CHECKING:
    from core.analyzer import AnalysisResult

console = Console()


def _bar(score: float, width: int = 10) -> str:
    """Render a compact unicode bar for a 0–100 score."""
    filled = round(score / 100 * width)
    return "█" * filled + "░" * (width - filled)


def render_compare(a: "AnalysisResult", b: "AnalysisResult") -> None:
    """Render a side-by-side comparison of two repository analyses.

    Shows per-signal scores for both repos, highlights the winner of each
    signal, and prints an overall recommendation.

    Args:
        a: First AnalysisResult.
        b: Second AnalysisResult.
    """
    from core.scorer import get_score_color, get_score_label
    from core.verdict import get_verdict_emoji, get_verdict_color

    # ── Header panels ──────────────────────────────────────────────────────
    def _header(r: "AnalysisResult") -> Text:
        sc = get_score_color(r.score)
        vc = get_verdict_color(r.verdict)
        ve = get_verdict_emoji(r.verdict)
        t = Text()
        t.append(f"{ve} {r.owner}/{r.repo}\n", style="bold white")
        t.append(f"Score: ", style="dim")
        t.append(f"{r.score:.1f}/100", style=f"bold {sc}")
        t.append(f"  {get_score_label(r.score)}\n", style=sc)
        t.append(f"Verdict: ", style="dim")
        t.append(r.verdict.upper(), style=f"bold {vc}")
        return t

    col_a_color = get_verdict_color(a.verdict)
    col_b_color = get_verdict_color(b.verdict)

    # Side-by-side header
    from rich.columns import Columns
    console.print()
    console.print(
        Columns([
            Panel(_header(a), border_style=col_a_color, expand=True),
            Panel(_header(b), border_style=col_b_color, expand=True),
        ])
    )

    # ── Signal comparison table ────────────────────────────────────────────
    sigs_a = {s.name: s for s in a.signals}
    sigs_b = {s.name: s for s in b.signals}
    all_names = list(dict.fromkeys(list(sigs_a.keys()) + list(sigs_b.keys())))

    table = Table(
        title="[bold]Signal Comparison[/bold]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        expand=True,
    )
    table.add_column("Signal", min_width=22)
    table.add_column(f"{a.owner}/{a.repo}", justify="center", min_width=20)
    table.add_column("", justify="center", min_width=4)   # winner arrow
    table.add_column(f"{b.owner}/{b.repo}", justify="center", min_width=20)

    VCOL = {"good": "green", "warning": "yellow", "bad": "red"}

    a_wins = 0
    b_wins = 0

    for name in all_names:
        sa = sigs_a.get(name)
        sb = sigs_b.get(name)

        def _cell(s) -> str:
            if s is None:
                return "[dim]N/A[/dim]"
            c = VCOL.get(s.verdict, "white")
            bar = _bar(s.score * 100, 8)
            return f"[{c}]{bar}[/{c}] [{c}]{s.score * 100:.0f}[/{c}]"

        score_a = sa.score if sa else -1
        score_b = sb.score if sb else -1

        if score_a > score_b + 0.01:
            arrow = "[green]◀[/green]"
            a_wins += 1
        elif score_b > score_a + 0.01:
            arrow = "[green]▶[/green]"
            b_wins += 1
        else:
            arrow = "[dim]=[/dim]"

        label = (sa or sb).label if (sa or sb) else name
        table.add_row(label, _cell(sa), arrow, _cell(sb))

    console.print(table)

    # ── Score bar comparison ───────────────────────────────────────────────
    bar_table = Table(box=box.SIMPLE, show_header=False, expand=True)
    bar_table.add_column("Repo", style="bold", min_width=28)
    bar_table.add_column("Bar", min_width=40)
    bar_table.add_column("Score", justify="right", min_width=10)

    for r in [a, b]:
        sc = get_score_color(r.score)
        bar = _bar(r.score, 30)
        bar_table.add_row(
            f"{r.owner}/{r.repo}",
            f"[{sc}]{bar}[/{sc}]",
            f"[{sc}]{r.score:.1f}/100[/{sc}]",
        )

    console.print(bar_table)

    # ── Verdict ────────────────────────────────────────────────────────────
    console.print()
    if abs(a.score - b.score) < 2.0:
        console.print(
            "[yellow]⚖️  Too close to call[/yellow] — both repos have similar health scores."
        )
        console.print(
            f"[dim]  {a.owner}/{a.repo}: {a_wins} signal wins  •  "
            f"{b.owner}/{b.repo}: {b_wins} signal wins[/dim]"
        )
    else:
        winner = a if a.score > b.score else b
        loser  = b if a.score > b.score else a
        margin = abs(a.score - b.score)
        wc = get_score_color(winner.score)
        console.print(
            f"[bold {wc}]🏆  {winner.owner}/{winner.repo}[/bold {wc}] "
            f"wins by {margin:.1f} points"
        )
        console.print(
            f"[dim]  Signal wins: {a.owner}/{a.repo} {a_wins}  •  "
            f"{b.owner}/{b.repo} {b_wins}[/dim]"
        )
        _print_recommendation(winner, loser)

    console.print()


def _print_recommendation(winner: "AnalysisResult", loser: "AnalysisResult") -> None:
    """Print a one-line recommendation based on the comparison result."""
    from core.verdict import get_verdict_emoji

    ve_w = get_verdict_emoji(winner.verdict)
    ve_l = get_verdict_emoji(loser.verdict)

    if loser.verdict == "dead":
        msg = (
            f"  {ve_l} [red]{loser.owner}/{loser.repo}[/red] appears unmaintained. "
            f"Use [green]{winner.owner}/{winner.repo}[/green] instead."
        )
    elif loser.verdict == "uncertain":
        msg = (
            f"  {ve_w} [green]{winner.owner}/{winner.repo}[/green] is more actively maintained. "
            f"{ve_l} [yellow]{loser.owner}/{loser.repo}[/yellow] shows signs of slowing down."
        )
    else:
        msg = (
            f"  {ve_w} Both repos are maintained, but "
            f"[green]{winner.owner}/{winner.repo}[/green] has stronger health signals."
        )
    console.print(msg)