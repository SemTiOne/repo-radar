"""
core/scorer.py — Weighted score calculation for RepoRadar health signals.

Computes a 0–100 score from a list of SignalResults.
Archived repos always score 0 (archive_status override).
"""

from typing import List

from core.signals.base import SignalResult


def calculate_score(signals: List[SignalResult]) -> float:
    """Compute a weighted health score from 0 to 100.

    If any signal is 'archive_status' with score 0.0, the entire
    score is overridden to 0.0 (repository is archived).

    Args:
        signals: List of SignalResult objects from each signal analysis.

    Returns:
        Health score as a float between 0.0 and 100.0.
    """
    if not signals:
        return 0.0

    # Archive override: if archived, score is always 0
    for signal in signals:
        if signal.name == "archive_status" and signal.score == 0.0:
            return 0.0

    total_weight = sum(s.weight for s in signals)
    if total_weight == 0:
        return 0.0

    weighted_sum = sum(s.score * s.weight for s in signals)
    raw_score = (weighted_sum / total_weight) * 100.0

    # Clamp to 0–100
    return max(0.0, min(100.0, round(raw_score, 2)))


def get_score_label(score: float) -> str:
    """Return a human-readable label for a given health score.

    Ranges:
      80–100 → "Healthy"
      60–79  → "Maintained"
      40–59  → "Slowing Down"
      20–39  → "Barely Alive"
      0–19   → "Dead"

    Args:
        score: Health score between 0 and 100.

    Returns:
        Label string.
    """
    if score >= 80:
        return "Healthy"
    if score >= 60:
        return "Maintained"
    if score >= 40:
        return "Slowing Down"
    if score >= 20:
        return "Barely Alive"
    return "Dead"


def get_score_color(score: float) -> str:
    """Return a rich color string for terminal rendering based on score.

    Args:
        score: Health score between 0 and 100.

    Returns:
        Rich color name string (e.g. 'green', 'yellow', 'red').
    """
    if score >= 80:
        return "bright_green"
    if score >= 60:
        return "green"
    if score >= 40:
        return "yellow"
    if score >= 20:
        return "dark_orange"
    return "red"