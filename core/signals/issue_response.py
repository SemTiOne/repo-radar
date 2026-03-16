"""
core/signals/issue_response.py — Signal: how quickly do maintainers respond to issues?

Paid tier signal. Weight: 0.15.
"""

from datetime import datetime, timezone
from typing import List, Optional

from core.signals.base import BaseSignal, SignalResult


class IssueResponseSignal(BaseSignal):
    """Measures average time to first maintainer response on closed issues."""

    NAME = "issue_response"
    WEIGHT = 0.15
    IS_FREE = False

    def analyze(self, repo_data: dict) -> SignalResult:
        """Compute average days to first comment on last 20 closed issues.

        Buckets:
          < 3 days  → 1.0 (good)
          3–7       → 0.8
          7–30      → 0.5
          30–90     → 0.2
          > 90      → 0.0 (bad)

        Args:
            repo_data: Must contain 'closed_issues' list and 'issue_comments' dict.

        Returns:
            SignalResult for issue_response.
        """
        try:
            closed_issues: List[dict] = repo_data.get("closed_issues", [])
            issue_comments: dict = repo_data.get("issue_comments", {})

            if not closed_issues:
                return SignalResult(
                    name=self.NAME,
                    label="Issue Response Time",
                    score=0.5,
                    weight=self.WEIGHT,
                    value="No issues",
                    verdict="warning",
                    detail="No closed issues found to analyze.",
                    is_free_tier=self.IS_FREE,
                )

            response_days: List[float] = []

            for issue in closed_issues:
                issue_num = issue.get("number")
                created_at_str: Optional[str] = issue.get("created_at")
                if not created_at_str:
                    continue

                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                comments = issue_comments.get(str(issue_num), [])

                first_comment: Optional[datetime] = None
                for comment in comments:
                    comment_at_str = comment.get("created_at")
                    if comment_at_str:
                        comment_at = datetime.fromisoformat(comment_at_str.replace("Z", "+00:00"))
                        if first_comment is None or comment_at < first_comment:
                            first_comment = comment_at

                if first_comment:
                    days = (first_comment - created_at).total_seconds() / 86400
                    if days >= 0:
                        response_days.append(days)

            if not response_days:
                return SignalResult(
                    name=self.NAME,
                    label="Issue Response Time",
                    score=0.5,
                    weight=self.WEIGHT,
                    value="No responses",
                    verdict="warning",
                    detail="No issue responses found in analyzed issues.",
                    is_free_tier=self.IS_FREE,
                )

            avg_days = sum(response_days) / len(response_days)

            if avg_days < 3:
                score, verdict = 1.0, "good"
            elif avg_days < 7:
                score, verdict = 0.8, "good"
            elif avg_days < 30:
                score, verdict = 0.5, "warning"
            elif avg_days < 90:
                score, verdict = 0.2, "bad"
            else:
                score, verdict = 0.0, "bad"

            return SignalResult(
                name=self.NAME,
                label="Issue Response Time",
                score=score,
                weight=self.WEIGHT,
                value=f"{avg_days:.1f}d avg",
                verdict=verdict,
                detail=(
                    f"Average first response: {avg_days:.1f} days "
                    f"across {len(response_days)} issue(s)."
                ),
                is_free_tier=self.IS_FREE,
            )
        except Exception as exc:
            return SignalResult(
                name=self.NAME,
                label="Issue Response Time",
                score=0.0,
                weight=self.WEIGHT,
                value="Error",
                verdict="bad",
                detail=f"Error analyzing issue response time: {exc}",
                is_free_tier=self.IS_FREE,
            )