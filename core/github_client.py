"""
core/github_client.py — All GitHub API interactions for RepoRadar.

This is the single source of truth for GitHub API calls.
No other module should call the GitHub API directly.
"""

import re
import time
from typing import Dict, List, Optional, Tuple

import requests

from security import mask_token


class RepoNotFoundError(Exception):
    """Raised when a GitHub repository cannot be found (404)."""
    pass


class GitHubAPIError(Exception):
    """Raised for unexpected GitHub API errors (non-404, non-429)."""
    pass


class RateLimitExceededError(Exception):
    """Raised when GitHub API rate limit is exhausted."""
    pass


class InvalidRepoURLError(Exception):
    """Raised when a URL cannot be parsed into owner/repo."""
    pass


_GITHUB_URL_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git|/.*)?$"
)
_SHORTHAND_RE = re.compile(r"^([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?$")


class GitHubClient:
    """Client for interacting with the GitHub REST API v3."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None) -> None:
        """Initialize the GitHub API client.

        Args:
            token: Optional GitHub personal access token. Without a token,
                   the API rate limit is 60 requests/hour.
        """
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "RepoRadar/0.1.0",
        })
        if token:
            self.session.headers["Authorization"] = f"token {token}"

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        """Perform a GET request and return the parsed JSON response.

        Args:
            path: API path (e.g. '/repos/owner/repo').
            params: Optional query parameters.

        Returns:
            Parsed JSON response dict.

        Raises:
            RepoNotFoundError: On HTTP 404.
            RateLimitExceededError: On HTTP 429 or rate limit headers.
            GitHubAPIError: On all other non-2xx responses.
        """
        url = f"{self.BASE_URL}{path}"
        resp = self.session.get(url, params=params, timeout=15)

        if resp.status_code == 404:
            raise RepoNotFoundError(f"Repository not found: {path}")
        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            raise RateLimitExceededError("GitHub API rate limit exceeded.")
        if resp.status_code == 429:
            raise RateLimitExceededError("GitHub API rate limit exceeded (429).")
        if not resp.ok:
            raise GitHubAPIError(
                f"GitHub API error {resp.status_code} for {path}: {resp.text[:200]}"
            )
        return resp.json()

    def _get_list(self, path: str, params: Optional[dict] = None) -> List[dict]:
        """Perform a GET that returns a JSON list.

        Args:
            path: API path.
            params: Optional query parameters.

        Returns:
            Parsed JSON list.
        """
        result = self._get(path, params=params)
        if isinstance(result, list):
            return result
        return []

    def _get_with_202_retry(self, path: str, max_retries: int = 3, delay: float = 2.0) -> List[dict]:
        """GET with retry logic for 202 Accepted responses (async GitHub endpoints).

        Args:
            path: API path.
            max_retries: Maximum number of retry attempts.
            delay: Seconds to wait between retries.

        Returns:
            Parsed JSON list once data is ready.

        Raises:
            GitHubAPIError: If still receiving 202 after all retries.
        """
        url = f"{self.BASE_URL}{path}"
        for attempt in range(max_retries + 1):
            resp = self.session.get(url, timeout=15)
            if resp.status_code == 202:
                if attempt < max_retries:
                    time.sleep(delay)
                    continue
                else:
                    raise GitHubAPIError(
                        f"GitHub returned 202 after {max_retries} retries for {path}. Try again later."
                    )
            if resp.status_code == 404:
                raise RepoNotFoundError(f"Not found: {path}")
            if not resp.ok:
                raise GitHubAPIError(f"GitHub API error {resp.status_code} for {path}")
            data = resp.json()
            return data if isinstance(data, list) else []
        return []

    def get_repo(self, owner: str, repo: str) -> dict:
        """Fetch repository metadata.

        Args:
            owner: GitHub username or org.
            repo: Repository name.

        Returns:
            Repository object dict from GitHub API.
        """
        return self._get(f"/repos/{owner}/{repo}")

    def get_commit_activity(self, owner: str, repo: str) -> List[dict]:
        """Fetch weekly commit activity (last 52 weeks).

        Uses 202 retry logic — GitHub computes this asynchronously.

        Args:
            owner: GitHub username or org.
            repo: Repository name.

        Returns:
            List of weekly commit stat objects.
        """
        return self._get_with_202_retry(f"/repos/{owner}/{repo}/stats/commit_activity")

    def get_closed_issues(self, owner: str, repo: str, count: int = 20) -> List[dict]:
        """Fetch recently closed issues (excluding pull requests).

        Args:
            owner: GitHub username or org.
            repo: Repository name.
            count: Number of issues to fetch.

        Returns:
            List of issue objects.
        """
        issues = self._get_list(
            f"/repos/{owner}/{repo}/issues",
            params={"state": "closed", "per_page": count, "sort": "updated", "direction": "desc"},
        )
        # Exclude pull requests (GitHub returns PRs in the issues endpoint)
        return [i for i in issues if "pull_request" not in i][:count]

    def get_closed_prs(self, owner: str, repo: str, count: int = 20) -> List[dict]:
        """Fetch recently closed pull requests.

        Args:
            owner: GitHub username or org.
            repo: Repository name.
            count: Number of PRs to fetch.

        Returns:
            List of pull request objects.
        """
        return self._get_list(
            f"/repos/{owner}/{repo}/pulls",
            params={"state": "closed", "per_page": count, "sort": "updated", "direction": "desc"},
        )[:count]

    def get_releases(self, owner: str, repo: str, count: int = 10) -> List[dict]:
        """Fetch recent releases.

        Args:
            owner: GitHub username or org.
            repo: Repository name.
            count: Number of releases to fetch.

        Returns:
            List of release objects.
        """
        return self._get_list(
            f"/repos/{owner}/{repo}/releases",
            params={"per_page": count},
        )[:count]

    def get_contributors(self, owner: str, repo: str) -> List[dict]:
        """Fetch contributor statistics with weekly commit data.

        Uses 202 retry logic — GitHub computes this asynchronously.

        Args:
            owner: GitHub username or org.
            repo: Repository name.

        Returns:
            List of contributor stat objects with 'weeks' arrays.
        """
        return self._get_with_202_retry(f"/repos/{owner}/{repo}/stats/contributors")

    def get_issue_comments(self, owner: str, repo: str, issue_number: int) -> List[dict]:
        """Fetch comments on a specific issue.

        Args:
            owner: GitHub username or org.
            repo: Repository name.
            issue_number: Issue number.

        Returns:
            List of comment objects.
        """
        try:
            return self._get_list(
                f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
                params={"per_page": 10},
            )
        except Exception:
            return []

    def get_rate_limit(self) -> dict:
        """Fetch current GitHub API rate limit status.

        Returns:
            Rate limit info dict with 'resources.core' sub-dict.
        """
        return self._get("/rate_limit")

    def check_rate_limit_before_call(self) -> None:
        """Check remaining API calls and warn or raise as appropriate.

        Warns (via rich) if remaining < 10.
        Raises RateLimitExceededError if remaining == 0.
        """
        from rich.console import Console
        console = Console(stderr=True)

        try:
            data = self.get_rate_limit()
            core = data.get("resources", {}).get("core", {})
            remaining = core.get("remaining", 1)
            reset_ts = core.get("reset", 0)
            reset_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(reset_ts))

            if remaining == 0:
                raise RateLimitExceededError(
                    f"GitHub API rate limit exhausted. Resets at {reset_iso}."
                )
            if remaining < 10:
                console.print(
                    f"[yellow]⚠️  GitHub API rate limit low: {remaining} calls remaining "
                    f"(resets at {reset_iso})[/yellow]"
                )
        except RateLimitExceededError:
            raise
        except Exception:
            pass  # Don't block on rate limit check failure

    def parse_repo_url(self, url: str) -> Tuple[str, str]:
        """Parse a GitHub repository URL into (owner, repo) tuple.

        Accepts:
          - github.com/user/repo
          - https://github.com/user/repo
          - user/repo

        Args:
            url: The raw URL or slug string.

        Returns:
            (owner, repo) tuple.

        Raises:
            InvalidRepoURLError: If the URL cannot be parsed.
        """
        url = url.strip().rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]

        m = _GITHUB_URL_RE.match(url)
        if m:
            return m.group(1), m.group(2)

        m = _SHORTHAND_RE.match(url)
        if m:
            return m.group(1), m.group(2)

        raise InvalidRepoURLError(
            f"Cannot parse repository URL: '{url}'. "
            "Expected formats: user/repo, github.com/user/repo, https://github.com/user/repo"
        )