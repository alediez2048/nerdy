"""Video client factory — resolves provider with precedence:

    session.config["video_provider"]  →  config.yaml  →  VIDEO_PROVIDER env

Returns a concrete ``VideoGenerationClient`` implementation.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import yaml

from generate_video.video_client import VideoGenerationClient

logger = logging.getLogger(__name__)

VALID_PROVIDERS = {"fal", "veo", "kling"}
_CONFIG_PATH = "data/config.yaml"


def _load_config_provider() -> str | None:
    """Read ``video_provider`` from config.yaml (returns None on failure)."""
    try:
        with open(_CONFIG_PATH) as f:
            cfg: dict[str, Any] = yaml.safe_load(f) or {}
        return cfg.get("video_provider")
    except FileNotFoundError:
        return None


def _resolve_provider(session_value: str | None) -> str:
    """Return validated provider name using the precedence chain."""
    raw = (
        session_value
        or _load_config_provider()
        or os.getenv("VIDEO_PROVIDER")
        or "fal"
    )
    provider = raw.strip().lower()
    if provider not in VALID_PROVIDERS:
        logger.warning(
            "Unknown video_provider '%s', falling back to 'fal'", provider
        )
        return "fal"
    return provider


def build_video_client(
    provider: str | None = None,
    **kwargs: Any,
) -> VideoGenerationClient:
    """Construct the video client for the resolved provider.

    Parameters
    ----------
    provider:
        Explicit value (typically from ``session.config["video_provider"]``).
        Falls back to config.yaml then ``VIDEO_PROVIDER`` env.
    **kwargs:
        Forwarded to the concrete client constructor (``api_key``, ``rpm``, …).
    """
    resolved = _resolve_provider(provider)
    logger.info("Video provider resolved: %s (requested: %s)", resolved, provider)

    if resolved == "fal":
        from generate_video.fal_client import FalVideoClient

        model = kwargs.pop("model", None)
        if model is None:
            try:
                with open(_CONFIG_PATH) as f:
                    cfg = yaml.safe_load(f) or {}
                model = cfg.get("video_fal_model")
            except FileNotFoundError:
                pass
        if model:
            kwargs["model"] = model
        return FalVideoClient(**kwargs)

    if resolved == "veo":
        from generate_video.veo_client import VeoClient

        return VeoClient(**kwargs)

    if resolved == "kling":
        from generate_video.kling_client import KlingClient

        return KlingClient(**kwargs)

    raise ValueError(f"Unsupported video provider: {resolved}")
