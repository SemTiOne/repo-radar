"""
core/signals/base.py — Base classes for all RepoRadar health signals.

All signals extend BaseSignal and return a SignalResult.
Signals must never raise exceptions — return a bad score with error detail on failure.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SignalResult:
    """Holds the result of a single signal analysis."""

    name: str
    label: str
    score: float        # 0.0 to 1.0
    weight: float
    value: str
    verdict: str        # "good", "warning", or "bad"
    detail: str
    is_free_tier: bool


class BaseSignal(ABC):
    """Abstract base class for all health signals."""

    @abstractmethod
    def analyze(self, repo_data: dict) -> SignalResult:
        """Analyze the provided repository data and return a SignalResult.

        Must never raise exceptions. On any error, return a SignalResult
        with score=0.0, verdict='bad', and an error description in 'detail'.

        Args:
            repo_data: Aggregated data dict from GitHubClient calls.

        Returns:
            A populated SignalResult instance.
        """
        pass