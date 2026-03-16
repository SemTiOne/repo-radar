"""
tests/test_github_client.py — Tests for core/github_client.py
"""

from unittest.mock import MagicMock, patch, call
import pytest
import requests

from core.github_client import (
    GitHubClient,
    RepoNotFoundError,
    GitHubAPIError,
    RateLimitExceededError,
    InvalidRepoURLError,
)


class TestParseRepoUrl:
    client = GitHubClient()

    def test_shorthand(self):
        owner, repo = self.client.parse_repo_url("user/repo")
        assert owner == "user"
        assert repo == "repo"

    def test_github_dot_com(self):
        owner, repo = self.client.parse_repo_url("github.com/user/repo")
        assert owner == "user"
        assert repo == "repo"

    def test_https_url(self):
        owner, repo = self.client.parse_repo_url("https://github.com/user/repo")
        assert owner == "user"
        assert repo == "repo"

    def test_https_url_with_git_suffix(self):
        owner, repo = self.client.parse_repo_url("https://github.com/user/repo.git")
        assert owner == "user"
        assert repo == "repo"

    def test_trailing_slash(self):
        owner, repo = self.client.parse_repo_url("user/repo/")
        assert owner == "user"
        assert repo == "repo"

    def test_invalid_url_raises(self):
        with pytest.raises(InvalidRepoURLError):
            self.client.parse_repo_url("not-a-valid-url")

    def test_plain_domain_raises(self):
        with pytest.raises(InvalidRepoURLError):
            self.client.parse_repo_url("github.com")

    def test_empty_string_raises(self):
        with pytest.raises(InvalidRepoURLError):
            self.client.parse_repo_url("")


class TestGetRepo:
    def test_404_raises_repo_not_found(self):
        client = GitHubClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.ok = False
        mock_resp.text = "Not Found"

        with patch.object(client.session, "get", return_value=mock_resp):
            with pytest.raises(RepoNotFoundError):
                client.get_repo("user", "missing")

    def test_success_returns_dict(self):
        client = GitHubClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_resp.json.return_value = {"name": "repo", "archived": False}

        with patch.object(client.session, "get", return_value=mock_resp):
            result = client.get_repo("user", "repo")
        assert result["name"] == "repo"

    def test_rate_limit_403_raises(self):
        client = GitHubClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.ok = False
        mock_resp.text = "API rate limit exceeded"

        with patch.object(client.session, "get", return_value=mock_resp):
            with pytest.raises(RateLimitExceededError):
                client.get_repo("user", "repo")


class Test202RetryLogic:
    def test_retries_on_202_up_to_3_times(self):
        client = GitHubClient()

        # 3x 202, then success
        resp_202 = MagicMock()
        resp_202.status_code = 202
        resp_202.ok = True

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.ok = True
        resp_200.json.return_value = [{"total": 5}]

        call_count = {"n": 0}

        def fake_get(url, **kwargs):
            call_count["n"] += 1
            if call_count["n"] <= 2:
                return resp_202
            return resp_200

        with patch.object(client.session, "get", side_effect=fake_get):
            with patch("time.sleep"):
                result = client._get_with_202_retry("/test", max_retries=3, delay=0)
        assert result == [{"total": 5}]
        assert call_count["n"] == 3

    def test_raises_after_max_retries_of_202(self):
        client = GitHubClient()

        resp_202 = MagicMock()
        resp_202.status_code = 202
        resp_202.ok = True

        with patch.object(client.session, "get", return_value=resp_202):
            with patch("time.sleep"):
                with pytest.raises(GitHubAPIError):
                    client._get_with_202_retry("/test", max_retries=3, delay=0)


class TestCheckRateLimit:
    def test_raises_when_remaining_zero(self):
        client = GitHubClient()
        client.get_rate_limit = MagicMock(return_value={
            "resources": {"core": {"remaining": 0, "reset": 9999999999}}
        })
        with pytest.raises(RateLimitExceededError):
            client.check_rate_limit_before_call()

    def test_no_raise_when_remaining_positive(self):
        client = GitHubClient()
        client.get_rate_limit = MagicMock(return_value={
            "resources": {"core": {"remaining": 500, "reset": 9999999999}}
        })
        # Should not raise
        client.check_rate_limit_before_call()