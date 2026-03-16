"""
core/signals/pr_merge_rate.py — Signal: what percentage of PRs are merged?

Paid tier signal. Weight: 0.15.
"""

from typing import List

from core.signals.base import BaseSignal, SignalResult


class PRMergeRateSignal(BaseSignal):
    """Measures the merge rate of recently closed pull requests."""

    NAME = "pr_merge_rate"
    WEIGHT = 0.15
    IS_FREE = False

    def analyze(self, repo_data: dict) -> SignalResult:
        """Score based on % of last 20 closed PRs that were merged.

        Buckets:
          >= 60% → 1.0 (good)
          40–60% → 0.7
          20–40% → 0.4
          < 20%  → 0.1 (bad)
          No PRs → 0.5 (neutral)

        Args:
            repo_data: Must contain 'closed_prs' list of PR objects.

        Returns:
            SignalResult for pr_merge_rate.
        """
        try:
            closed_prs: List[dict] = repo_data.get("closed_prs", [])

            if not closed_prs:
                return SignalResult(
                    name=self.NAME,
                    label="PR Merge Rate",
                    score=0.5,
                    weight=self.WEIGHT,
                    value="No PRs",
                    verdict="warning",
                    detail="No closed pull requests found.",
                    is_free_tier=self.IS_FREE,
                )

            merged = sum(1 for pr in closed_prs if pr.get("merged_at") is not None)
            total = len(closed_prs)
            rate = merged / total if total > 0 else 0.0
            pct = rate * 100

            if rate >= 0.60:
                score, verdict = 1.0, "good"
            elif rate >= 0.40:
                score, verdict = 0.7, "good"
            elif rate >= 0.20:
                score, verdict = 0.4, "warning"
            else:
                score, verdict = 0.1, "bad"

            return SignalResult(
                name=self.NAME,
                label="PR Merge Rate",
                score=score,
                weight=self.WEIGHT,
                value=f"{pct:.0f}%",
                verdict=verdict,
                detail=f"{merged}/{total} PRs merged ({pct:.0f}%).",
                is_free_tier=self.IS_FREE,
            )
        except Exception as exc:
            return SignalResult(
                name=self.NAME,
                label="PR Merge Rate",
                score=0.0,
                weight=self.WEIGHT,
                value="Error",
                verdict="bad",
                detail=f"Error analyzing PR merge rate: {exc}",
                is_free_tier=self.IS_FREE,
            )