"""
tests/test_audit_log.py — Tests for history/audit_log.py

History isolation is handled by the autouse `isolate_history` fixture in
conftest.py, which sets HISTORY_PATH env var per test so load_config()
always resolves to a fresh temp file.
"""

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest


def _record(repo="user/repo", score=75.0, verdict="alive"):
    """Record a check (isolation handled by conftest autouse fixture)."""
    from history.audit_log import record_check
    record_check(
        repo=repo,
        url=f"https://github.com/{repo}",
        score=score,
        score_label="Maintained",
        verdict=verdict,
        tier="free",
        signals_run=["commit_recency"],
        cached=False,
        command="reporadar check user/repo",
        duration_ms=123,
    )


def test_record_check_appends_entry(isolate_history):
    _record()
    data = json.loads(isolate_history.read_text())
    assert len(data["entries"]) == 1
    e = data["entries"][0]
    assert e["repo"] == "user/repo"
    assert e["score"] == 75.0
    assert e["verdict"] == "alive"
    assert "id" in e
    assert "timestamp" in e


def test_get_history_newest_first(isolate_history):
    _record(score=50.0)
    _record(score=80.0)

    from history.audit_log import get_history
    entries = get_history()
    assert entries[0]["score"] == 80.0
    assert entries[1]["score"] == 50.0


def test_get_history_filters_by_repo(isolate_history):
    _record(repo="user/repo-a", score=60.0)
    _record(repo="user/repo-b", score=40.0)

    from history.audit_log import get_history
    entries = get_history(repo="user/repo-a")
    assert len(entries) == 1
    assert entries[0]["repo"] == "user/repo-a"


def test_clear_history_returns_count(isolate_history):
    _record()
    _record()

    from history.audit_log import clear_history
    count = clear_history()
    assert count == 2

    data = json.loads(isolate_history.read_text())
    assert data["entries"] == []


def test_get_history_stats_structure(isolate_history):
    _record(repo="user/repo", score=70.0)
    _record(repo="user/repo", score=80.0)
    _record(repo="user/other", score=50.0)

    from history.audit_log import get_history_stats
    stats = get_history_stats()

    assert stats["total_entries"] == 3
    assert stats["unique_repos"] == 2
    assert stats["most_checked_repo"] == "user/repo"
    assert isinstance(stats["avg_score"], float)
    assert stats["oldest_entry"] != ""
    assert stats["newest_entry"] != ""


def test_get_trend_none_for_fewer_than_2(isolate_history):
    _record(repo="user/repo", score=70.0)

    from history.audit_log import get_trend
    result = get_trend("user/repo")
    assert result is None


def test_get_trend_improving(isolate_history):
    _record(repo="user/repo", score=30.0)
    _record(repo="user/repo", score=80.0)

    from history.audit_log import get_trend
    result = get_trend("user/repo")
    assert result is not None
    assert result["trend"] == "improving"
    assert result["score_change"] > 0


def test_get_trend_declining(isolate_history):
    _record(repo="user/repo", score=85.0)
    _record(repo="user/repo", score=25.0)

    from history.audit_log import get_trend
    result = get_trend("user/repo")
    assert result is not None
    assert result["trend"] == "declining"
    assert result["score_change"] < 0


def test_history_purged_over_max(tmp_path, monkeypatch):
    history_file = tmp_path / "purge.json"
    monkeypatch.setenv("HISTORY_PATH", str(history_file))
    monkeypatch.setenv("MAX_HISTORY_ENTRIES", "5")

    from history.audit_log import record_check, load_history
    for i in range(7):
        record_check(
            repo=f"user/repo-{i}",
            url=f"https://github.com/user/repo-{i}",
            score=float(i * 10),
            score_label="Test",
            verdict="alive",
            tier="free",
            signals_run=["commit_recency"],
            cached=False,
            command="test",
            duration_ms=100,
        )
    h = load_history()
    assert len(h["entries"]) <= 5


def test_history_file_created_if_missing(tmp_path, monkeypatch):
    new_path = tmp_path / "new_history.json"
    assert not new_path.exists()
    monkeypatch.setenv("HISTORY_PATH", str(new_path))

    from history.audit_log import load_history
    data = load_history()

    assert new_path.exists()
    assert "entries" in data