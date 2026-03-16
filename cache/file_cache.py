"""
cache/file_cache.py — Local file-based cache for GitHub API analysis results.

Cache entries are stored as JSON files keyed by owner/repo slug.
Supports TTL-based expiry, stats reporting, and full cache clearing.
"""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional


class FileCache:
    """File-based key-value cache with TTL expiry for RepoRadar analysis results."""

    def __init__(self, cache_dir: str, ttl_seconds: int) -> None:
        """Initialize the cache.

        Args:
            cache_dir: Directory path for storing cache files.
            ttl_seconds: Time-to-live in seconds for each cache entry.
        """
        self.cache_dir = Path(cache_dir).expanduser()
        self.ttl_seconds = ttl_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def make_key(self, owner: str, repo: str) -> str:
        """Generate a filesystem-safe cache key for an owner/repo pair.

        Args:
            owner: GitHub username or org name.
            repo: Repository name.

        Returns:
            A hex string key derived from owner/repo.
        """
        raw = f"{owner.lower()}/{repo.lower()}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _key_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(self, key: str) -> Optional[dict]:
        """Retrieve a cached value if it exists and has not expired.

        Args:
            key: Cache key string.

        Returns:
            Cached dict, or None if missing or expired.
        """
        path = self._key_path(key)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                entry = json.load(f)
            cached_at = entry.get("_cached_at", 0)
            if time.time() - cached_at > self.ttl_seconds:
                path.unlink(missing_ok=True)
                return None
            return entry.get("data")
        except Exception:
            return None

    def set(self, key: str, data: dict) -> None:
        """Store a value in the cache with the current timestamp.

        Args:
            key: Cache key string.
            data: The dict to store.
        """
        path = self._key_path(key)
        entry = {"_cached_at": time.time(), "data": data}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2)

    def delete(self, key: str) -> None:
        """Remove a single cache entry by key.

        Args:
            key: Cache key string.
        """
        path = self._key_path(key)
        if path.exists():
            path.unlink()

    def clear_all(self) -> int:
        """Delete all cache files in the cache directory.

        Returns:
            Number of cache files deleted.
        """
        count = 0
        for path in self.cache_dir.glob("*.json"):
            try:
                path.unlink()
                count += 1
            except Exception:
                pass
        return count

    def get_stats(self) -> dict:
        """Return statistics about the current cache state.

        Returns:
            Dict with keys: total_entries (int), total_size_bytes (int),
            oldest_entry_age_seconds (float), cache_dir (str).
        """
        entries = list(self.cache_dir.glob("*.json"))
        total_size = sum(p.stat().st_size for p in entries if p.exists())
        oldest_age = 0.0
        for p in entries:
            try:
                with open(p, "r", encoding="utf-8") as f:
                    entry = json.load(f)
                age = time.time() - entry.get("_cached_at", time.time())
                if age > oldest_age:
                    oldest_age = age
            except Exception:
                pass
        return {
            "total_entries": len(entries),
            "total_size_bytes": total_size,
            "oldest_entry_age_seconds": oldest_age,
            "cache_dir": str(self.cache_dir),
        }