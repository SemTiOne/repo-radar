"""
core — Central analysis engine for RepoRadar.

Contains the analyzer, scorer, verdict logic, reporter, signals, and GitHub client.
This package is completely decoupled from the CLI, API, and subscription layers.
"""

from core.analyzer import RepoAnalyzer, AnalysisResult
from core.github_client import (
    GitHubClient,
    RepoNotFoundError,
    GitHubAPIError,
    RateLimitExceededError,
    InvalidRepoURLError,
)

__all__ = [
    "RepoAnalyzer",
    "AnalysisResult",
    "GitHubClient",
    "RepoNotFoundError",
    "GitHubAPIError",
    "RateLimitExceededError",
    "InvalidRepoURLError",
]