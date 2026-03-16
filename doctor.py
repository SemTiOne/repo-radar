"""
doctor.py — System health check command for RepoRadar.

Runs a series of checks on environment, connectivity, config, and resources.
Outputs a rich-formatted report with severity indicators.
"""

import os
import platform
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import psutil
from rich.console import Console
from rich.table import Table
from rich import box


console = Console()


def validate_token_format(token: str) -> bool:
    """Check if a GitHub token has a recognized prefix format.

    Args:
        token: Raw token string.

    Returns:
        True if the token starts with a known GitHub token prefix.
    """
    return token.startswith(("ghp_", "gho_", "github_pat_"))


def get_system_stats() -> Dict[str, float]:
    """Retrieve current system resource statistics via psutil.

    Returns:
        Dict with keys: memory_mb (float), cpu_percent (float), disk_free_mb (float).
    """
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(str(Path.home()))
    cpu = psutil.cpu_percent(interval=0.5)
    return {
        "memory_mb": mem.used / (1024 * 1024),
        "cpu_percent": cpu,
        "disk_free_mb": disk.free / (1024 * 1024),
    }


def _check(label: str, condition: bool, severity: str, detail: str, fix: Optional[str] = None) -> dict:
    return {
        "label": label,
        "passed": condition,
        "severity": severity,
        "detail": detail,
        "fix": fix,
    }


def _run_checks(config: dict) -> List[dict]:
    checks: List[dict] = []

    # GitHub API reachable
    try:
        import requests
        resp = requests.get("https://api.github.com/rate_limit", timeout=5)
        checks.append(_check(
            "GitHub API reachable",
            resp.status_code == 200,
            "critical",
            f"GET /rate_limit → HTTP {resp.status_code}",
            "Check your internet connection or GitHub status at https://githubstatus.com"
        ))
    except Exception as exc:
        checks.append(_check(
            "GitHub API reachable", False, "critical",
            f"Connection error: {exc}",
            "Check your internet connection."
        ))

    # Network connectivity
    try:
        import requests
        resp = requests.get("https://api.github.com", timeout=5)
        checks.append(_check(
            "Network connectivity", True, "critical",
            "Can reach api.github.com"
        ))
    except Exception as exc:
        checks.append(_check(
            "Network connectivity", False, "critical",
            f"Cannot reach api.github.com: {exc}",
            "Check firewall or proxy settings."
        ))

    # Dependencies installed
    missing = []
    for pkg in ["requests", "rich", "dotenv", "pytz", "psutil", "fastapi", "uvicorn"]:
        try:
            __import__(pkg if pkg != "dotenv" else "dotenv")
        except ImportError:
            missing.append(pkg)
    checks.append(_check(
        "All dependencies installed",
        len(missing) == 0,
        "critical",
        "All packages present" if not missing else f"Missing: {', '.join(missing)}",
        f"Run: pip install {' '.join(missing)}" if missing else None
    ))

    # GitHub token present
    token = config.get("GITHUB_TOKEN") or ""
    checks.append(_check(
        "GitHub token present",
        bool(token),
        "warning",
        "GITHUB_TOKEN is set" if token else "GITHUB_TOKEN not set (rate limit: 60 req/hour)",
        "Set GITHUB_TOKEN in your .env file or environment."
    ))

    # GitHub token valid format
    if token:
        valid_fmt = validate_token_format(token)
        checks.append(_check(
            "GitHub token valid format",
            valid_fmt,
            "warning",
            "Token format looks valid" if valid_fmt else "Token format unusual (expected ghp_... or github_pat_...)",
            "Regenerate your token at https://github.com/settings/tokens"
        ))

    # GitHub rate limit
    if token:
        try:
            import requests as req
            headers = {"Authorization": f"token {token}"}
            r = req.get("https://api.github.com/rate_limit", headers=headers, timeout=5)
            if r.status_code == 200:
                remaining = r.json().get("resources", {}).get("core", {}).get("remaining", 0)
                checks.append(_check(
                    "GitHub rate limit",
                    remaining > 50,
                    "warning",
                    f"Remaining calls: {remaining}",
                    "Wait for the rate limit to reset or use a different token."
                ))
        except Exception:
            pass

    # Cache directory
    cache_dir = Path(config.get("CACHE_DIR", Path.home() / ".reporadar" / "cache")).expanduser()
    cache_ok = cache_dir.exists() or True  # will be created on first use
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_exists = True
    except Exception:
        cache_exists = False
    checks.append(_check(
        "Cache directory exists",
        cache_exists,
        "warning",
        str(cache_dir),
        f"Run: mkdir -p {cache_dir}"
    ))

    # Cache size
    if cache_dir.exists():
        total_bytes = sum(f.stat().st_size for f in cache_dir.rglob("*") if f.is_file())
        total_mb = total_bytes / (1024 * 1024)
        checks.append(_check(
            "Cache size",
            total_mb < 500,
            "warning",
            f"{total_mb:.1f} MB used",
            "Run: reporadar cache clear"
        ))

    # History file
    history_path = Path(config.get("HISTORY_PATH", Path.home() / ".reporadar" / "history.json")).expanduser()
    try:
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history_exists = True
    except Exception:
        history_exists = False
    checks.append(_check(
        "History file exists",
        history_exists,
        "warning",
        str(history_path),
        f"Run: mkdir -p {history_path.parent}"
    ))

    # History file permissions (Unix/macOS only)
    if platform.system() in ("Linux", "Darwin") and history_path.exists():
        mode = oct(history_path.stat().st_mode)[-3:]
        checks.append(_check(
            "History file permissions",
            mode == "600",
            "warning",
            f"Permissions: {mode}",
            f"Run: chmod 600 {history_path}"
        ))

    # .env file permissions (Unix/macOS only)
    env_path = Path('.env')
    if platform.system() in ('Linux', 'Darwin') and env_path.exists():
        env_mode = oct(env_path.stat().st_mode)[-3:]
        checks.append(_check(
            '.env file permissions',
            env_mode == '600',
            'warning',
            f'Permissions: {env_mode}',
            'Run: chmod 600 .env  (prevents other users reading your token)'
        ))

    # History file size
    if history_path.exists():
        size_mb = history_path.stat().st_size / (1024 * 1024)
        checks.append(_check(
            "History file size",
            size_mb < 10,
            "warning",
            f"{size_mb:.2f} MB",
            "Run: reporadar history --clear"
        ))

    # License key format
    license_key = config.get("LICENSE_KEY", "")
    if license_key:
        from validator import validate_license_key_format
        valid, reason = validate_license_key_format(license_key)
        checks.append(_check(
            "License key format",
            valid,
            "warning",
            "Valid format" if valid else reason,
            "Check your license key at reporadar.dev"
        ))

    # Tier detected
    from subscription.license import get_tier
    tier = get_tier(license_key)
    checks.append(_check(
        "Tier detected",
        True,
        "info",
        f"Current tier: {tier.upper()}"
    ))

    # Python version
    version_ok = sys.version_info >= (3, 9)
    checks.append(_check(
        "Python version",
        version_ok,
        "warning",
        f"Python {sys.version.split()[0]}",
        "Upgrade to Python 3.9 or newer."
    ))

    # Memory usage
    stats = get_system_stats()
    checks.append(_check(
        "Memory usage",
        stats["memory_mb"] < 400,
        "warning",
        f"{stats['memory_mb']:.0f} MB used"
    ))

    # Disk space
    checks.append(_check(
        "Disk space",
        stats["disk_free_mb"] > 200,
        "warning",
        f"{stats['disk_free_mb']:.0f} MB free",
        "Free up disk space."
    ))

    # History entry count
    try:
        from history.audit_log import load_history
        history = load_history()
        entry_count = len(history.get("entries", []))
    except Exception:
        entry_count = 0
    checks.append(_check(
        "Total history entries",
        True,
        "info",
        f"{entry_count} entries stored"
    ))

    return checks


def run_doctor(config: dict) -> None:
    """Run all system health checks and print a rich-formatted report.

    Args:
        config: Application configuration dict from load_config().
    """
    checks = _run_checks(config)

    has_critical_fail = any(not c["passed"] and c["severity"] == "critical" for c in checks)
    has_warning_fail = any(not c["passed"] and c["severity"] == "warning" for c in checks)

    if has_critical_fail:
        header_style = "bold red"
        header_icon = "❌"
        header_text = "RepoRadar Doctor"
    elif has_warning_fail:
        header_style = "bold yellow"
        header_icon = "⚠️"
        header_text = "RepoRadar Doctor"
    else:
        header_style = "bold green"
        header_icon = "✅"
        header_text = "RepoRadar Doctor"

    console.print(f"\n[{header_style}]{header_icon}  {header_text}[/{header_style}]\n")

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Check", style="bold", min_width=30)
    table.add_column("Status", justify="center", min_width=8)
    table.add_column("Detail", min_width=40)

    SEV_ICON = {"critical": "🔴", "warning": "🟡", "info": "ℹ️"}

    for c in checks:
        icon = SEV_ICON.get(c["severity"], "")
        if c["passed"]:
            status = "✅ Pass"
            status_style = "green"
        else:
            status = f"{icon} Fail"
            status_style = "red" if c["severity"] == "critical" else "yellow"

        detail = c["detail"]
        if not c["passed"] and c.get("fix"):
            detail += f"\n  [dim]Fix: {c['fix']}[/dim]"

        table.add_row(
            f"[bold]{c['label']}[/bold]",
            f"[{status_style}]{status}[/{status_style}]",
            detail,
        )

    console.print(table)

    failed = [c for c in checks if not c["passed"]]
    if failed:
        console.print(f"\n[dim]{len(failed)} check(s) failed. See fix suggestions above.[/dim]")
    else:
        console.print("\n[green]All checks passed! RepoRadar is healthy.[/green]")
    console.print()