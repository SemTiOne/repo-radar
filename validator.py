"""
validator.py — Single source of truth for all input validation in RepoRadar.

All validation functions return Tuple[bool, str] and never raise exceptions.
Do not duplicate validation logic elsewhere in the codebase.
"""

import os
import re
from typing import Any, Tuple


VALID_OUTPUT_FORMATS = {"text", "json", "markdown"}
GITHUB_URL_PATTERN = re.compile(
    r"^(https?://)?(www\.)?github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(/|\.git)?$"
)
SHORTHAND_PATTERN = re.compile(r"^([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(/|\.git)?$")
LICENSE_KEY_PATTERN = re.compile(r"^RRADAR-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$")


def validate_repo_url(url: str) -> Tuple[bool, str]:
    """Validate that a URL points to a GitHub repository.

    Accepts:
      - github.com/user/repo
      - https://github.com/user/repo
      - user/repo

    Returns (True, "") on success or (False, reason) on failure.
    """
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string."
    url = url.strip()
    if GITHUB_URL_PATTERN.match(url):
        return True, ""
    if SHORTHAND_PATTERN.match(url):
        return True, ""
    return False, f"Invalid GitHub repository URL: '{url}'. Expected formats: user/repo, github.com/user/repo, or https://github.com/user/repo"


def validate_output_format(value: str) -> Tuple[bool, str]:
    """Validate the --format CLI option value.

    Returns (True, "") if valid, (False, reason) otherwise.
    """
    if value in VALID_OUTPUT_FORMATS:
        return True, ""
    return False, f"Invalid format '{value}'. Must be one of: {', '.join(sorted(VALID_OUTPUT_FORMATS))}"


def validate_bulk_file(filepath: str) -> Tuple[bool, str]:
    """Validate that a bulk input file exists and is readable.

    Returns (True, "") if valid, (False, reason) otherwise.
    """
    if not filepath or not isinstance(filepath, str):
        return False, "File path must be a non-empty string."
    if not os.path.exists(filepath):
        return False, f"File not found: '{filepath}'"
    if not os.path.isfile(filepath):
        return False, f"Path is not a file: '{filepath}'"
    if not os.access(filepath, os.R_OK):
        return False, f"File is not readable: '{filepath}'"
    return True, ""


def validate_license_key_format(key: str) -> Tuple[bool, str]:
    """Validate the format of a license key.

    Accepts empty string (free tier) or RRADAR-XXXX-XXXX-XXXX format.
    Returns (True, "") if valid, (False, reason) otherwise.
    """
    if key == "" or key is None:
        return True, ""
    if LICENSE_KEY_PATTERN.match(str(key)):
        return True, ""
    return False, "Invalid license key format. Expected: RRADAR-XXXX-XXXX-XXXX (alphanumeric segments)."


def validate_cache_ttl(value: Any) -> Tuple[bool, str]:
    """Validate a cache TTL value (must be a positive integer).

    Returns (True, "") if valid, (False, reason) otherwise.
    """
    try:
        ttl = int(value)
        if ttl <= 0:
            return False, "CACHE_TTL_SECONDS must be a positive integer."
        return True, ""
    except (TypeError, ValueError):
        return False, f"CACHE_TTL_SECONDS must be an integer, got: {value!r}"


def validate_history_limit(value: Any) -> Tuple[bool, str]:
    """Validate a history limit (must be an integer between 1 and 500).

    Returns (True, "") if valid, (False, reason) otherwise.
    """
    try:
        limit = int(value)
        if 1 <= limit <= 500:
            return True, ""
        return False, f"History limit must be between 1 and 500, got: {limit}"
    except (TypeError, ValueError):
        return False, f"History limit must be an integer, got: {value!r}"


def validate_bulk_count(count: int, tier: str) -> Tuple[bool, str]:
    """Validate the number of repos in a bulk check for the given tier.

    Free tier: bulk not allowed.
    Paid tier: max 50 repos.
    Returns (True, "") if valid, (False, reason) otherwise.
    """
    if tier != "paid":
        return False, "Bulk checking requires a paid subscription. Upgrade at reporadar.dev"
    if count > 50:
        return False, f"Bulk check is limited to 50 repositories per run (got {count})."
    if count < 1:
        return False, "No repositories provided for bulk check."
    return True, ""


def sanitize_repo_url(url: str) -> str:
    """Normalize a repository URL by stripping trailing slashes and .git suffix.

    Returns the cleaned URL string.
    """
    if not url:
        return url
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    return url