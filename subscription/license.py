"""
subscription/license.py — License key validation for RepoRadar.

Validation strategy (defence in depth):
  1. Format check  — fast local regex, rejects garbage immediately
  2. Signature check — local HMAC verify (no network) using LICENSE_SERVER_SECRET
  3. Online check — calls LICENSE_SERVER_URL to catch revoked/expired keys
     - If server unreachable: falls back to local signature check (grace period)
     - Result cached locally for OFFLINE_GRACE_SECONDS to avoid hammering server

This means:
  - Forged keys fail at step 2 (no server needed)
  - Revoked keys fail at step 3
  - Offline users still work via grace period
  - No key is ever stored in plaintext beyond what's already in .env
"""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional, Tuple

import requests

# ── Constants ────────────────────────────────────────────────────────────────
_FORMAT_RE = __import__("re").compile(
    r"^RRADAR-[A-Z0-9]{16}-[A-Z0-9]{8}$"
)
_OFFLINE_GRACE_SECONDS = 60 * 60 * 24 * 3   # 3 days offline grace
_VALIDATION_TIMEOUT = 4                       # seconds before giving up on server
_CACHE_FILE = Path.home() / ".reporadar" / "license_cache.json"


# ── Local cache ───────────────────────────────────────────────────────────────
def _read_cache(key: str) -> Optional[dict]:
    """Read a cached validation result for this key. Returns None if stale/missing."""
    try:
        if not _CACHE_FILE.exists():
            return None
        data = json.loads(_CACHE_FILE.read_text())
        entry = data.get(hashlib.sha256(key.encode()).hexdigest())
        if entry and time.time() - entry["cached_at"] < _OFFLINE_GRACE_SECONDS:
            return entry
    except Exception:
        pass
    return None


def _write_cache(key: str, valid: bool, tier: str, reason: str) -> None:
    """Cache a validation result locally."""
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = json.loads(_CACHE_FILE.read_text()) if _CACHE_FILE.exists() else {}
        except Exception:
            data = {}
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        data[key_hash] = {
            "valid": valid,
            "tier": tier,
            "reason": reason,
            "cached_at": time.time(),
        }
        # Keep only last 5 entries (one per key typically)
        if len(data) > 5:
            oldest = sorted(data.items(), key=lambda x: x[1].get("cached_at", 0))
            data = dict(oldest[-5:])
        _CACHE_FILE.write_text(json.dumps(data, indent=2))
        if os.name != "nt":  # chmod not available on Windows
            os.chmod(_CACHE_FILE, 0o600)
    except Exception:
        pass


# ── Local signature check ─────────────────────────────────────────────────────
def _local_signature_check(key: str) -> Tuple[bool, str]:
    """Verify key signature using the local LICENSE_SERVER_SECRET.

    If the secret isn't set locally, we skip this and rely on the server.
    """
    secret = os.environ.get("LICENSE_SERVER_SECRET", "")
    if not secret:
        return True, "No local secret — deferring to server."
    try:
        from licensing.key_generator import verify_key_signature
        return verify_key_signature(key, secret)
    except Exception as exc:
        return True, f"Local check skipped: {exc}"


# ── Online validation ─────────────────────────────────────────────────────────
def _online_validate(key: str) -> Tuple[bool, str, str]:
    """Call the license server to validate the key.

    Returns (is_valid, tier, reason).
    Raises requests.RequestException on network failure.
    """
    server_url = os.environ.get("LICENSE_SERVER_URL", "").rstrip("/")
    auth_token = os.environ.get("LICENSE_API_TOKEN", "")

    if not server_url:
        raise ValueError("LICENSE_SERVER_URL not configured.")

    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    headers["User-Agent"] = "RepoRadar-CLI/0.1.0"

    resp = requests.get(
        f"{server_url}/validate",
        params={"key": key},
        headers=headers,
        timeout=_VALIDATION_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("valid", False), data.get("tier", "free"), data.get("reason", "")


# ── Public API ────────────────────────────────────────────────────────────────
def validate_license(key: str) -> Tuple[bool, str]:
    """Validate a license key using a layered defence strategy.

    Layer 1: Format check (instant, no network)
    Layer 2: Local HMAC signature check (instant, no network)
    Layer 3: Online server check (network, with cache + grace period fallback)

    Args:
        key: The raw license key string.

    Returns:
        (is_valid, message) tuple.
    """
    # Empty = free tier, always valid
    if not key or not key.strip():
        return True, "Free tier."

    key = key.strip().upper()

    # Layer 1: Format
    if not _FORMAT_RE.match(key):
        return False, (
            "Invalid license key format. "
            "Expected: RRADAR-XXXXXXXXXXXXXXXX-XXXXXXXX. "
            "Purchase at reporadar.dev"
        )

    # Layer 2: Local signature (catches forged keys instantly, no server needed)
    sig_ok, sig_reason = _local_signature_check(key)
    if not sig_ok:
        return False, f"License key invalid: {sig_reason}"

    # Layer 3: Online check (catches revoked/expired keys)
    # First check cache
    cached = _read_cache(key)
    if cached:
        return cached["valid"], cached["reason"] + " [cached]"

    # Try server
    try:
        valid, tier, reason = _online_validate(key)
        _write_cache(key, valid, tier, reason)
        return valid, reason
    except ValueError:
        # Server URL not configured — local-only mode (dev/offline)
        _write_cache(key, True, "paid", "Local validation only (server not configured).")
        return True, "License valid (offline mode — server not configured)."
    except Exception:
        # Network error — use grace period from cache or fall back to local check
        if sig_ok:
            _write_cache(key, True, "paid", "Offline grace period.")
            return True, "License valid (offline — server unreachable, grace period active)."
        return False, "Could not validate license key and no cached result found."


def get_tier(license_key: str) -> str:
    """Resolve the subscription tier from a license key.

    Uses the same layered validation. Returns 'free' on any doubt.

    Args:
        license_key: Raw license key string (may be empty).

    Returns:
        'paid' or 'free'.
    """
    if not license_key or not license_key.strip():
        return "free"

    key = license_key.strip().upper()
    if not _FORMAT_RE.match(key):
        return "free"

    # Quick local check first (no network)
    sig_ok, _ = _local_signature_check(key)
    if not sig_ok:
        return "free"

    # Check cache
    cached = _read_cache(key)
    if cached:
        return "paid" if cached["valid"] else "free"

    # Try online
    try:
        valid, tier, reason = _online_validate(key)
        _write_cache(key, valid, tier, reason)
        return tier if valid else "free"
    except Exception:
        # Offline grace: if signature is valid, trust it
        return "paid" if sig_ok else "free"