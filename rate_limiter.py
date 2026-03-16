"""
rate_limiter.py — GitHub API rate limit management for RepoRadar.

Wraps the GitHubClient rate limit API with helper methods for
warning, blocking, and estimating API call usage.
"""

import time
from typing import Tuple


class GitHubRateLimiter:
    """Manages GitHub API rate limit awareness and enforcement."""

    def __init__(self, client: "GitHubClient") -> None:  # noqa: F821
        """Initialize with a GitHubClient instance.

        Args:
            client: An initialized GitHubClient for fetching rate limit info.
        """
        self.client = client

    def get_status(self) -> dict:
        """Fetch current rate limit status from the GitHub API.

        Returns:
            Dict with keys: limit, remaining, reset_at (ISO timestamp), used.
        """
        data = self.client.get_rate_limit()
        core = data.get("resources", {}).get("core", {})
        reset_ts = core.get("reset", 0)
        reset_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(reset_ts))
        return {
            "limit": core.get("limit", 0),
            "remaining": core.get("remaining", 0),
            "reset_at": reset_iso,
            "used": core.get("used", 0),
        }

    def warn_if_low(self, threshold: int = 100) -> None:
        """Print a warning via rich if remaining API calls are below threshold.

        Args:
            threshold: Warn if remaining calls are below this number.
        """
        from rich.console import Console

        console = Console(stderr=True)
        status = self.get_status()
        remaining = status["remaining"]
        if remaining < threshold:
            console.print(
                f"[yellow]⚠️  GitHub API rate limit low: {remaining} calls remaining "
                f"(resets at {status['reset_at']})[/yellow]"
            )

    def wait_if_exceeded(self) -> None:
        """Block until the GitHub API rate limit resets if currently at zero.

        Prints a countdown message and sleeps until the reset time.
        """
        from rich.console import Console

        console = Console(stderr=True)
        data = self.client.get_rate_limit()
        core = data.get("resources", {}).get("core", {})
        remaining = core.get("remaining", 1)
        if remaining == 0:
            reset_ts = core.get("reset", time.time() + 60)
            wait_seconds = max(0, int(reset_ts - time.time())) + 5
            console.print(
                f"[red]GitHub API rate limit exceeded. Waiting {wait_seconds}s for reset...[/red]"
            )
            time.sleep(wait_seconds)

    def estimate_calls_needed(self, tier: str) -> int:
        """Estimate how many GitHub API calls will be used for one analysis.

        Free tier: ~3 calls (repo info + commits + issues).
        Paid tier: ~8 calls (all signals).

        Args:
            tier: "free" or "paid".

        Returns:
            Estimated number of API calls.
        """
        if tier == "paid":
            return 8
        return 3

    def can_analyze(self, tier: str) -> Tuple[bool, str]:
        """Check whether there are enough remaining API calls to run an analysis.

        Args:
            tier: "free" or "paid".

        Returns:
            (True, "") if sufficient calls remain, (False, reason) otherwise.
        """
        try:
            status = self.get_status()
            needed = self.estimate_calls_needed(tier)
            remaining = status["remaining"]
            if remaining >= needed:
                return True, ""
            return (
                False,
                f"Insufficient GitHub API calls: {remaining} remaining, {needed} needed. "
                f"Resets at {status['reset_at']}.",
            )
        except Exception as exc:
            return False, f"Could not check rate limit: {exc}"