"""
core/analyzer.py — Main analysis orchestrator for RepoRadar.

Fetches repository data, runs all applicable signals, scores the result,
and records to history. Fully decoupled from the CLI.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from cache.file_cache import FileCache
from core.github_client import GitHubClient
from core.signals.base import SignalResult
from core.signals import SIGNAL_MAP
from core.scorer import calculate_score, get_score_label
from core.verdict import determine_verdict
from core.reporter import build_report
from subscription.tiers import get_allowed_signals


@dataclass
class AnalysisResult:
    """Complete result of a repository health analysis."""

    owner: str
    repo: str
    url: str
    score: float
    verdict: str
    signals: List[SignalResult]
    report: dict
    cached: bool
    analyzed_at: str
    tier: str
    duration_ms: int


class RepoAnalyzer:
    """Orchestrates all analysis steps for a GitHub repository."""

    def __init__(
        self,
        client: GitHubClient,
        tier: str,
        cache: Optional[FileCache] = None,
    ) -> None:
        """Initialize the analyzer.

        Args:
            client: Initialized GitHubClient.
            tier: 'free' or 'paid'.
            cache: Optional FileCache instance. Pass None to disable caching.
        """
        self.client = client
        self.tier = tier
        self.cache = cache

    def analyze(self, owner: str, repo: str) -> AnalysisResult:
        """Run a full health analysis on the specified repository.

        Checks cache first, fetches data from GitHub API if needed,
        runs all tier-appropriate signals, scores and verdicts the result,
        and records the check to history.

        Args:
            owner: GitHub username or organization.
            repo: Repository name.

        Returns:
            Populated AnalysisResult.
        """
        start_ms = int(time.time() * 1000)
        url = f"https://github.com/{owner}/{repo}"
        cached = False

        # Check cache
        if self.cache:
            key = self.cache.make_key(owner, repo)
            cached_data = self.cache.get(key)
            if cached_data:
                cached = True
                duration_ms = int(time.time() * 1000) - start_ms
                result = self._result_from_cache(cached_data, owner, repo, url, duration_ms)
                self._record(result)
                return result

        # Fetch data from GitHub
        repo_data = self._fetch_repo_data(owner, repo)

        # Run signals
        allowed_signals = get_allowed_signals(self.tier)
        signals: List[SignalResult] = []
        for signal_name in allowed_signals:
            signal_cls = SIGNAL_MAP.get(signal_name)
            if signal_cls:
                signal = signal_cls()
                result_signal = signal.analyze(repo_data)
                signals.append(result_signal)

        # Score and verdict
        score = calculate_score(signals)
        verdict = determine_verdict(score, signals)
        analyzed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        duration_ms = int(time.time() * 1000) - start_ms

        result = AnalysisResult(
            owner=owner,
            repo=repo,
            url=url,
            score=score,
            verdict=verdict,
            signals=signals,
            report={},
            cached=cached,
            analyzed_at=analyzed_at,
            tier=self.tier,
            duration_ms=duration_ms,
        )
        result.report = build_report(result)

        # Store in cache
        if self.cache:
            self.cache.set(key, self._result_to_cache(result))

        self._record(result)
        return result

    def _fetch_repo_data(self, owner: str, repo: str) -> dict:
        """Fetch all required data from GitHub API for signal analysis.

        Args:
            owner: GitHub username or org.
            repo: Repository name.

        Returns:
            Aggregated data dict keyed by signal data type.
        """
        allowed_signals = get_allowed_signals(self.tier)
        data: Dict = {}

        # Always fetch repo metadata
        data["repo"] = self.client.get_repo(owner, repo)

        if "commit_frequency" in allowed_signals:
            try:
                data["commit_activity"] = self.client.get_commit_activity(owner, repo)
            except Exception:
                data["commit_activity"] = []

        if "issue_response" in allowed_signals or "issue_ratio" in allowed_signals:
            try:
                closed_issues = self.client.get_closed_issues(owner, repo)
                data["closed_issues"] = closed_issues

                if "issue_response" in allowed_signals:
                    issue_comments: Dict[str, list] = {}
                    for issue in closed_issues[:10]:  # Limit API calls
                        num = issue.get("number")
                        if num:
                            issue_comments[str(num)] = self.client.get_issue_comments(
                                owner, repo, num
                            )
                    data["issue_comments"] = issue_comments
            except Exception:
                data["closed_issues"] = []
                data["issue_comments"] = {}

        if "pr_merge_rate" in allowed_signals:
            try:
                data["closed_prs"] = self.client.get_closed_prs(owner, repo)
            except Exception:
                data["closed_prs"] = []

        if "release_frequency" in allowed_signals:
            try:
                data["releases"] = self.client.get_releases(owner, repo)
            except Exception:
                data["releases"] = []

        if "contributor_activity" in allowed_signals:
            try:
                data["contributors"] = self.client.get_contributors(owner, repo)
            except Exception:
                data["contributors"] = []

        return data

    def _result_to_cache(self, result: AnalysisResult) -> dict:
        """Serialize an AnalysisResult to a cacheable dict."""
        return {
            "owner": result.owner,
            "repo": result.repo,
            "url": result.url,
            "score": result.score,
            "verdict": result.verdict,
            "signals": [
                {
                    "name": s.name,
                    "label": s.label,
                    "score": s.score,
                    "weight": s.weight,
                    "value": s.value,
                    "verdict": s.verdict,
                    "detail": s.detail,
                    "is_free_tier": s.is_free_tier,
                }
                for s in result.signals
            ],
            "report": result.report,
            "analyzed_at": result.analyzed_at,
            "tier": result.tier,
            "duration_ms": result.duration_ms,
        }

    def _result_from_cache(
        self,
        data: dict,
        owner: str,
        repo: str,
        url: str,
        duration_ms: int,
    ) -> AnalysisResult:
        """Deserialize a cached dict back into an AnalysisResult."""
        signals = [
            SignalResult(
                name=s["name"],
                label=s["label"],
                score=s["score"],
                weight=s["weight"],
                value=s["value"],
                verdict=s["verdict"],
                detail=s["detail"],
                is_free_tier=s["is_free_tier"],
            )
            for s in data.get("signals", [])
        ]
        result = AnalysisResult(
            owner=owner,
            repo=repo,
            url=url,
            score=data.get("score", 0.0),
            verdict=data.get("verdict", "unknown"),
            signals=signals,
            report=data.get("report", {}),
            cached=True,
            analyzed_at=data.get("analyzed_at", ""),
            tier=data.get("tier", self.tier),
            duration_ms=duration_ms,
        )
        return result

    def _record(self, result: AnalysisResult) -> None:
        """Record the analysis result to the local history log."""
        try:
            from history.audit_log import record_check
            from core.scorer import get_score_label
            import sys

            command = " ".join(sys.argv)
            record_check(
                repo=f"{result.owner}/{result.repo}",
                url=result.url,
                score=result.score,
                score_label=get_score_label(result.score),
                verdict=result.verdict,
                tier=result.tier,
                signals_run=[s.name for s in result.signals],
                cached=result.cached,
                command=command,
                duration_ms=result.duration_ms,
            )
        except Exception:
            pass  # Never fail the analysis due to history logging errors