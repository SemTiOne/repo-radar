"""
cli/main.py — CLI entry point for RepoRadar.

Routes all subcommands: check, bulk, history, doctor, cache.
Use: python -m cli.main <command> [options]
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.prompt import Confirm

console = Console()

_VERSION = "0.1.0"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reporadar",
        description="RepoRadar — GitHub repository health analyzer.",
    )
    parser.add_argument(
        "--version", action="store_true", help="Show version and exit."
    )
    parser.add_argument(
        "--changelog", action="store_true", help="Show changelog and exit."
    )

    subparsers = parser.add_subparsers(dest="command")

    # check
    check_p = subparsers.add_parser("check", help="Analyze a single repository.")
    check_p.add_argument("repo", help="Repository (user/repo, github.com/user/repo, or full URL).")
    check_p.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format (default: text).",
    )
    check_p.add_argument(
        "--no-cache", action="store_true", help="Skip cache and force fresh analysis."
    )
    check_p.add_argument(
        "--watch", action="store_true",
        help="Re-check continuously at a fixed interval.",
    )
    check_p.add_argument(
        "--interval", type=int, default=300, metavar="SECONDS",
        help="Seconds between re-checks in watch mode (default: 300).",
    )
    check_p.add_argument(
        "--badge", action="store_true",
        help="Generate README badge snippets after analysis.",
    )

    # compare
    compare_p = subparsers.add_parser("compare", help="Compare two repositories side by side.")
    compare_p.add_argument("repo_a", help="First repository.")
    compare_p.add_argument("repo_b", help="Second repository.")
    compare_p.add_argument(
        "--no-cache", action="store_true", help="Skip cache and force fresh analysis."
    )

    # bulk
    bulk_p = subparsers.add_parser("bulk", help="Check multiple repositories (paid).")
    bulk_input = bulk_p.add_mutually_exclusive_group(required=True)
    bulk_input.add_argument("file", nargs="?", help="Text file with one repo per line.")
    bulk_input.add_argument(
        "--from-package-json", metavar="PATH", help="Extract repos from package.json."
    )
    bulk_input.add_argument(
        "--from-requirements", metavar="PATH", help="Extract repos from requirements.txt."
    )
    bulk_p.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format.",
    )

    # history
    history_p = subparsers.add_parser("history", help="View analysis history (paid).")
    history_p.add_argument("--repo", help="Filter history for a specific repo.")
    history_p.add_argument("--clear", action="store_true", help="Clear all history.")
    history_p.add_argument(
        "--stats", action="store_true", help="Show history statistics."
    )
    history_p.add_argument(
        "--trend", metavar="REPO", help="Show score trend for a repo."
    )

    # doctor
    subparsers.add_parser("doctor", help="Run system health checks.")

    # cache
    cache_p = subparsers.add_parser("cache", help="Manage local analysis cache.")
    cache_sub = cache_p.add_subparsers(dest="cache_command")
    cache_sub.add_parser("clear", help="Delete all cached results.")
    cache_sub.add_parser("stats", help="Show cache statistics.")

    return parser


def _get_config_and_tier():
    """Load config and resolve the subscription tier."""
    from config import load_config
    from subscription.license import get_tier

    config = load_config()
    tier = get_tier(config.get("LICENSE_KEY", ""))
    return config, tier


def _make_cache(config: dict, no_cache: bool = False):
    """Construct a FileCache instance, or None if caching is disabled."""
    if no_cache:
        return None
    from cache.file_cache import FileCache
    return FileCache(
        cache_dir=config["CACHE_DIR"],
        ttl_seconds=int(config["CACHE_TTL_SECONDS"]),
    )


def _make_client(config: dict):
    """Construct a GitHubClient from config."""
    from core.github_client import GitHubClient
    from security import mask_token

    token = config.get("GITHUB_TOKEN")
    if token:
        console.print(f"[dim]Using GitHub token: {mask_token(token)}[/dim]")
    return GitHubClient(token=token)


def cmd_check(args: argparse.Namespace) -> int:
    """Handle the 'check' subcommand."""
    from core.github_client import InvalidRepoURLError, RepoNotFoundError, RateLimitExceededError
    from core.analyzer import RepoAnalyzer
    from cli.output import render_result, render_json, render_markdown, render_upgrade_prompt
    from validator import validate_repo_url, sanitize_repo_url
    from subscription.tiers import enforce_tier

    config, tier = _get_config_and_tier()

    # Validate format access
    if args.format == "json":
        ok, msg = enforce_tier(tier, "json_export")
        if not ok:
            render_upgrade_prompt("json_export", msg)
            return 1
    if args.format == "markdown":
        ok, msg = enforce_tier(tier, "markdown_export")
        if not ok:
            render_upgrade_prompt("markdown_export", msg)
            return 1

    raw_url = sanitize_repo_url(args.repo)
    valid, reason = validate_repo_url(raw_url)
    if not valid:
        console.print(f"[red]Error:[/red] {reason}")
        return 1

    client = _make_client(config)

    try:
        owner, repo_name = client.parse_repo_url(raw_url)
    except InvalidRepoURLError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        return 1

    cache = _make_cache(config, no_cache=args.no_cache)
    analyzer = RepoAnalyzer(client=client, tier=tier, cache=cache)

    try:
        with console.status(f"[bold cyan]Analyzing {owner}/{repo_name}…[/bold cyan]"):
            result = analyzer.analyze(owner, repo_name)
    except RepoNotFoundError:
        console.print(f"[red]Repository not found:[/red] {owner}/{repo_name}")
        return 1
    except RateLimitExceededError as exc:
        console.print(f"[red]Rate limit exceeded:[/red] {exc}")
        return 1
    except Exception as exc:
        console.print(f"[red]Analysis failed:[/red] {exc}")
        return 1

    if args.format == "json":
        render_json(result)
    elif args.format == "markdown":
        md = render_markdown(result)
        console.print(md)
    else:
        render_result(result, tier)

    # --badge
    if getattr(args, "badge", False):
        from cli.badge import render_badge
        render_badge(result)

    # --watch: hand off to watch mode after first render
    if getattr(args, "watch", False):
        from cli.watch import run_watch
        interval = max(30, getattr(args, "interval", 300))
        return run_watch(owner, repo_name, interval, analyzer, tier)

    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    """Handle the compare subcommand — side-by-side diff of two repos."""
    from core.github_client import InvalidRepoURLError, RepoNotFoundError, RateLimitExceededError
    from core.analyzer import RepoAnalyzer
    from cli.compare import render_compare
    from validator import validate_repo_url, sanitize_repo_url

    config, tier = _get_config_and_tier()
    client = _make_client(config)
    cache = _make_cache(config, no_cache=getattr(args, "no_cache", False))
    analyzer = RepoAnalyzer(client=client, tier=tier, cache=cache)

    results = []
    for raw in [args.repo_a, args.repo_b]:
        raw = sanitize_repo_url(raw)
        valid, reason = validate_repo_url(raw)
        if not valid:
            console.print(f"[red]Error:[/red] {reason}")
            return 1
        try:
            owner, repo_name = client.parse_repo_url(raw)
        except InvalidRepoURLError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            return 1
        try:
            with console.status(f"[bold cyan]Analyzing {owner}/{repo_name}…[/bold cyan]"):
                result = analyzer.analyze(owner, repo_name)
            results.append(result)
        except RepoNotFoundError:
            console.print(f"[red]Repository not found:[/red] {owner}/{repo_name}")
            return 1
        except RateLimitExceededError as exc:
            console.print(f"[red]Rate limit exceeded:[/red] {exc}")
            return 1
        except Exception as exc:
            console.print(f"[red]Analysis failed:[/red] {exc}")
            return 1

    render_compare(results[0], results[1])
    return 0


def cmd_bulk(args: argparse.Namespace) -> int:
    """Handle the 'bulk' subcommand."""
    from cli.bulk import load_repos_from_file, load_repos_from_package_json, load_repos_from_requirements
    from cli.output import render_bulk_results, render_upgrade_prompt
    from core.analyzer import RepoAnalyzer
    from core.github_client import InvalidRepoURLError, RepoNotFoundError
    from subscription.tiers import enforce_tier
    from validator import validate_bulk_count

    config, tier = _get_config_and_tier()

    ok, msg = enforce_tier(tier, "bulk_check")
    if not ok:
        render_upgrade_prompt("bulk_check", msg)
        return 1

    # Load repos
    try:
        if args.from_package_json:
            repos = load_repos_from_package_json(args.from_package_json)
        elif args.from_requirements:
            repos = load_repos_from_requirements(args.from_requirements)
        elif args.file:
            repos = load_repos_from_file(args.file)
        else:
            console.print("[red]Error:[/red] No input source specified.")
            return 1
    except Exception as exc:
        console.print(f"[red]Failed to load repos:[/red] {exc}")
        return 1

    valid_count, count_msg = validate_bulk_count(len(repos), tier)
    if not valid_count:
        console.print(f"[red]Error:[/red] {count_msg}")
        return 1

    console.print(f"[cyan]Checking {len(repos)} repositories…[/cyan]")

    client = _make_client(config)
    cache = _make_cache(config)
    analyzer = RepoAnalyzer(client=client, tier=tier, cache=cache)

    results = []
    for repo_url in repos:
        try:
            owner, repo_name = client.parse_repo_url(repo_url)
            with console.status(f"[dim]Analyzing {owner}/{repo_name}…[/dim]"):
                result = analyzer.analyze(owner, repo_name)
            results.append(result)
        except RepoNotFoundError:
            console.print(f"[yellow]Skipping {repo_url} — not found.[/yellow]")
        except Exception as exc:
            console.print(f"[yellow]Skipping {repo_url} — {exc}[/yellow]")

    if results:
        render_bulk_results(results)
    else:
        console.print("[dim]No results to display.[/dim]")

    return 0


def cmd_history(args: argparse.Namespace) -> int:
    """Handle the 'history' subcommand."""
    from cli.output import render_history, render_history_stats, render_trend, render_upgrade_prompt
    from history.audit_log import get_history, clear_history, get_history_stats, get_trend
    from subscription.tiers import enforce_tier

    config, tier = _get_config_and_tier()

    ok, msg = enforce_tier(tier, "history")
    if not ok:
        render_upgrade_prompt("history", msg)
        return 1

    if args.clear:
        if Confirm.ask("[yellow]Clear all history?[/yellow]"):
            count = clear_history()
            console.print(f"[green]Cleared {count} history entries.[/green]")
        return 0

    if args.stats:
        stats = get_history_stats()
        render_history_stats(stats)
        return 0

    if args.trend:
        trend = get_trend(args.trend)
        if trend is None:
            console.print(f"[yellow]Not enough history for trend analysis of '{args.trend}' (need 2+ entries).[/yellow]")
        else:
            ok2, msg2 = enforce_tier(tier, "trend_analysis")
            if not ok2:
                render_upgrade_prompt("trend_analysis", msg2)
                return 1
            render_trend(trend, args.trend)
        return 0

    entries = get_history(repo=args.repo, limit=20)
    render_history(entries)
    return 0


def cmd_cache(args: argparse.Namespace) -> int:
    """Handle the 'cache' subcommand."""
    from cache.file_cache import FileCache
    from rich.table import Table
    from rich import box as rbox

    config, _ = _get_config_and_tier()
    fc = FileCache(cache_dir=config["CACHE_DIR"], ttl_seconds=int(config["CACHE_TTL_SECONDS"]))

    if args.cache_command == "clear":
        count = fc.clear_all()
        console.print(f"[green]Cache cleared: {count} entries deleted.[/green]")
    elif args.cache_command == "stats":
        stats = fc.get_stats()
        table = Table(box=rbox.SIMPLE, show_header=False)
        table.add_column("Key", style="bold cyan")
        table.add_column("Value")
        table.add_row("Total entries", str(stats["total_entries"]))
        table.add_row("Total size", f"{stats['total_size_bytes'] / 1024:.1f} KB")
        table.add_row(
            "Oldest entry age",
            f"{stats['oldest_entry_age_seconds'] / 3600:.1f}h" if stats["oldest_entry_age_seconds"] else "—",
        )
        table.add_row("Cache directory", stats["cache_dir"])
        console.print(table)
    else:
        console.print("[yellow]Usage: reporadar cache [clear|stats][/yellow]")

    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Handle the 'doctor' subcommand."""
    from doctor import run_doctor
    config, _ = _get_config_and_tier()
    run_doctor(config)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entry point.

    Args:
        argv: Argument list (defaults to sys.argv).

    Returns:
        Exit code (0 = success, 1 = error).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.version:
        console.print(f"[bold]RepoRadar[/bold] v{_VERSION}")
        return 0

    if args.changelog:
        changelog_path = Path(__file__).parent.parent / "CHANGELOG.md"
        if changelog_path.exists():
            console.print(changelog_path.read_text())
        else:
            console.print("[dim]CHANGELOG.md not found.[/dim]")
        return 0

    if args.command == "check":
        return cmd_check(args)
    elif args.command == "compare":
        return cmd_compare(args)
    elif args.command == "bulk":
        return cmd_bulk(args)
    elif args.command == "history":
        return cmd_history(args)
    elif args.command == "cache":
        return cmd_cache(args)
    elif args.command == "doctor":
        return cmd_doctor(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())