"""
tests/test_analyzer.py — Tests for core/analyzer.py
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call
import pytest

from core.analyzer import RepoAnalyzer, AnalysisResult
from core.github_client import RepoNotFoundError
from core.signals.base import SignalResult


def _fake_repo():
    return {
        "archived": False,
        "pushed_at": "2024-01-01T00:00:00Z",
        "open_issues_count": 5,
        "name": "repo",
        "full_name": "user/repo",
    }


def _make_client():
    client = MagicMock()
    client.get_repo.return_value = _fake_repo()
    client.get_commit_activity.return_value = [{"total": 5}] * 52
    client.get_closed_issues.return_value = []
    client.get_closed_prs.return_value = []
    client.get_releases.return_value = []
    client.get_contributors.return_value = []
    client.get_issue_comments.return_value = []
    return client


class TestRepoAnalyzer:

    def test_returns_analysis_result_with_all_fields(self):
        client = _make_client()
        with patch("history.audit_log.record_check"):
            analyzer = RepoAnalyzer(client=client, tier="free", cache=None)
            result = analyzer.analyze("user", "repo")

        assert isinstance(result, AnalysisResult)
        assert result.owner == "user"
        assert result.repo == "repo"
        assert result.url == "https://github.com/user/repo"
        assert isinstance(result.score, float)
        assert result.verdict in ("alive", "uncertain", "dead")
        assert isinstance(result.signals, list)
        assert isinstance(result.report, dict)
        assert isinstance(result.duration_ms, int)
        assert result.duration_ms >= 0
        assert result.tier == "free"
        assert result.cached is False

    def test_uses_cache_when_available(self, tmp_path):
        from cache.file_cache import FileCache

        client = _make_client()
        cache = FileCache(str(tmp_path), ttl_seconds=3600)

        with patch("history.audit_log.record_check"):
            analyzer = RepoAnalyzer(client=client, tier="free", cache=cache)
            result1 = analyzer.analyze("user", "repo")

        # Second call — client should NOT be called again
        client2 = _make_client()
        with patch("history.audit_log.record_check"):
            analyzer2 = RepoAnalyzer(client=client2, tier="free", cache=cache)
            result2 = analyzer2.analyze("user", "repo")

        assert result2.cached is True
        client2.get_repo.assert_not_called()

    def test_free_tier_runs_only_free_signals(self):
        client = _make_client()
        with patch("history.audit_log.record_check"):
            analyzer = RepoAnalyzer(client=client, tier="free", cache=None)
            result = analyzer.analyze("user", "repo")

        signal_names = [s.name for s in result.signals]
        assert "commit_recency" in signal_names
        assert "issue_ratio" in signal_names
        assert "archive_status" in signal_names
        # Paid signals should NOT be present
        assert "commit_frequency" not in signal_names
        assert "pr_merge_rate" not in signal_names

    def test_paid_tier_runs_all_signals(self):
        client = _make_client()
        with patch("history.audit_log.record_check"):
            analyzer = RepoAnalyzer(client=client, tier="paid", cache=None)
            result = analyzer.analyze("user", "repo")

        signal_names = [s.name for s in result.signals]
        assert "commit_recency" in signal_names
        assert "commit_frequency" in signal_names
        assert "pr_merge_rate" in signal_names

    def test_calls_record_check_after_analysis(self):
        client = _make_client()
        with patch("history.audit_log.record_check") as mock_record:
            analyzer = RepoAnalyzer(client=client, tier="free", cache=None)
            analyzer.analyze("user", "repo")
        mock_record.assert_called_once()

    def test_handles_repo_not_found(self):
        client = _make_client()
        client.get_repo.side_effect = RepoNotFoundError("Not found")

        analyzer = RepoAnalyzer(client=client, tier="free", cache=None)
        with pytest.raises(RepoNotFoundError):
            analyzer.analyze("user", "missing-repo")