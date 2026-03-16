"""
core/reporter.py — Build structured reports from analysis results.

Produces human-readable summaries and actionable recommendations.
"""

from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from core.analyzer import AnalysisResult

from core.signals.base import SignalResult
from core.scorer import get_score_label, get_score_color
from core.verdict import get_verdict_emoji


def build_report(result: "AnalysisResult") -> dict:
    """Build a full structured report dict from an AnalysisResult.

    Args:
        result: Completed AnalysisResult from the analyzer.

    Returns:
        Dict with all report fields including summary, recommendations,
        signal breakdown, and metadata.
    """
    summary = build_summary(result.signals, result.verdict)
    recommendations = build_recommendations(result.signals)

    signal_details = [
        {
            "name": s.name,
            "label": s.label,
            "score": round(s.score * 100, 1),
            "weight": s.weight,
            "value": s.value,
            "verdict": s.verdict,
            "detail": s.detail,
            "is_free_tier": s.is_free_tier,
        }
        for s in result.signals
    ]

    return {
        "repo": result.repo,
        "owner": result.owner,
        "url": result.url,
        "score": result.score,
        "score_label": get_score_label(result.score),
        "verdict": result.verdict,
        "verdict_emoji": get_verdict_emoji(result.verdict),
        "tier": result.tier,
        "cached": result.cached,
        "analyzed_at": result.analyzed_at,
        "duration_ms": result.duration_ms,
        "summary": summary,
        "recommendations": recommendations,
        "signals": signal_details,
    }


def build_summary(signals: List[SignalResult], verdict: str) -> str:
    """Generate a one-paragraph summary of the repository health.

    Args:
        signals: List of completed SignalResult objects.
        verdict: Overall verdict string ("alive", "uncertain", "dead").

    Returns:
        Human-readable summary string.
    """
    emoji = get_verdict_emoji(verdict)
    good = [s for s in signals if s.verdict == "good"]
    bad = [s for s in signals if s.verdict == "bad"]
    warning = [s for s in signals if s.verdict == "warning"]

    if verdict == "alive":
        base = f"{emoji} This repository appears to be actively maintained."
    elif verdict == "uncertain":
        base = f"{emoji} This repository shows mixed maintenance signals."
    else:
        base = f"{emoji} This repository appears to be unmaintained or dead."

    parts = [base]
    if good:
        parts.append(f"Strong signals: {', '.join(s.label for s in good[:3])}.")
    if bad:
        parts.append(f"Weak signals: {', '.join(s.label for s in bad[:3])}.")
    if warning:
        parts.append(f"Watch: {', '.join(s.label for s in warning[:2])}.")

    return " ".join(parts)


def build_recommendations(signals: List[SignalResult]) -> List[str]:
    """Generate a list of actionable recommendations based on signal results.

    Args:
        signals: List of completed SignalResult objects.

    Returns:
        List of recommendation strings. Empty list if repo is healthy.
    """
    recommendations: List[str] = []

    signal_map = {s.name: s for s in signals}

    recency = signal_map.get("commit_recency")
    if recency and recency.score < 0.4:
        recommendations.append(
            "⚠️  No recent commits — consider finding an actively maintained fork."
        )

    freq = signal_map.get("commit_frequency")
    if freq and freq.score < 0.4:
        recommendations.append(
            "📉 Commit frequency is declining significantly — watch for project abandonment."
        )

    issue_resp = signal_map.get("issue_response")
    if issue_resp and issue_resp.score < 0.4:
        recommendations.append(
            "🐌 Slow issue response time — expect delays if you open a bug report."
        )

    pr_rate = signal_map.get("pr_merge_rate")
    if pr_rate and pr_rate.score < 0.4:
        recommendations.append(
            "🚫 Low PR merge rate — contributions may not be accepted."
        )

    releases = signal_map.get("release_frequency")
    if releases and releases.score < 0.3:
        recommendations.append(
            "📦 No recent releases — check if the project follows a release cycle."
        )

    contrib = signal_map.get("contributor_activity")
    if contrib and contrib.score < 0.4:
        recommendations.append(
            "👤 Low contributor activity — project may be a single-maintainer risk."
        )

    ratio = signal_map.get("issue_ratio")
    if ratio and ratio.score < 0.3:
        recommendations.append(
            "🐛 High open issue ratio — many issues may be going unaddressed."
        )

    archive = signal_map.get("archive_status")
    if archive and archive.score == 0.0:
        recommendations.append(
            "🔒 Repository is archived — no further development will occur. Seek an alternative."
        )

    if not recommendations:
        recommendations.append("✅ Repository looks healthy — no immediate concerns.")

    return recommendations