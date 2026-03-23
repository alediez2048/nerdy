"""Fal.ai video generation client.

Uses ``fal-client`` (PyPI) to submit video generation jobs, poll for
completion, and download the resulting MP4 to disk.  Implements the
``VideoGenerationClient`` protocol so the orchestrator is provider-agnostic.
"""

from __future__ import annotations

import logging
import os
import time
from collections import deque
from pathlib import Path
from typing import Any

import fal_client
import httpx

from iterate.retry import retry_with_backoff

logger = logging.getLogger(__name__)

MODEL_FAL_DEFAULT = "fal-ai/veo3"

# Per-model capabilities: durations (seconds), aspect ratios, and argument format
_MODEL_PROFILES: dict[str, dict[str, Any]] = {
    "fal-ai/veo3": {
        "durations": {4, 6, 8},
        "aspect_ratios": {"9:16", "16:9"},
        "duration_format": "suffix_s",  # "8s"
        "extra_args": {"resolution": "720p", "generate_audio": False},
        "audio_key": "generate_audio",
    },
    "fal-ai/minimax/hailuo-02/standard/text-to-video": {
        "durations": {6, 10},
        "aspect_ratios": {"9:16", "16:9"},
        "duration_format": "bare_str",  # "6"
        "extra_args": {},
        "audio_key": None,
    },
    "fal-ai/wan/v2.2-5b/text-to-video/distill": {
        "durations": {4, 6, 8},
        "aspect_ratios": {"9:16", "16:9"},
        "duration_format": "bare_str",
        "extra_args": {},
        "audio_key": None,
    },
}

# Fallback for unknown models
_DEFAULT_PROFILE: dict[str, Any] = {
    "durations": {4, 6, 8},
    "aspect_ratios": {"9:16", "16:9"},
    "duration_format": "bare_str",
    "extra_args": {},
    "audio_key": None,
}

# Legacy constants for backward compat
SUPPORTED_DURATIONS_FAL = {4, 6, 8}
SUPPORTED_ASPECT_RATIOS_FAL = {"9:16", "16:9"}


def _extract_fal_video_url(result: Any) -> str:
    """Parse Fal queue result; supports minor API wrapper variations."""
    if not isinstance(result, dict):
        raise ValueError(f"Fal result must be dict, got {type(result).__name__}")
    video = result.get("video")
    if isinstance(video, dict) and video.get("url"):
        return str(video["url"])
    for wrap in ("data", "output", "result"):
        inner = result.get(wrap)
        if isinstance(inner, dict):
            v = inner.get("video")
            if isinstance(v, dict) and v.get("url"):
                return str(v["url"])
    raise KeyError(
        "Fal response missing video.url; top-level keys: "
        + str(sorted(result.keys()))
    )


class FalVideoClient:
    """Fal.ai video generation client implementing VideoGenerationClient."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = MODEL_FAL_DEFAULT,
        rpm: int = 10,
        timeout_seconds: int = 600,
    ) -> None:
        self.api_key = (
            api_key
            or os.getenv("FAL_KEY", "").strip()
            or os.getenv("FAL_AI_KEY", "").strip()
        )
        if not self.api_key:
            raise RuntimeError(
                "FAL_KEY not set — add FAL_KEY=... to .env (or pass api_key=)"
            )
        os.environ["FAL_KEY"] = self.api_key
        self.model = model
        self.model_used = model
        self._profile = _MODEL_PROFILES.get(model, _DEFAULT_PROFILE)
        self.rpm = rpm
        self.timeout_seconds = timeout_seconds
        self._call_timestamps: deque[float] = deque()
        self._last_remote_url: str | None = None

    def _rate_limit_wait(self) -> None:
        now = time.time()
        window = 60.0
        while len(self._call_timestamps) >= self.rpm:
            oldest = self._call_timestamps[0]
            if now - oldest >= window:
                self._call_timestamps.popleft()
            else:
                wait = window - (now - oldest) + 0.1
                logger.info("Fal rate limit: waiting %.1fs", wait)
                time.sleep(wait)
                now = time.time()
        self._call_timestamps.append(now)

    def normalize_duration(self, duration: int) -> int:
        supported = self._profile["durations"]
        if duration in supported:
            return duration
        # Pick the closest supported duration
        return min(supported, key=lambda d: abs(d - duration))

    def normalize_aspect_ratio(self, aspect_ratio: str) -> str:
        supported = self._profile["aspect_ratios"]
        if aspect_ratio in supported:
            return aspect_ratio
        return "9:16"

    def _format_duration(self, duration: int) -> str:
        """Format duration per model requirements."""
        fmt = self._profile["duration_format"]
        if fmt == "suffix_s":
            return f"{duration}s"
        return str(duration)

    def generate_video(
        self,
        prompt: str,
        duration: int = 8,
        aspect_ratio: str = "9:16",
        audio: bool = False,
        negative_prompt: str = "",
        output_path: str = "output/videos/video.mp4",
        mode: str = "standard",
    ) -> str:
        """Submit a video job to Fal, poll, download result to *output_path*."""
        del mode
        normalized_duration = self.normalize_duration(duration)
        normalized_aspect_ratio = self.normalize_aspect_ratio(aspect_ratio)

        arguments: dict[str, Any] = {
            "prompt": prompt,
            "duration": self._format_duration(normalized_duration),
            "aspect_ratio": normalized_aspect_ratio,
        }
        # Add model-specific extra args (resolution, etc.)
        arguments.update(self._profile.get("extra_args", {}))
        # Set audio flag if the model supports it
        audio_key = self._profile.get("audio_key")
        if audio_key:
            arguments[audio_key] = audio
        if negative_prompt.strip():
            arguments["negative_prompt"] = negative_prompt.strip()

        def _do_call() -> str:
            self._rate_limit_wait()
            try:
                result = fal_client.subscribe(
                    self.model,
                    arguments=arguments,
                    client_timeout=float(self.timeout_seconds),
                )
                video_url = _extract_fal_video_url(result)
            except Exception as exc:
                logger.error(
                    "Fal subscribe failed model=%s error=%s",
                    self.model,
                    exc,
                    exc_info=True,
                )
                raise

            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            resp = httpx.get(video_url, timeout=120, follow_redirects=True)
            resp.raise_for_status()
            path.write_bytes(resp.content)

            if not path.exists() or path.stat().st_size == 0:
                raise RuntimeError(f"Downloaded Fal video missing or empty: {path}")

            # Store remote URL on the instance for ledger persistence
            self._last_remote_url = video_url

            return str(path)

        return retry_with_backoff(_do_call)
