"""Load a user's BYO API keys at the start of a pipeline task.

Strategy: pipeline code paths read provider keys from ``os.environ``
(``GEMINI_API_KEY``, ``FAL_KEY``, ``KLING_API_KEY``) in many call sites.
Refactoring every callsite to accept an ``api_key`` argument is invasive.
Instead we override ``os.environ`` for the duration of the task — safe
because Celery's prefork pool runs one task per subprocess at a time.

Use ``loaded_keys_env(user_id)`` as a context manager around the pipeline
body. It returns the dict of keys it loaded (for diagnostics) and restores
the previous environ on exit.
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Iterator

from app.api.key_crypto import decrypt
from app.db import SessionLocal
from app.models.user_api_key import UserApiKey

logger = logging.getLogger(__name__)

# Map provider → env var that the pipeline reads.
_PROVIDER_ENV = {
    "gemini": "GEMINI_API_KEY",
    "fal": "FAL_KEY",
    "kling": "KLING_API_KEY",
}


class MissingKeys(RuntimeError):
    """The user has not provided keys required for this session type."""

    def __init__(self, missing: list[str]) -> None:
        super().__init__(f"Missing required API keys: {', '.join(missing)}")
        self.missing = missing


def load_keys_for_user(user_id: str) -> dict[str, str]:
    """Read + decrypt all stored keys for a user. Returns ``{provider: plaintext}``."""
    db = SessionLocal()
    try:
        rows = db.query(UserApiKey).filter(UserApiKey.user_id == user_id).all()
        out: dict[str, str] = {}
        for row in rows:
            try:
                out[row.provider] = decrypt(row.ciphertext)
            except Exception as e:
                logger.warning(
                    "Could not decrypt %s key for user %s: %s",
                    row.provider, user_id, e,
                )
        return out
    finally:
        db.close()


def required_providers(session_type: str, config: dict) -> list[str]:
    """Return the providers the session needs to run.

    Image sessions: Gemini only.
    Video sessions: Gemini AND the chosen video provider (fal | kling | veo).
    Veo runs on Gemini's API so it does not add a provider beyond Gemini.
    """
    if session_type == "video":
        provider = (config.get("video_provider") or "fal").strip().lower()
        if provider == "veo":
            return ["gemini"]
        if provider in ("fal", "kling"):
            return ["gemini", provider]
        # Unknown provider — fall back to requiring Gemini only; the
        # video client factory will surface a clearer error later.
        return ["gemini"]
    return ["gemini"]


@contextmanager
def loaded_keys_env(user_id: str, session_type: str, config: dict) -> Iterator[dict[str, str]]:
    """Override env with the user's keys for the duration of the block.

    Raises ``MissingKeys`` *before* mutating env when any required provider
    is absent. Restores the previous environ on exit.
    """
    user_keys = load_keys_for_user(user_id)
    needed = required_providers(session_type, config)
    missing = [p for p in needed if p not in user_keys or not user_keys[p]]
    if missing:
        raise MissingKeys(missing)

    saved: dict[str, str | None] = {}
    try:
        for provider, plaintext in user_keys.items():
            env_var = _PROVIDER_ENV.get(provider)
            if not env_var:
                continue
            saved[env_var] = os.environ.get(env_var)
            os.environ[env_var] = plaintext
        yield user_keys
    finally:
        for env_var, prev in saved.items():
            if prev is None:
                os.environ.pop(env_var, None)
            else:
                os.environ[env_var] = prev
