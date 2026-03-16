"""
core/signals/contributor_activity.py — Signal: how many contributors are recently active?

Paid tier signal. Weight: 0.10.
"""

from datetime import datetime, timezone, timedelta
from typing import List

from core.signals.base import BaseSignal, SignalResult


class ContributorActivitySignal(BaseSignal):
    """Counts unique contributors active in the last 90 days."""

    NAME = "contributor_activity"
    WEIGHT = 0.10
    IS_FREE = False

    def analyze(self, repo_data: dict) -> SignalResult:
        """Score based on number of active contributors in the last 90 days.

        Buckets:
          >= 5 contributors → 1.0 (good)
          3–4               → 0.8
          2                 → 0.5
          1                 → 0.3
          0                 → 0.0 (bad)

        Args:
            repo_data: Must contain 'contributors' list of contributor objects
                       with 'login' and optionally commit 'weeks' data.

        Returns:
            SignalResult for contributor_activity.
        """
        try:
            contributors: List[dict] = repo_data.get("contributors", [])

            if not contributors:
                return SignalResult(
                    name=self.NAME,
                    label="Contributor Activity",
                    score=0.0,
                    weight=self.WEIGHT,
                    value="0 contributors",
                    verdict="bad",
                    detail="No contributor data available.",
                    is_free_tier=self.IS_FREE,
                )

            cutoff = datetime.now(timezone.utc) - timedelta(days=90)
            cutoff_ts = int(cutoff.timestamp())

            active_count = 0
            for contributor in contributors:
                weeks: List[dict] = contributor.get("weeks", [])
                for week in weeks:
                    w_ts = week.get("w", 0)
                    commits = week.get("c", 0)
                    if w_ts >= cutoff_ts and commits > 0:
                        active_count += 1
                        break
                else:
                    # Fallback: if no weeks data, count as active if they have recent commits
                    if not weeks and contributor.get("contributions", 0) > 0:
                        active_count += 1

            if active_count >= 5:
                score, verdict = 1.0, "good"
            elif active_count >= 3:
                score, verdict = 0.8, "good"
            elif active_count == 2:
                score, verdict = 0.5, "warning"
            elif active_count == 1:
                score, verdict = 0.3, "warning"
            else:
                score, verdict = 0.0, "bad"

            return SignalResult(
                name=self.NAME,
                label="Contributor Activity",
                score=score,
                weight=self.WEIGHT,
                value=f"{active_count} active",
                verdict=verdict,
                detail=f"{active_count} contributor(s) active in the last 90 days.",
                is_free_tier=self.IS_FREE,
            )
        except Exception as exc:
            return SignalResult(
                name=self.NAME,
                label="Contributor Activity",
                score=0.0,
                weight=self.WEIGHT,
                value="Error",
                verdict="bad",
                detail=f"Error analyzing contributor activity: {exc}",
                is_free_tier=self.IS_FREE,
            )