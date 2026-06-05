"""Per-provider auth probes used when a user saves a key.

Each probe makes the cheapest authenticated call we can find and raises
``KeyRejected`` if the provider returns an auth-style error. Other errors
(network, provider outage) propagate as ``ProbeUnavailable`` so the route
can surface a 503 instead of misleading the user that their key was bad.
"""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class KeyRejected(ValueError):
    """The provider explicitly rejected the supplied key."""


class ProbeUnavailable(RuntimeError):
    """We couldn't reach the provider to validate the key."""


PROVIDERS = ("gemini", "fal", "kling")


def probe(provider: str, api_key: str) -> None:
    """Dispatch to the per-provider probe. Raises on failure."""
    if not api_key or not api_key.strip():
        raise KeyRejected("Empty API key")
    fn = {
        "gemini": _probe_gemini,
        "fal": _probe_fal,
        "kling": _probe_kling,
    }.get(provider)
    if fn is None:
        raise ValueError(f"Unsupported provider: {provider}")
    fn(api_key.strip())


def _probe_gemini(api_key: str) -> None:
    """Validate via ``models.list`` — no token cost, fails fast on bad key."""
    try:
        from google import genai
    except ImportError as e:
        raise ProbeUnavailable(f"google-genai not installed: {e}") from e
    try:
        client = genai.Client(api_key=api_key)
        # Force iteration so we actually hit the API.
        next(iter(client.models.list()), None)
    except Exception as e:
        msg = str(e).lower()
        if "api key" in msg or "permission" in msg or "unauthenticated" in msg or "401" in msg or "403" in msg:
            raise KeyRejected("Key rejected by Gemini") from e
        logger.warning("Gemini probe failed unexpectedly: %s", e)
        raise ProbeUnavailable(f"Could not validate Gemini key: {e}") from e


def _probe_fal(api_key: str) -> None:
    """Validate via a public auth-check endpoint."""
    try:
        resp = httpx.get(
            "https://rest.alpha.fal.ai/auth/me",
            headers={"Authorization": f"Key {api_key}"},
            timeout=10.0,
        )
    except httpx.HTTPError as e:
        raise ProbeUnavailable(f"Could not reach Fal: {e}") from e
    if resp.status_code == 401 or resp.status_code == 403:
        raise KeyRejected("Key rejected by Fal")
    if resp.status_code >= 500:
        raise ProbeUnavailable(f"Fal returned {resp.status_code}")
    # 2xx or 4xx-not-auth → treat as valid auth (account-related 4xx is not our concern here).


def _probe_kling(api_key: str) -> None:
    """Kling has no dedicated auth-only endpoint. We attempt a cheap listing
    call and treat HTTP 401/403 as rejection. Any other failure means we
    can't tell, so we report ProbeUnavailable.
    """
    try:
        resp = httpx.get(
            "https://api.klingai.com/v1/videos/text2video",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
    except httpx.HTTPError as e:
        raise ProbeUnavailable(f"Could not reach Kling: {e}") from e
    if resp.status_code in (401, 403):
        raise KeyRejected("Key rejected by Kling")
    if resp.status_code >= 500:
        raise ProbeUnavailable(f"Kling returned {resp.status_code}")
    # Any other 2xx/4xx response indicates the key was accepted at the auth layer.
