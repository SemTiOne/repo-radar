"""
core/signals — All health signal implementations for RepoRadar.

Each signal extends BaseSignal and returns a SignalResult.
Import all signals from here for use in the analyzer.
"""

from core.signals.base import BaseSignal, SignalResult
from core.signals.commit_recency import CommitRecencySignal
from core.signals.commit_frequency import CommitFrequencySignal
from core.signals.issue_response import IssueResponseSignal
from core.signals.pr_merge_rate import PRMergeRateSignal
from core.signals.release_frequency import ReleaseFrequencySignal
from core.signals.contributor_activity import ContributorActivitySignal
from core.signals.issue_ratio import IssueRatioSignal
from core.signals.archive_status import ArchiveStatusSignal

ALL_SIGNALS = [
    CommitRecencySignal,
    CommitFrequencySignal,
    IssueResponseSignal,
    PRMergeRateSignal,
    ReleaseFrequencySignal,
    ContributorActivitySignal,
    IssueRatioSignal,
    ArchiveStatusSignal,
]

SIGNAL_MAP = {cls().NAME: cls for cls in ALL_SIGNALS}  # type: ignore[call-arg]

__all__ = [
    "BaseSignal",
    "SignalResult",
    "CommitRecencySignal",
    "CommitFrequencySignal",
    "IssueResponseSignal",
    "PRMergeRateSignal",
    "ReleaseFrequencySignal",
    "ContributorActivitySignal",
    "IssueRatioSignal",
    "ArchiveStatusSignal",
    "ALL_SIGNALS",
    "SIGNAL_MAP",
]