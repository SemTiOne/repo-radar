"""
tests/test_scorer.py — Tests for core/scorer.py
"""

import pytest

from core.scorer import calculate_score, get_score_label, get_score_color
from core.signals.base import SignalResult


def _signal(name: str, score: float, weight: float, is_free: bool = True) -> SignalResult:
    return SignalResult(
        name=name,
        label=name,
        score=score,
        weight=weight,
        value="test",
        verdict="good" if score >= 0.6 else "bad",
        detail="test",
        is_free_tier=is_free,
    )


class TestCalculateScore:
    def test_weighted_average_correct(self):
        signals = [
            _signal("a", 1.0, 0.5),
            _signal("b", 0.0, 0.5),
        ]
        score = calculate_score(signals)
        assert abs(score - 50.0) < 0.01

    def test_score_clamped_to_100(self):
        signals = [_signal("a", 1.0, 1.0)]
        assert calculate_score(signals) <= 100.0

    def test_score_clamped_to_0(self):
        signals = [_signal("a", 0.0, 1.0)]
        assert calculate_score(signals) >= 0.0

    def test_archive_override_returns_0(self):
        signals = [
            _signal("commit_recency", 1.0, 0.25),
            SignalResult(
                name="archive_status",
                label="Archive Status",
                score=0.0,
                weight=0.02,
                value="Archived",
                verdict="bad",
                detail="Archived",
                is_free_tier=True,
            ),
        ]
        assert calculate_score(signals) == 0.0

    def test_empty_signals_returns_0(self):
        assert calculate_score([]) == 0.0

    def test_single_signal_full_weight(self):
        signals = [_signal("commit_recency", 0.7, 0.25)]
        score = calculate_score(signals)
        assert abs(score - 70.0) < 0.01


class TestGetScoreLabel:
    def test_healthy(self):
        assert get_score_label(90) == "Healthy"

    def test_maintained(self):
        assert get_score_label(65) == "Maintained"

    def test_slowing_down(self):
        assert get_score_label(50) == "Slowing Down"

    def test_barely_alive(self):
        assert get_score_label(25) == "Barely Alive"

    def test_dead(self):
        assert get_score_label(10) == "Dead"

    def test_boundary_80(self):
        assert get_score_label(80) == "Healthy"

    def test_boundary_60(self):
        assert get_score_label(60) == "Maintained"


class TestGetScoreColor:
    def test_high_score_green(self):
        assert "green" in get_score_color(85)

    def test_low_score_red(self):
        assert get_score_color(10) == "red"

    def test_mid_score_yellow(self):
        assert get_score_color(45) == "yellow"