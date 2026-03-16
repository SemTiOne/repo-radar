"""
subscription/tiers.py — Tier definitions and signal access control for RepoRadar.

Free tier: 3 signals, no bulk/export/history.
Paid tier: All 8 signals, bulk check, export, history, no watermark.
"""

from typing import List, Tuple

FREE_SIGNALS: List[str] = ["commit_recency", "issue_ratio", "archive_status"]

PAID_SIGNALS: List[str] = [
    "commit_recency",
    "commit_frequency",
    "issue_response",
    "pr_merge_rate",
    "release_frequency",
    "contributor_activity",
    "issue_ratio",
    "archive_status",
]

# Features gated behind paid tier
_PAID_FEATURES = {
    "bulk_check",
    "json_export",
    "markdown_export",
    "history",
    "all_signals",
    "no_watermark",
    "trend_analysis",
}


def get_allowed_signals(tier: str) -> List[str]:
    """Return the list of signal names allowed for the given tier.

    Args:
        tier: 'free' or 'paid'.

    Returns:
        List of signal name strings.
    """
    if tier == "paid":
        return list(PAID_SIGNALS)
    return list(FREE_SIGNALS)


def is_paid(tier: str) -> bool:
    """Check whether the given tier is a paid tier.

    Args:
        tier: Tier string.

    Returns:
        True if paid, False otherwise.
    """
    return tier == "paid"


def enforce_tier(tier: str, feature: str) -> Tuple[bool, str]:
    """Check whether a feature is allowed for the given tier.

    Args:
        tier: 'free' or 'paid'.
        feature: Feature name string (e.g. 'bulk_check', 'json_export').

    Returns:
        (True, "") if allowed, (False, upgrade_message) if not.
    """
    if feature in _PAID_FEATURES and not is_paid(tier):
        return (
            False,
            f"'{feature}' requires a paid subscription ($4.99/month or $29 one-time). "
            "Upgrade at reporadar.dev",
        )
    return True, ""