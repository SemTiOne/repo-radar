"""
config.py — Loads configuration from environment variables and .env file.
All application-wide defaults are defined here.
"""

import os
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv

load_dotenv()


def load_config() -> Dict[str, Any]:
    """Load and return the full application configuration dictionary.

    Reads from environment variables (with .env support via python-dotenv).
    Returns a dict with all config keys and their resolved values.
    """
    return {
        "GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN", None),
        "CACHE_DIR": os.environ.get("CACHE_DIR", str(Path.home() / ".reporadar" / "cache")),
        "CACHE_TTL_SECONDS": int(os.environ.get("CACHE_TTL_SECONDS", 3600)),
        "LICENSE_KEY": os.environ.get("LICENSE_KEY", ""),
        "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO"),
        "HISTORY_PATH": os.environ.get("HISTORY_PATH", str(Path.home() / ".reporadar" / "history.json")),
        "MAX_HISTORY_ENTRIES": int(os.environ.get("MAX_HISTORY_ENTRIES", 500)),
    }