"""
cli/bulk.py — Bulk repository loading for RepoRadar CLI.

Supports loading repos from plain .txt files, package.json, and requirements.txt.
All loaders return a deduplicated list of valid repo URL strings.
"""

import json
import re
from typing import List

from validator import validate_repo_url, sanitize_repo_url

_REQUIREMENTS_COMMENT_RE = re.compile(r"^\s*#")
_REQUIREMENTS_EXTRAS_RE = re.compile(r"[>=<!;\[].+")


def load_repos_from_file(filepath: str) -> List[str]:
    """Load repository URLs from a plain text file (one per line).

    Skips blank lines, comment lines (starting with #), and invalid URLs.

    Args:
        filepath: Path to the .txt file.

    Returns:
        Deduplicated list of valid repository URL strings.
    """
    repos: List[str] = []
    seen = set()

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            cleaned = sanitize_repo_url(line)
            valid, _ = validate_repo_url(cleaned)
            if valid and cleaned not in seen:
                repos.append(cleaned)
                seen.add(cleaned)

    return repos


def load_repos_from_package_json(filepath: str) -> List[str]:
    """Extract GitHub repository URLs from a package.json dependencies block.

    Parses 'dependencies' and 'devDependencies'. Looks up each package
    on npm to find its GitHub repository URL (uses repository field if present
    in package.json itself, otherwise produces a best-effort slug).

    For packages that reference GitHub directly in their version string
    (e.g. 'github:user/repo' or 'user/repo'), those are extracted directly.

    Args:
        filepath: Path to the package.json file.

    Returns:
        List of GitHub repository URL strings found.
    """
    repos: List[str] = []
    seen: set = set()

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_deps: dict = {}
    all_deps.update(data.get("dependencies", {}))
    all_deps.update(data.get("devDependencies", {}))

    github_version_re = re.compile(
        r"^(?:github:)?([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+?)(?:#.+)?$"
    )

    for _pkg, version in all_deps.items():
        if not isinstance(version, str):
            continue
        m = github_version_re.match(version.strip())
        if m:
            slug = sanitize_repo_url(m.group(1))
            valid, _ = validate_repo_url(slug)
            if valid and slug not in seen:
                repos.append(slug)
                seen.add(slug)

    # Also check top-level 'repository' field
    repo_field = data.get("repository", {})
    if isinstance(repo_field, dict):
        repo_url = repo_field.get("url", "")
    elif isinstance(repo_field, str):
        repo_url = repo_field
    else:
        repo_url = ""

    if repo_url:
        # Strip git+ prefix and .git suffix
        repo_url = re.sub(r"^git\+", "", repo_url)
        repo_url = sanitize_repo_url(repo_url)
        valid, _ = validate_repo_url(repo_url)
        if valid and repo_url not in seen:
            repos.append(repo_url)
            seen.add(repo_url)

    return repos


def load_repos_from_requirements(filepath: str) -> List[str]:
    """Parse a Python requirements.txt and return package names as GitHub slugs.

    Strips version constraints, extras, and comments. Returns only entries
    that look like GitHub shorthand (user/repo) or GitHub URLs.

    Note: Standard PyPI package names (e.g. 'requests==2.31') are returned
    as bare package names for informational use — callers may want to
    resolve them via PyPI metadata if GitHub URLs are needed.

    Args:
        filepath: Path to requirements.txt.

    Returns:
        List of repository slugs or package names extracted from the file.
    """
    repos: List[str] = []
    seen: set = set()

    github_re = re.compile(
        r"(?:git\+)?(?:https?://)?github\.com/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+?)(?:\.git|@|#|/|$)"
    )

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # Skip comments and blank lines
            if not line or _REQUIREMENTS_COMMENT_RE.match(line):
                continue

            # Skip -r, -c, -f flags
            if line.startswith("-"):
                continue

            # Try to extract GitHub URL from line
            m = github_re.search(line)
            if m:
                slug = sanitize_repo_url(m.group(1))
                valid, _ = validate_repo_url(slug)
                if valid and slug not in seen:
                    repos.append(slug)
                    seen.add(slug)

    return repos