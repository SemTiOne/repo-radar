"""
tests/test_signals.py — Tests for all 8 health signals.
"""

from datetime import datetime, timezone, timedelta

import pytest

from core.signals.base import SignalResult
from core.signals.commit_recency import CommitRecencySignal
from core.signals.commit_frequency import CommitFrequencySignal
from core.signals.issue_response import IssueResponseSignal
from core.signals.pr_merge_rate import PRMergeRateSignal
from core.signals.release_frequency import ReleaseFrequencySignal
from core.signals.contributor_activity import ContributorActivitySignal
from core.signals.issue_ratio import IssueRatioSignal
from core.signals.archive_status import ArchiveStatusSignal


def _days_ago_iso(days: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# --- CommitRecencySignal ---

class TestCommitRecency:
    sig = CommitRecencySignal()

    def test_returns_signal_result(self):
        data = {"repo": {"pushed_at": _days_ago_iso(10)}}
        r = self.sig.analyze(data)
        assert isinstance(r, SignalResult)
        assert r.name == "commit_recency"
        assert r.weight == 0.25
        assert r.is_free_tier is True

    def test_recent_commit_score_1(self):
        data = {"repo": {"pushed_at": _days_ago_iso(5)}}
        r = self.sig.analyze(data)
        assert r.score == 1.0
        assert r.verdict == "good"

    def test_30_90_days(self):
        data = {"repo": {"pushed_at": _days_ago_iso(60)}}
        r = self.sig.analyze(data)
        assert r.score == 0.7

    def test_90_180_days(self):
        data = {"repo": {"pushed_at": _days_ago_iso(120)}}
        r = self.sig.analyze(data)
        assert r.score == 0.4

    def test_180_365_days(self):
        data = {"repo": {"pushed_at": _days_ago_iso(200)}}
        r = self.sig.analyze(data)
        assert r.score == 0.2

    def test_over_365_days(self):
        data = {"repo": {"pushed_at": _days_ago_iso(400)}}
        r = self.sig.analyze(data)
        assert r.score == 0.0
        assert r.verdict == "bad"

    def test_missing_pushed_at(self):
        r = self.sig.analyze({"repo": {}})
        assert r.score == 0.0
        assert r.verdict == "bad"

    def test_no_repo_key(self):
        r = self.sig.analyze({})
        assert r.score == 0.0


# --- CommitFrequencySignal ---

class TestCommitFrequency:
    sig = CommitFrequencySignal()

    def _make_activity(self, recent_avg: float, hist_avg: float):
        prior = [{"total": int(hist_avg)} for _ in range(12)]
        recent = [{"total": int(recent_avg)} for _ in range(4)]
        return prior + recent

    def test_returns_correct_fields(self):
        data = {"commit_activity": self._make_activity(5, 5)}
        r = self.sig.analyze(data)
        assert r.name == "commit_frequency"
        assert r.is_free_tier is False

    def test_stable_score_1(self):
        data = {"commit_activity": self._make_activity(10, 10)}
        r = self.sig.analyze(data)
        assert r.score == 1.0

    def test_slightly_declining(self):
        data = {"commit_activity": self._make_activity(6, 10)}
        r = self.sig.analyze(data)
        assert r.score == 0.6

    def test_significantly_declining(self):
        data = {"commit_activity": self._make_activity(3, 10)}
        r = self.sig.analyze(data)
        assert r.score == 0.3

    def test_near_zero(self):
        data = {"commit_activity": self._make_activity(0.1, 10)}
        r = self.sig.analyze(data)
        assert r.score == 0.0

    def test_handles_empty(self):
        r = self.sig.analyze({"commit_activity": []})
        assert r.score == 0.3  # neutral
        assert "No data" in r.value

    def test_handles_missing_key(self):
        r = self.sig.analyze({})
        assert isinstance(r, SignalResult)


# --- IssueResponseSignal ---

class TestIssueResponse:
    sig = IssueResponseSignal()

    def test_fast_response(self):
        issue = {"number": 1, "created_at": _days_ago_iso(5)}
        comment = {"created_at": _days_ago_iso(4)}
        data = {
            "closed_issues": [issue],
            "issue_comments": {"1": [comment]},
        }
        r = self.sig.analyze(data)
        assert r.score == 1.0

    def test_no_issues(self):
        r = self.sig.analyze({"closed_issues": [], "issue_comments": {}})
        assert r.score == 0.5  # neutral

    def test_missing_data(self):
        r = self.sig.analyze({})
        assert isinstance(r, SignalResult)


# --- PRMergeRateSignal ---

class TestPRMergeRate:
    sig = PRMergeRateSignal()

    def test_high_merge_rate(self):
        prs = [{"merged_at": "2024-01-01T00:00:00Z"} for _ in range(7)]
        prs += [{"merged_at": None} for _ in range(3)]
        r = self.sig.analyze({"closed_prs": prs})
        assert r.score == 1.0

    def test_no_prs_neutral(self):
        r = self.sig.analyze({"closed_prs": []})
        assert r.score == 0.5
        assert r.verdict == "warning"

    def test_low_merge_rate(self):
        prs = [{"merged_at": None} for _ in range(9)]
        prs += [{"merged_at": "2024-01-01T00:00:00Z"}]
        r = self.sig.analyze({"closed_prs": prs})
        assert r.score == 0.1

    def test_missing_key(self):
        r = self.sig.analyze({})
        assert isinstance(r, SignalResult)


# --- ReleaseFrequencySignal ---

class TestReleaseFrequency:
    sig = ReleaseFrequencySignal()

    def test_recent_release(self):
        data = {"releases": [{"published_at": _days_ago_iso(10)}]}
        r = self.sig.analyze(data)
        assert r.score == 1.0

    def test_no_releases(self):
        r = self.sig.analyze({"releases": []})
        assert r.score == 0.0
        assert r.verdict == "bad"

    def test_missing_key(self):
        r = self.sig.analyze({})
        assert isinstance(r, SignalResult)


# --- ContributorActivitySignal ---

class TestContributorActivity:
    sig = ContributorActivitySignal()

    def _make_contributors(self, count: int, active: bool = True):
        from datetime import timezone, datetime, timedelta
        cutoff_ts = int((datetime.now(timezone.utc) - timedelta(days=89)).timestamp())
        contributors = []
        for _ in range(count):
            if active:
                contributors.append({
                    "login": "user",
                    "weeks": [{"w": cutoff_ts + 100, "c": 5}],
                })
            else:
                contributors.append({
                    "login": "user",
                    "weeks": [{"w": 0, "c": 0}],
                })
        return contributors

    def test_five_or_more_contributors(self):
        data = {"contributors": self._make_contributors(5)}
        r = self.sig.analyze(data)
        assert r.score == 1.0

    def test_zero_contributors(self):
        data = {"contributors": []}
        r = self.sig.analyze(data)
        assert r.score == 0.0

    def test_single_contributor(self):
        data = {"contributors": self._make_contributors(1)}
        r = self.sig.analyze(data)
        assert r.score == 0.3

    def test_missing_key(self):
        r = self.sig.analyze({})
        assert isinstance(r, SignalResult)


# --- IssueRatioSignal ---

class TestIssueRatio:
    sig = IssueRatioSignal()

    def test_zero_issues(self):
        data = {"repo": {"open_issues_count": 0}, "closed_issues": []}
        r = self.sig.analyze(data)
        assert r.score == 1.0
        assert r.verdict == "good"

    def test_low_open_ratio(self):
        closed = [{}] * 90
        data = {"repo": {"open_issues_count": 5}, "closed_issues": closed}
        r = self.sig.analyze(data)
        assert r.score == 1.0

    def test_high_open_ratio(self):
        closed = [{}] * 5
        data = {"repo": {"open_issues_count": 90}, "closed_issues": closed}
        r = self.sig.analyze(data)
        assert r.score == 0.0

    def test_missing_key(self):
        r = self.sig.analyze({})
        assert isinstance(r, SignalResult)


# --- ArchiveStatusSignal ---

class TestArchiveStatus:
    sig = ArchiveStatusSignal()

    def test_not_archived_score_1(self):
        data = {"repo": {"archived": False}}
        r = self.sig.analyze(data)
        assert r.score == 1.0
        assert r.verdict == "good"
        assert r.is_free_tier is True

    def test_archived_score_0(self):
        data = {"repo": {"archived": True}}
        r = self.sig.analyze(data)
        assert r.score == 0.0
        assert r.verdict == "bad"

    def test_missing_archived_field_defaults_not_archived(self):
        data = {"repo": {}}
        r = self.sig.analyze(data)
        assert r.score == 1.0

    def test_missing_repo_key(self):
        r = self.sig.analyze({})
        assert isinstance(r, SignalResult)
        assert r.score == 1.0