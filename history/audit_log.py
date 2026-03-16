"""
history/audit_log.py — Local history and audit logging for RepoRadar.

History is stored in ~/.reporadar/history.json as a JSON file.
The file is chmod 600 on every write (Unix/macOS).
Oldest entries are purged when MAX_HISTORY_ENTRIES is exceeded.
"""

import hashlib
import json
import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional





def _history_path() -> Path:
    """Resolve the history file path from config at call time (never cached)."""
    from config import load_config
    return Path(load_config()["HISTORY_PATH"]).expanduser()


def _max_entries() -> int:
    """Resolve the max entries limit from config at call time (never cached)."""
    from config import load_config
    return int(load_config()["MAX_HISTORY_ENTRIES"])


def load_history() -> dict:
    """Load the history file from disk.

    Creates the file with empty structure if it does not exist.

    Returns:
        Dict with 'version' and 'entries' keys.
    """
    path = _history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        save_history({"version": "1.0", "entries": []})
        return {"version": "1.0", "entries": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "entries" not in data:
            data["entries"] = []
        if "version" not in data:
            data["version"] = "1.0"
        return data
    except Exception:
        return {"version": "1.0", "entries": []}


def save_history(history: dict) -> None:
    """Write the history dict to disk and enforce permissions.

    Purges oldest entries if over MAX_HISTORY_ENTRIES before writing.
    Applies chmod 600 on Unix/macOS.

    Args:
        history: The full history dict to persist.
    """
    path = _history_path()
    max_e = _max_entries()
    path.parent.mkdir(parents=True, exist_ok=True)

    entries = history.get("entries", [])
    if len(entries) > max_e:
        entries = sorted(entries, key=lambda e: e.get("timestamp", ""), reverse=True)
        history["entries"] = entries[:max_e]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    if platform.system() in ("Linux", "Darwin"):
        os.chmod(path, 0o600)


def record_check(
    repo: str,
    url: str,
    score: float,
    score_label: str,
    verdict: str,
    tier: str,
    signals_run: List[str],
    cached: bool,
    command: str,
    duration_ms: int,
) -> None:
    """Append a new analysis result to the history log."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{datetime.now(timezone.utc).microsecond:06d}Z"
    uid_raw = f"{repo}{timestamp}".encode()
    entry_id = hashlib.md5(uid_raw).hexdigest()[:8]

    entry = {
        "id": entry_id,
        "repo": repo,
        "url": url,
        "score": round(score, 2),
        "score_label": score_label,
        "verdict": verdict,
        "tier": tier,
        "signals_run": signals_run,
        "timestamp": timestamp,
        "cached": cached,
        "command": command,
        "duration_ms": duration_ms,
    }

    history = load_history()
    history["entries"].append(entry)
    save_history(history)


def get_history(repo: Optional[str] = None, limit: int = 20) -> List[dict]:
    """Retrieve history entries, optionally filtered by repo, newest first."""
    history = load_history()
    entries = history.get("entries", [])

    if repo:
        repo_norm = repo.lower().strip("/")
        entries = [e for e in entries if e.get("repo", "").lower() == repo_norm]

    entries = sorted(entries, key=lambda e: e.get("timestamp", ""), reverse=True)
    return entries[:limit]


def clear_history() -> int:
    """Delete all history entries. Returns count deleted."""
    history = load_history()
    count = len(history.get("entries", []))
    history["entries"] = []
    save_history(history)
    return count


def get_history_stats() -> dict:
    """Compute summary statistics for all history entries."""
    history = load_history()
    entries = history.get("entries", [])

    if not entries:
        return {
            "total_entries": 0,
            "unique_repos": 0,
            "oldest_entry": "",
            "newest_entry": "",
            "most_checked_repo": "",
            "avg_score": 0.0,
        }

    timestamps = sorted(e.get("timestamp", "") for e in entries if e.get("timestamp"))
    repo_counts: Dict[str, int] = {}
    for e in entries:
        r = e.get("repo", "")
        repo_counts[r] = repo_counts.get(r, 0) + 1

    most_checked = max(repo_counts, key=lambda r: repo_counts[r]) if repo_counts else ""
    scores = [e["score"] for e in entries if isinstance(e.get("score"), (int, float))]
    avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0

    return {
        "total_entries": len(entries),
        "unique_repos": len(set(e.get("repo", "") for e in entries)),
        "oldest_entry": timestamps[0] if timestamps else "",
        "newest_entry": timestamps[-1] if timestamps else "",
        "most_checked_repo": most_checked,
        "avg_score": avg_score,
    }


def get_trend(repo: str) -> Optional[dict]:
    """Compute score trend for a repo. Returns None if fewer than 2 entries."""
    entries = get_history(repo=repo, limit=500)
    entries = sorted(entries, key=lambda e: e.get("timestamp", ""))

    if len(entries) < 2:
        return None

    scores = [e["score"] for e in entries if isinstance(e.get("score"), (int, float))]
    if len(scores) < 2:
        return None

    score_change = round(scores[-1] - scores[0], 2)
    if score_change >= 2.0:
        trend = "improving"
    elif score_change <= -2.0:
        trend = "declining"
    else:
        trend = "stable"

    return {
        "entries": entries,
        "trend": trend,
        "score_change": score_change,
    }