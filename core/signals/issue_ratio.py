"""
core/signals/issue_ratio.py — Signal: what fraction of issues are open?

Free tier signal. Weight: 0.03.
"""

from core.signals.base import BaseSignal, SignalResult


class IssueRatioSignal(BaseSignal):
    """Measures the ratio of open issues to total issues."""

    NAME = "issue_ratio"
    WEIGHT = 0.03
    IS_FREE = True

    def analyze(self, repo_data: dict) -> SignalResult:
        """Score based on percentage of issues that are open.

        Buckets:
          < 20%  → 1.0 (good)
          20–40% → 0.7
          40–60% → 0.4
          60–80% → 0.2
          > 80%  → 0.0 (bad)

        Args:
            repo_data: Must contain 'repo' key with open_issues_count
                       and optionally total issue counts.

        Returns:
            SignalResult for issue_ratio.
        """
        try:
            repo = repo_data.get("repo", {})
            open_count = repo.get("open_issues_count", 0)

            # GitHub doesn't provide a direct closed count on the repo object.
            # We infer total from closed_issues + open_count if available.
            closed_issues = repo_data.get("closed_issues", [])
            closed_count = len(closed_issues) if closed_issues else 0

            total = open_count + closed_count

            if total == 0:
                return SignalResult(
                    name=self.NAME,
                    label="Issue Ratio",
                    score=1.0,
                    weight=self.WEIGHT,
                    value="No issues",
                    verdict="good",
                    detail="Repository has no issues (open or closed).",
                    is_free_tier=self.IS_FREE,
                )

            ratio = open_count / total
            pct = ratio * 100

            if ratio < 0.20:
                score, verdict = 1.0, "good"
            elif ratio < 0.40:
                score, verdict = 0.7, "good"
            elif ratio < 0.60:
                score, verdict = 0.4, "warning"
            elif ratio < 0.80:
                score, verdict = 0.2, "bad"
            else:
                score, verdict = 0.0, "bad"

            return SignalResult(
                name=self.NAME,
                label="Issue Ratio",
                score=score,
                weight=self.WEIGHT,
                value=f"{pct:.0f}% open",
                verdict=verdict,
                detail=f"{open_count} open / {total} total issues ({pct:.0f}% open).",
                is_free_tier=self.IS_FREE,
            )
        except Exception as exc:
            return SignalResult(
                name=self.NAME,
                label="Issue Ratio",
                score=0.0,
                weight=self.WEIGHT,
                value="Error",
                verdict="bad",
                detail=f"Error analyzing issue ratio: {exc}",
                is_free_tier=self.IS_FREE,
            )