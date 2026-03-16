"""
core/signals/release_frequency.py — Signal: how often does the repo publish releases?

Paid tier signal. Weight: 0.10.
"""

from datetime import datetime, timezone
from typing import List, Optional

from core.signals.base import BaseSignal, SignalResult


class ReleaseFrequencySignal(BaseSignal):
    """Measures how recently the repository published a GitHub release."""

    NAME = "release_frequency"
    WEIGHT = 0.10
    IS_FREE = False

    def analyze(self, repo_data: dict) -> SignalResult:
        """Score based on days since the most recent release.

        Buckets:
          < 30 days  → 1.0 (good)
          < 90       → 0.8
          < 180      → 0.5
          < 365      → 0.2
          > 365 / no releases → 0.0 (bad)

        Args:
            repo_data: Must contain 'releases' list of release objects.

        Returns:
            SignalResult for release_frequency.
        """
        try:
            releases: List[dict] = repo_data.get("releases", [])

            if not releases:
                return SignalResult(
                    name=self.NAME,
                    label="Release Frequency",
                    score=0.0,
                    weight=self.WEIGHT,
                    value="No releases",
                    verdict="bad",
                    detail="No releases published.",
                    is_free_tier=self.IS_FREE,
                )

            latest_at_str: Optional[str] = None
            for release in releases:
                published = release.get("published_at") or release.get("created_at")
                if published:
                    latest_at_str = published
                    break

            if not latest_at_str:
                return SignalResult(
                    name=self.NAME,
                    label="Release Frequency",
                    score=0.0,
                    weight=self.WEIGHT,
                    value="Unknown",
                    verdict="bad",
                    detail="Release date unavailable.",
                    is_free_tier=self.IS_FREE,
                )

            latest_dt = datetime.fromisoformat(latest_at_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            days = (now - latest_dt).days

            if days < 30:
                score, verdict = 1.0, "good"
            elif days < 90:
                score, verdict = 0.8, "good"
            elif days < 180:
                score, verdict = 0.5, "warning"
            elif days < 365:
                score, verdict = 0.2, "bad"
            else:
                score, verdict = 0.0, "bad"

            return SignalResult(
                name=self.NAME,
                label="Release Frequency",
                score=score,
                weight=self.WEIGHT,
                value=f"{days}d ago",
                verdict=verdict,
                detail=f"Latest release: {latest_at_str[:10]} ({days} day(s) ago).",
                is_free_tier=self.IS_FREE,
            )
        except Exception as exc:
            return SignalResult(
                name=self.NAME,
                label="Release Frequency",
                score=0.0,
                weight=self.WEIGHT,
                value="Error",
                verdict="bad",
                detail=f"Error analyzing release frequency: {exc}",
                is_free_tier=self.IS_FREE,
            )