"""
core/verdict.py — Determine the Dead / Alive / Uncertain verdict for a repo.

Verdict is based on health score and signal overrides (e.g. archived).
"""

from typing import List

from core.signals.base import SignalResult


def determine_verdict(score: float, signals: List[SignalResult]) -> str:
    """Determine the health verdict for a repository.

    Rules:
      - Archived (archive_status score == 0.0) → always "dead"
      - score >= 60  → "alive"
      - score 35–59  → "uncertain"
      - score < 35   → "dead"

    Args:
        score: Computed health score (0–100).
        signals: List of SignalResult objects (checked for archive override).

    Returns:
        One of: "alive", "uncertain", "dead".
    """
    # Archive override
    for signal in signals:
        if signal.name == "archive_status" and signal.score == 0.0:
            return "dead"

    if score >= 60:
        return "alive"
    if score >= 35:
        return "uncertain"
    return "dead"


def get_verdict_emoji(verdict: str) -> str:
    """Return an emoji for a given verdict string.

    Args:
        verdict: One of "alive", "uncertain", "dead".

    Returns:
        Emoji string.
    """
    return {
        "alive": "✅",
        "uncertain": "⚠️",
        "dead": "💀",
    }.get(verdict, "❓")


def get_verdict_color(verdict: str) -> str:
    """Return a rich color string for the given verdict.

    Args:
        verdict: One of "alive", "uncertain", "dead".

    Returns:
        Rich color name string.
    """
    return {
        "alive": "green",
        "uncertain": "yellow",
        "dead": "red",
    }.get(verdict, "white")