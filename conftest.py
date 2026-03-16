"""
conftest.py — Pytest configuration for RepoRadar.

Adds the project root to sys.path so all modules (core, cli, cache, etc.)
are importable when running: pytest tests/
"""

import sys
from pathlib import Path

# Insert project root at the front of sys.path
sys.path.insert(0, str(Path(__file__).parent))