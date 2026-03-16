"""
scripts/clear_cache.py — Standalone script to clear the RepoRadar file cache.

Usage:
    python scripts/clear_cache.py

Reads CACHE_DIR from environment / .env and deletes all cached entries.
"""

import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.prompt import Confirm

from config import load_config
from cache.file_cache import FileCache

console = Console()


def main() -> int:
    """Clear all cached analysis results.

    Returns:
        Exit code (0 = success).
    """
    config = load_config()
    cache_dir = config["CACHE_DIR"]
    ttl = int(config["CACHE_TTL_SECONDS"])

    fc = FileCache(cache_dir=cache_dir, ttl_seconds=ttl)
    stats = fc.get_stats()

    if stats["total_entries"] == 0:
        console.print("[dim]Cache is already empty.[/dim]")
        return 0

    console.print(
        f"[yellow]Found {stats['total_entries']} cached entries "
        f"({stats['total_size_bytes'] / 1024:.1f} KB) in {cache_dir}[/yellow]"
    )

    if Confirm.ask("Clear all cached entries?"):
        count = fc.clear_all()
        console.print(f"[green]✅ Cleared {count} cache entries.[/green]")
    else:
        console.print("[dim]Cache clear cancelled.[/dim]")

    return 0


if __name__ == "__main__":
    sys.exit(main())