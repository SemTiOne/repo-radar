"""
tests/test_cache.py — Tests for cache/file_cache.py
"""

import time
import pytest

from cache.file_cache import FileCache


@pytest.fixture()
def cache(tmp_path):
    return FileCache(cache_dir=str(tmp_path), ttl_seconds=60)


class TestFileCache:
    def test_get_returns_none_for_missing_key(self, cache):
        assert cache.get("nonexistent_key") is None

    def test_set_then_get_returns_data(self, cache):
        data = {"score": 75.0, "verdict": "alive"}
        cache.set("key1", data)
        result = cache.get("key1")
        assert result == data

    def test_get_returns_none_for_expired_entry(self, tmp_path):
        short_cache = FileCache(cache_dir=str(tmp_path / "exp"), ttl_seconds=1)
        short_cache.set("k", {"val": 1})
        time.sleep(1.1)
        assert short_cache.get("k") is None

    def test_delete_removes_entry(self, cache):
        cache.set("del_key", {"x": 1})
        cache.delete("del_key")
        assert cache.get("del_key") is None

    def test_clear_all_returns_correct_count(self, cache):
        cache.set("k1", {"a": 1})
        cache.set("k2", {"b": 2})
        cache.set("k3", {"c": 3})
        count = cache.clear_all()
        assert count == 3

    def test_clear_all_removes_all_entries(self, cache):
        cache.set("k1", {"a": 1})
        cache.set("k2", {"b": 2})
        cache.clear_all()
        assert cache.get("k1") is None
        assert cache.get("k2") is None

    def test_get_stats_returns_correct_structure(self, cache):
        cache.set("k1", {"a": 1})
        cache.set("k2", {"b": 2})
        stats = cache.get_stats()
        assert stats["total_entries"] == 2
        assert stats["total_size_bytes"] > 0
        assert "cache_dir" in stats
        assert "oldest_entry_age_seconds" in stats

    def test_make_key_is_deterministic(self, cache):
        k1 = cache.make_key("user", "repo")
        k2 = cache.make_key("user", "repo")
        assert k1 == k2

    def test_make_key_differs_for_different_repos(self, cache):
        k1 = cache.make_key("user", "repo-a")
        k2 = cache.make_key("user", "repo-b")
        assert k1 != k2

    def test_make_key_case_insensitive(self, cache):
        k1 = cache.make_key("User", "Repo")
        k2 = cache.make_key("user", "repo")
        assert k1 == k2