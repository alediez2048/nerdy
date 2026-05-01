# Ad-Ops-Autopilot — Clerk JWKS key fetcher (PG-01)
import time
import logging

import httpx
from jose import jwk

from app.config import settings

logger = logging.getLogger(__name__)

# In-memory JWKS cache: {kid: (key_object, fetched_at)}
_jwks_cache: dict[str, tuple[object, float]] = {}
_CACHE_TTL_SECONDS = 3600  # 1 hour


def _fetch_jwks() -> list[dict]:
    """Fetch JWKS key set from Clerk."""
    url = settings.CLERK_JWKS_URL
    if not url:
        raise RuntimeError("CLERK_JWKS_URL is not configured")
    try:
        resp = httpx.get(url, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        return data.get("keys", [])
    except httpx.HTTPError as e:
        logger.error("Failed to fetch JWKS from %s: %s", url, e)
        raise RuntimeError(f"Failed to fetch JWKS: {e}") from e


def get_clerk_public_key(kid: str):
    """Return the RSA public key for the given kid, using a 1-hour cache."""
    now = time.time()

    # Check cache
    if kid in _jwks_cache:
        key_obj, fetched_at = _jwks_cache[kid]
        if now - fetched_at < _CACHE_TTL_SECONDS:
            return key_obj

    # Fetch fresh keys
    keys = _fetch_jwks()
    for key_data in keys:
        k = key_data.get("kid")
        if k:
            _jwks_cache[k] = (jwk.construct(key_data), now)

    if kid in _jwks_cache:
        return _jwks_cache[kid][0]

    raise ValueError(f"No JWKS key found for kid={kid}")
