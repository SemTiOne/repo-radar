"""
tests/test_verdict.py — Tests for core/verdict.py
"""

import pytest

from core.verdict import determine_verdict, get_verdict_emoji, get_verdict_color
from core.signals.base import SignalResult


def _signal(name: str, score: float) -> SignalResult:
    return SignalResult(
        name=name,
        label=name,
        score=score,
        weight=0.1,
        value="test",
        verdict="good" if score >= 0.6 else "bad",
        detail="test",
        is_free_tier=True,
    )


class TestDetermineVerdict:
    def test_archived_always_dead(self):
        signals = [
            _signal("commit_recency", 1.0),
            _signal("archive_status", 0.0),
        ]
        assert determine_verdict(95.0, signals) == "dead"

    def test_score_60_or_above_alive(self):
        signals = [_signal("commit_recency", 1.0)]
        assert determine_verdict(60.0, signals) == "alive"
        assert determine_verdict(80.0, signals) == "alive"
        assert determine_verdict(100.0, signals) == "alive"

    def test_score_35_to_59_uncertain(self):
        signals = [_signal("commit_recency", 0.5)]
        assert determine_verdict(35.0, signals) == "uncertain"
        assert determine_verdict(50.0, signals) == "uncertain"
        assert determine_verdict(59.9, signals) == "uncertain"

    def test_score_below_35_dead(self):
        signals = [_signal("commit_recency", 0.1)]
        assert determine_verdict(34.9, signals) == "dead"
        assert determine_verdict(0.0, signals) == "dead"

    def test_archive_status_score_1_not_dead(self):
        # Non-zero archive status should not override
        signals = [_signal("archive_status", 1.0)]
        assert determine_verdict(80.0, signals) == "alive"

    def test_empty_signals_low_score_dead(self):
        assert determine_verdict(10.0, []) == "dead"


class TestGetVerdictEmoji:
    def test_alive_emoji(self):
        assert get_verdict_emoji("alive") == "✅"

    def test_dead_emoji(self):
        assert get_verdict_emoji("dead") == "💀"

    def test_uncertain_emoji(self):
        assert get_verdict_emoji("uncertain") == "⚠️"

    def test_unknown_verdict(self):
        emoji = get_verdict_emoji("unknown_xyz")
        assert isinstance(emoji, str)


class TestGetVerdictColor:
    def test_alive_green(self):
        assert get_verdict_color("alive") == "green"

    def test_dead_red(self):
        assert get_verdict_color("dead") == "red"

    def test_uncertain_yellow(self):
        assert get_verdict_color("uncertain") == "yellow"