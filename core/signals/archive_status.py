"""
core/signals/archive_status.py — Signal: is the repository archived?

Free tier signal. Weight: 0.02.
If archived, score is 0.0 and overrides the entire health score to 0.
"""

from core.signals.base import BaseSignal, SignalResult


class ArchiveStatusSignal(BaseSignal):
    """Checks whether the repository has been archived on GitHub."""

    NAME = "archive_status"
    WEIGHT = 0.02
    IS_FREE = True

    def analyze(self, repo_data: dict) -> SignalResult:
        """Return 0.0 if archived, 1.0 if active.

        Archived status overrides the entire health score to 0 in scorer.py.

        Args:
            repo_data: Must contain 'repo' key with 'archived' bool field.

        Returns:
            SignalResult for archive_status.
        """
        try:
            repo = repo_data.get("repo", {})
            archived: bool = repo.get("archived", False)

            if archived:
                return SignalResult(
                    name=self.NAME,
                    label="Archive Status",
                    score=0.0,
                    weight=self.WEIGHT,
                    value="Archived",
                    verdict="bad",
                    detail="This repository has been archived by its owner. No further development expected.",
                    is_free_tier=self.IS_FREE,
                )

            return SignalResult(
                name=self.NAME,
                label="Archive Status",
                score=1.0,
                weight=self.WEIGHT,
                value="Active",
                verdict="good",
                detail="Repository is not archived.",
                is_free_tier=self.IS_FREE,
            )
        except Exception as exc:
            return SignalResult(
                name=self.NAME,
                label="Archive Status",
                score=0.0,
                weight=self.WEIGHT,
                value="Error",
                verdict="bad",
                detail=f"Error checking archive status: {exc}",
                is_free_tier=self.IS_FREE,
            )