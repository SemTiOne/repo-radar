"""
core/signals/commit_frequency.py — Signal: is commit frequency trending up or declining?

Paid tier signal. Weight: 0.20.
"""

from typing import List

from core.signals.base import BaseSignal, SignalResult


class CommitFrequencySignal(BaseSignal):
    """Compares recent vs historical commit frequency."""

    NAME = "commit_frequency"
    WEIGHT = 0.20
    IS_FREE = False

    def analyze(self, repo_data: dict) -> SignalResult:
        """Compare last 4 weeks vs previous 12-week average commits/week.

        Buckets (ratio = recent_avg / historical_avg):
          >= 0.8 → 1.0 (increasing/stable)
          0.5–0.8 → 0.6 (slightly declining)
          0.2–0.5 → 0.3 (significantly declining)
          < 0.2  → 0.0 (near zero)

        Args:
            repo_data: Must contain 'commit_activity' list of weekly commit counts.

        Returns:
            SignalResult for commit_frequency.
        """
        try:
            activity: List[dict] = repo_data.get("commit_activity", [])

            if not activity:
                return SignalResult(
                    name=self.NAME,
                    label="Commit Frequency",
                    score=0.3,
                    weight=self.WEIGHT,
                    value="No data",
                    verdict="warning",
                    detail="No commit activity data available.",
                    is_free_tier=self.IS_FREE,
                )

            # GitHub returns 52 weeks of data; last 4 vs prior 12
            totals = [w.get("total", 0) for w in activity]
            if len(totals) < 16:
                return SignalResult(
                    name=self.NAME,
                    label="Commit Frequency",
                    score=0.3,
                    weight=self.WEIGHT,
                    value="Insufficient data",
                    verdict="warning",
                    detail=f"Only {len(totals)} weeks of data available.",
                    is_free_tier=self.IS_FREE,
                )

            recent_4 = totals[-4:]
            prior_12 = totals[-16:-4]

            recent_avg = sum(recent_4) / 4
            historical_avg = sum(prior_12) / 12

            if historical_avg == 0:
                if recent_avg > 0:
                    ratio = 1.0
                else:
                    ratio = 0.0
            else:
                ratio = recent_avg / historical_avg

            if ratio >= 0.8:
                score, verdict, trend_label = 1.0, "good", "Stable/Increasing"
            elif ratio >= 0.5:
                score, verdict, trend_label = 0.6, "warning", "Slightly Declining"
            elif ratio >= 0.2:
                score, verdict, trend_label = 0.3, "warning", "Significantly Declining"
            else:
                score, verdict, trend_label = 0.0, "bad", "Near Zero"

            return SignalResult(
                name=self.NAME,
                label="Commit Frequency",
                score=score,
                weight=self.WEIGHT,
                value=trend_label,
                verdict=verdict,
                detail=(
                    f"Recent 4-week avg: {recent_avg:.1f} commits/week. "
                    f"Prior 12-week avg: {historical_avg:.1f} commits/week. "
                    f"Ratio: {ratio:.2f}."
                ),
                is_free_tier=self.IS_FREE,
            )
        except Exception as exc:
            return SignalResult(
                name=self.NAME,
                label="Commit Frequency",
                score=0.0,
                weight=self.WEIGHT,
                value="Error",
                verdict="bad",
                detail=f"Error analyzing commit frequency: {exc}",
                is_free_tier=self.IS_FREE,
            )