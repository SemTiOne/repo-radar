"""
tests/conftest.py — Session-wide fixtures for RepoRadar tests.

Uses monkeypatch to set the HISTORY_PATH environment variable for each test,
ensuring every test gets its own fresh history file with zero cross-contamination.
This approach bypasses all import-caching and mock-object issues.
"""
import os
import pytest


@pytest.fixture(autouse=True)
def isolate_history(tmp_path, monkeypatch):
    """
    Auto-use: redirect HISTORY_PATH env var so load_config() returns a
    per-test temp path. Works regardless of .env, import caching, or
    mock-object resolution order.
    
    Returns the Path to the temp history file for tests that need to inspect it.
    """
    history_file = tmp_path / "history.json"
    monkeypatch.setenv("HISTORY_PATH", str(history_file))
    monkeypatch.setenv("MAX_HISTORY_ENTRIES", "500")
    yield history_file