"""
cli/badge.py — Badge generation for RepoRadar.

Generates shields.io-compatible badge URLs and Markdown/HTML snippets
that can be embedded in a repository README to show its health score.
"""

from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich import box

if TYPE_CHECKING:
    from core.analyzer import AnalysisResult

console = Console()

# shields.io color names mapped from score ranges
_SHIELDS_COLORS = {
    "bright_green": "brightgreen",
    "green":        "green",
    "yellow":       "yellow",
    "dark_orange":  "orange",
    "red":          "red",
}


def _shields_color(score: float) -> str:
    """Map a health score to a shields.io color name."""
    if score >= 80:
        return "brightgreen"
    if score >= 60:
        return "green"
    if score >= 40:
        return "yellow"
    if score >= 20:
        return "orange"
    return "red"


def _encode(s: str) -> str:
    """URL-encode a string for shields.io label/message fields."""
    return s.replace("-", "--").replace("_", "__").replace(" ", "%20")


def generate_badge_url(result: "AnalysisResult") -> str:
    """Generate a shields.io badge URL for the given analysis result.

    Format: https://img.shields.io/badge/<label>-<score>%20%2F%20100-<color>

    Args:
        result: Completed AnalysisResult.

    Returns:
        Full shields.io badge URL string.
    """
    from core.scorer import get_score_label
    label = _encode("RepoRadar")
    score_label = get_score_label(result.score)
    message = _encode(f"{result.score:.0f}/100 {score_label}")
    color = _shields_color(result.score)
    return f"https://img.shields.io/badge/{label}-{message}-{color}"


def generate_badge_variants(result: "AnalysisResult") -> dict:
    """Generate multiple badge format variants for a result.

    Returns a dict with keys: url, markdown, html, rst, link_url.

    Args:
        result: Completed AnalysisResult.

    Returns:
        Dict of badge format strings.
    """
    url = generate_badge_url(result)
    repo_url = result.url
    alt = f"RepoRadar score for {result.owner}/{result.repo}"

    return {
        "url": url,
        "markdown": f"[![{alt}]({url})]({repo_url})",
        "html": f'<a href="{repo_url}"><img src="{url}" alt="{alt}"></a>',
        "rst": f".. image:: {url}\n   :target: {repo_url}\n   :alt: {alt}",
        "link_url": repo_url,
    }


def render_badge(result: "AnalysisResult") -> None:
    """Render all badge variants to the terminal with copy-ready snippets.

    Args:
        result: Completed AnalysisResult.
    """
    from core.scorer import get_score_label, get_score_color

    variants = generate_badge_variants(result)
    score_color = get_score_color(result.score)
    score_label = get_score_label(result.score)

    console.print()
    console.print(
        f"[bold]Badge for[/bold] [cyan]{result.owner}/{result.repo}[/cyan]  "
        f"[{score_color}]{result.score:.0f}/100 — {score_label}[/{score_color}]"
    )
    console.print()

    # Badge URL
    console.print("[bold dim]Badge URL:[/bold dim]")
    console.print(f"  [link={variants['url']}]{variants['url']}[/link]")
    console.print()

    # Markdown
    console.print("[bold dim]Markdown (paste into README.md):[/bold dim]")
    console.print(
        Syntax(variants["markdown"], "markdown", theme="monokai", word_wrap=True)
    )
    console.print()

    # HTML
    console.print("[bold dim]HTML:[/bold dim]")
    console.print(
        Syntax(variants["html"], "html", theme="monokai", word_wrap=True)
    )
    console.print()

    # RST
    console.print("[bold dim]reStructuredText (.rst):[/bold dim]")
    console.print(
        Syntax(variants["rst"], "rst", theme="monokai", word_wrap=True)
    )
    console.print()

    # Preview hint
    console.print(
        f"[dim]Preview badge: {variants['url']}[/dim]"
    )
    console.print()