"""
security.py — Security utilities for RepoRadar.

Handles token masking, environment validation, and log sanitization.
Never log raw tokens or license keys — always pass through these helpers first.
"""

import re
from typing import List


TOKEN_PATTERN = re.compile(r"(ghp_|gho_|github_pat_)[A-Za-z0-9_]+")
LICENSE_PATTERN = re.compile(r"RRADAR-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}")


def mask_token(token: str) -> str:
    """Mask a GitHub token for safe display in logs or output.

    Shows first 4 and last 4 characters with asterisks in between.
    Returns a fully masked string if the token is too short.

    Args:
        token: The raw token string to mask.

    Returns:
        Masked token string like 'ghp_****...****abcd'.
    """
    if not token or len(token) < 8:
        return "****"
    return f"{token[:4]}{'*' * (len(token) - 8)}{token[-4:]}"


def validate_env() -> List[str]:
    """Validate environment variables and return a list of warning strings.

    Does not raise exceptions — returns warnings as strings for display.

    Returns:
        List of human-readable warning messages. Empty list means all good.
    """
    import os

    warnings: List[str] = []

    github_token = os.environ.get("GITHUB_TOKEN", "")
    if not github_token:
        warnings.append("GITHUB_TOKEN is not set. API calls will be rate-limited to 60/hour.")
    elif not (
        github_token.startswith("ghp_")
        or github_token.startswith("gho_")
        or github_token.startswith("github_pat_")
    ):
        warnings.append(
            f"GITHUB_TOKEN format looks unusual (masked: {mask_token(github_token)}). "
            "Expected format: ghp_... or github_pat_..."
        )

    license_key = os.environ.get("LICENSE_KEY", "")
    if license_key:
        from validator import validate_license_key_format
        valid, reason = validate_license_key_format(license_key)
        if not valid:
            warnings.append(f"LICENSE_KEY format invalid: {reason}")

    cache_ttl = os.environ.get("CACHE_TTL_SECONDS", "3600")
    from validator import validate_cache_ttl
    valid, reason = validate_cache_ttl(cache_ttl)
    if not valid:
        warnings.append(f"CACHE_TTL_SECONDS invalid: {reason}")

    max_history = os.environ.get("MAX_HISTORY_ENTRIES", "500")
    from validator import validate_history_limit
    valid, reason = validate_history_limit(max_history)
    if not valid:
        warnings.append(f"MAX_HISTORY_ENTRIES invalid: {reason}")

    return warnings


def sanitize_for_log(text: str) -> str:
    """Remove tokens and license keys from a string before logging.

    Replaces any detected sensitive patterns with masked placeholders.

    Args:
        text: The raw text to sanitize.

    Returns:
        Sanitized string safe for logging.
    """
    text = TOKEN_PATTERN.sub("[TOKEN_REDACTED]", text)
    text = LICENSE_PATTERN.sub("[LICENSE_REDACTED]", text)
    return text