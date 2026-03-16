"""
tests/test_validator.py — Tests for validator.py
"""

import os
import tempfile
import pytest

from validator import (
    validate_repo_url,
    validate_output_format,
    validate_bulk_file,
    validate_license_key_format,
    validate_cache_ttl,
    validate_history_limit,
    validate_bulk_count,
    sanitize_repo_url,
)


class TestValidateRepoUrl:
    def test_shorthand_valid(self):
        ok, _ = validate_repo_url("user/repo")
        assert ok is True

    def test_github_dot_com_valid(self):
        ok, _ = validate_repo_url("github.com/user/repo")
        assert ok is True

    def test_https_url_valid(self):
        ok, _ = validate_repo_url("https://github.com/user/repo")
        assert ok is True

    def test_url_with_git_suffix_valid(self):
        ok, _ = validate_repo_url("https://github.com/user/repo.git")
        assert ok is True

    def test_non_github_url_invalid(self):
        ok, msg = validate_repo_url("https://gitlab.com/user/repo")
        assert ok is False
        assert msg != ""

    def test_plain_string_invalid(self):
        ok, _ = validate_repo_url("notarepo")
        assert ok is False

    def test_empty_string_invalid(self):
        ok, _ = validate_repo_url("")
        assert ok is False

    def test_none_invalid(self):
        ok, _ = validate_repo_url(None)
        assert ok is False


class TestValidateOutputFormat:
    def test_text_valid(self):
        ok, _ = validate_output_format("text")
        assert ok is True

    def test_json_valid(self):
        ok, _ = validate_output_format("json")
        assert ok is True

    def test_markdown_valid(self):
        ok, _ = validate_output_format("markdown")
        assert ok is True

    def test_unknown_invalid(self):
        ok, msg = validate_output_format("xml")
        assert ok is False
        assert "xml" in msg.lower() or "invalid" in msg.lower()

    def test_empty_invalid(self):
        ok, _ = validate_output_format("")
        assert ok is False


class TestValidateBulkFile:
    def test_existing_file_valid(self, tmp_path):
        f = tmp_path / "repos.txt"
        f.write_text("user/repo\n")
        ok, _ = validate_bulk_file(str(f))
        assert ok is True

    def test_missing_file_invalid(self):
        ok, msg = validate_bulk_file("/nonexistent/path/file.txt")
        assert ok is False
        assert "not found" in msg.lower() or "File not found" in msg

    def test_empty_path_invalid(self):
        ok, _ = validate_bulk_file("")
        assert ok is False


class TestValidateLicenseKeyFormat:
    def test_empty_string_valid(self):
        ok, _ = validate_license_key_format("")
        assert ok is True

    def test_none_valid(self):
        ok, _ = validate_license_key_format(None)
        assert ok is True

    def test_valid_format(self):
        ok, _ = validate_license_key_format("RRADAR-ABCD-1234-XY90")
        assert ok is True

    def test_lowercase_invalid(self):
        ok, _ = validate_license_key_format("rradar-abcd-1234-xy90")
        assert ok is False

    def test_wrong_prefix_invalid(self):
        ok, _ = validate_license_key_format("RADAR-ABCD-1234-XY90")
        assert ok is False

    def test_too_short_invalid(self):
        ok, _ = validate_license_key_format("RRADAR-AB-12-XY")
        assert ok is False


class TestValidateCacheTtl:
    def test_positive_int_valid(self):
        ok, _ = validate_cache_ttl(3600)
        assert ok is True

    def test_string_int_valid(self):
        ok, _ = validate_cache_ttl("7200")
        assert ok is True

    def test_zero_invalid(self):
        ok, _ = validate_cache_ttl(0)
        assert ok is False

    def test_negative_invalid(self):
        ok, _ = validate_cache_ttl(-1)
        assert ok is False

    def test_non_numeric_invalid(self):
        ok, _ = validate_cache_ttl("abc")
        assert ok is False


class TestValidateHistoryLimit:
    def test_min_1_valid(self):
        ok, _ = validate_history_limit(1)
        assert ok is True

    def test_max_500_valid(self):
        ok, _ = validate_history_limit(500)
        assert ok is True

    def test_zero_invalid(self):
        ok, _ = validate_history_limit(0)
        assert ok is False

    def test_501_invalid(self):
        ok, _ = validate_history_limit(501)
        assert ok is False

    def test_string_number_valid(self):
        ok, _ = validate_history_limit("100")
        assert ok is True

    def test_non_numeric_invalid(self):
        ok, _ = validate_history_limit("abc")
        assert ok is False


class TestValidateBulkCount:
    def test_free_tier_rejected(self):
        ok, msg = validate_bulk_count(5, "free")
        assert ok is False
        assert "paid" in msg.lower()

    def test_paid_tier_under_50_valid(self):
        ok, _ = validate_bulk_count(50, "paid")
        assert ok is True

    def test_paid_tier_over_50_invalid(self):
        ok, msg = validate_bulk_count(51, "paid")
        assert ok is False
        assert "50" in msg

    def test_zero_repos_invalid(self):
        ok, _ = validate_bulk_count(0, "paid")
        assert ok is False


class TestSanitizeRepoUrl:
    def test_strips_trailing_slash(self):
        assert sanitize_repo_url("user/repo/") == "user/repo"

    def test_strips_git_suffix(self):
        assert sanitize_repo_url("user/repo.git") == "user/repo"

    def test_strips_both(self):
        assert sanitize_repo_url("https://github.com/user/repo.git/") == "https://github.com/user/repo"

    def test_no_change_needed(self):
        assert sanitize_repo_url("user/repo") == "user/repo"

    def test_empty_string(self):
        assert sanitize_repo_url("") == ""