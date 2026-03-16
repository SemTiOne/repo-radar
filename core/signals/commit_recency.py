"""
core/signals/commit_recency.py — Signal: how recently was the repo last committed to?

Free tier signal. Weight: 0.25.
"""

from datetime import datetime, timezone
from typing import Optional

from core.signals.base import BaseSignal, SignalResult


class CommitRecencySignal(BaseSignal):
    """Measures how recently the repository received a commit."""

    NAME = "commit_recency"
    WEIGHT = 0.25
    IS_FREE = True

    def analyze(self, repo_data: dict) -> SignalResult:
        """Score based on days since the last commit pushed to the default branch.

        Buckets:
          < 30 days  → 1.0 (good)
          30–90      → 0.7 (warning)
          90–180     → 0.4 (warning)
          180–365    → 0.2 (bad)
          > 365      → 0.0 (bad)

        Args:
            repo_data: Must contain 'repo' key with GitHub repository object.

        Returns:
            SignalResult for commit_recency.
        """
        try:
            repo = repo_data.get("repo", {})
            pushed_at: Optional[str] = repo.get("pushed_at")

            if not pushed_at:
                return SignalResult(
                    name=self.NAME,
                    label="Last Commit",
                    score=0.0,
                    weight=self.WEIGHT,
                    value="Unknown",
                    verdict="bad",
                    detail="No push date available.",
                    is_free_tier=self.IS_FREE,
                )

            last_push = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            days = (now - last_push).days

            if days < 30:
                score, verdict, label = 1.0, "good", f"{days}d ago"
            elif days < 90:
                score, verdict, label = 0.7, "warning", f"{days}d ago"
            elif days < 180:
                score, verdict, label = 0.4, "warning", f"{days}d ago"
            elif days < 365:
                score, verdict, label = 0.2, "bad", f"{days}d ago"
            else:
                score, verdict, label = 0.0, "bad", f"{days}d ago"

            return SignalResult(
                name=self.NAME,
                label="Last Commit",
                score=score,
                weight=self.WEIGHT,
                value=label,
                verdict=verdict,
                detail=f"Last commit was {days} day(s) ago ({pushed_at[:10]}).",
                is_free_tier=self.IS_FREE,
            )
        except Exception as exc:
            return SignalResult(
                name=self.NAME,
                label="Last Commit",
                score=0.0,
                weight=self.WEIGHT,
                value="Error",
                verdict="bad",
                detail=f"Error analyzing commit recency: {exc}",
                is_free_tier=self.IS_FREE,
            )