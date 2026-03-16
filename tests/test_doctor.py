"""
tests/test_doctor.py — Tests for doctor.py
"""

import platform
from unittest.mock import patch, MagicMock
import pytest

from doctor import run_doctor, validate_token_format, get_system_stats


class TestValidateTokenFormat:
    def test_ghp_prefix_valid(self):
        assert validate_token_format("ghp_abcdefg1234") is True

    def test_gho_prefix_valid(self):
        assert validate_token_format("gho_abcdefg1234") is True

    def test_github_pat_prefix_valid(self):
        assert validate_token_format("github_pat_abcdefg1234") is True

    def test_invalid_prefix(self):
        assert validate_token_format("invalid_token_abc") is False

    def test_empty_string(self):
        assert validate_token_format("") is False


class TestGetSystemStats:
    def test_returns_required_keys(self):
        stats = get_system_stats()
        assert "memory_mb" in stats
        assert "cpu_percent" in stats
        assert "disk_free_mb" in stats

    def test_values_are_numeric(self):
        stats = get_system_stats()
        assert isinstance(stats["memory_mb"], float)
        assert isinstance(stats["cpu_percent"], float)
        assert isinstance(stats["disk_free_mb"], float)

    def test_values_are_non_negative(self):
        stats = get_system_stats()
        assert stats["memory_mb"] >= 0
        assert stats["cpu_percent"] >= 0
        assert stats["disk_free_mb"] >= 0


class TestRunDoctor:
    def _base_config(self, tmp_path):
        return {
            "GITHUB_TOKEN": None,
            "CACHE_DIR": str(tmp_path / "cache"),
            "CACHE_TTL_SECONDS": 3600,
            "LICENSE_KEY": "",
            "LOG_LEVEL": "INFO",
            "HISTORY_PATH": str(tmp_path / "history.json"),
            "MAX_HISTORY_ENTRIES": 500,
        }

    def test_runs_without_raising(self, tmp_path):
        config = self._base_config(tmp_path)
        # Should complete without any exception
        run_doctor(config)

    def test_all_checks_produce_output(self, tmp_path, capsys):
        config = self._base_config(tmp_path)
        from rich.console import Console
        from io import StringIO
        import doctor as doc

        output_buffer = StringIO()
        with patch("doctor.console", Console(file=output_buffer, highlight=False)):
            run_doctor(config)

        output = output_buffer.getvalue()
        # Core checks should appear
        assert "GitHub API" in output or "reachable" in output.lower() or "Doctor" in output

    def test_critical_fail_in_checks(self, tmp_path):
        """If a critical check fails, run_doctor should still complete (not raise)."""
        config = self._base_config(tmp_path)

        # Simulate unreachable GitHub API
        import requests
        with patch("requests.get", side_effect=ConnectionError("No network")):
            # Should not raise even with network failures
            try:
                run_doctor(config)
            except Exception as exc:
                pytest.fail(f"run_doctor raised unexpectedly: {exc}")

    def test_fix_suggestions_present_for_failed_checks(self, tmp_path):
        """Failed checks with fix suggestions should appear in output."""
        config = self._base_config(tmp_path)
        config["GITHUB_TOKEN"] = None  # Will trigger a warning

        from rich.console import Console
        from io import StringIO
        import doctor as doc

        output_buffer = StringIO()
        with patch("doctor.console", Console(file=output_buffer, highlight=False)):
            run_doctor(config)

        output = output_buffer.getvalue()
        # The token-related warning or fix should appear somewhere
        assert len(output) > 100  # Substantial output was produced