"""Veo 3.1 Fast API client with rate limiting and file download."""

from __future__ import annotations

import json
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from iterate.retry import retry_with_backoff

logger = logging.getLogger(__name__)

MODEL_VEO = "veo-3.1-fast"
API_MODEL_VEO = "veo-3.1-fast-generate-preview"
SUPPORTED_ASPECT_RATIOS = {"9:16", "16:9"}
SUPPORTED_DURATIONS = {8}


def _debug_log(hypothesis_id: str, location: str, message: str, data: dict[str, Any]) -> None:
    # region agent log
    try:
        debug_path = Path("/app/.cursor/debug-c163a9.log")
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "sessionId": "c163a9",
            "runId": "post-fix",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with debug_path.open("a") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        pass
    # endregion


class VideoGenerationError(Exception):
    """Raised when Veo generation fails."""


@dataclass
class VideoResult:
    """Result of a video generation API call."""

    video_path: str
    model_used: str
    duration_seconds: int
    tokens_consumed: int
    metadata: dict[str, Any] = field(default_factory=dict)


class VeoRateLimiter:
    """Rate limiter for Veo API calls."""

    def __init__(self, max_calls_per_minute: int = 10) -> None:
        self.max_calls_per_minute = max_calls_per_minute
        self.call_count = 0
        self._call_timestamps: list[float] = []

    def can_call(self) -> bool:
        self._prune_old_timestamps()
        return len(self._call_timestamps) < self.max_calls_per_minute

    def record_call(self) -> None:
        self._call_timestamps.append(time.time())
        self.call_count += 1

    def wait_if_needed(self) -> None:
        while not self.can_call():
            time.sleep(1)

    def _prune_old_timestamps(self) -> None:
        cutoff = time.time() - 60
        self._call_timestamps = [t for t in self._call_timestamps if t > cutoff]


class VeoClient:
    """Veo 3.1 Fast client using the Google GenAI SDK."""

    def __init__(
        self,
        api_key: str | None = None,
        rpm: int = 10,
        model: str = API_MODEL_VEO,
        poll_interval: float = 10.0,
        timeout_seconds: int = 600,
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not set — add it to .env or pass api_key=")
        self.model = model
        self.model_used = MODEL_VEO
        self.rpm = rpm
        self.poll_interval = poll_interval
        self.timeout_seconds = timeout_seconds
        self._call_timestamps: deque[float] = deque()

    def _rate_limit_wait(self) -> None:
        now = time.time()
        window = 60.0
        while len(self._call_timestamps) >= self.rpm:
            oldest = self._call_timestamps[0]
            if now - oldest >= window:
                self._call_timestamps.popleft()
            else:
                wait = window - (now - oldest) + 0.1
                logger.info("Rate limit: waiting %.1fs (at %d RPM cap)", wait, self.rpm)
                time.sleep(wait)
                now = time.time()
        self._call_timestamps.append(now)

    def normalize_duration(self, duration: int) -> int:
        if duration in SUPPORTED_DURATIONS:
            return duration
        return 8

    def normalize_aspect_ratio(self, aspect_ratio: str) -> str:
        if aspect_ratio in SUPPORTED_ASPECT_RATIOS:
            return aspect_ratio
        return "9:16"

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
        """Generate and save a Veo video to disk."""
        del mode
        normalized_duration = self.normalize_duration(duration)
        normalized_aspect_ratio = self.normalize_aspect_ratio(aspect_ratio)

        def _build_prompt(include_audio: bool) -> str:
            full_prompt = prompt
            if negative_prompt:
                full_prompt = f"{full_prompt}\n\nAvoid: {negative_prompt}"
            if not include_audio:
                full_prompt = (
                    f"{full_prompt}\n\nAudio: silent. No dialogue, narration, music, or sound effects."
                )
            return full_prompt

        def _do_call(include_audio: bool) -> str:
            full_prompt = _build_prompt(include_audio)

            # region agent log
            _debug_log(
                "H7",
                "generate_video/veo_client.py:generate_video:start",
                "starting veo generation",
                {
                    "model": self.model,
                    "prompt_length": len(full_prompt),
                    "requested_duration": duration,
                    "normalized_duration": normalized_duration,
                    "requested_aspect_ratio": aspect_ratio,
                    "normalized_aspect_ratio": normalized_aspect_ratio,
                    "audio": include_audio,
                    "output_path": output_path,
                },
            )
            # endregion

            self._rate_limit_wait()
            client = genai.Client(api_key=self.api_key)
            operation = client.models.generate_videos(
                model=self.model,
                prompt=full_prompt,
                config=types.GenerateVideosConfig(
                    aspect_ratio=normalized_aspect_ratio,
                    duration_seconds=normalized_duration,
                    number_of_videos=1,
                    resolution="720p",
                ),
            )

            start = time.time()
            while not getattr(operation, "done", False):
                if time.time() - start >= self.timeout_seconds:
                    raise VideoGenerationError(
                        f"Veo generation timed out after {self.timeout_seconds}s"
                    )
                time.sleep(self.poll_interval)
                operation = client.operations.get(operation)

            error = getattr(operation, "error", None)
            if error is not None:
                raise VideoGenerationError(str(error))

            response = getattr(operation, "response", None)
            generated_videos = getattr(response, "generated_videos", None)
            if not generated_videos:
                raise VideoGenerationError("Veo completed without generated_videos")

            generated_video = generated_videos[0]
            video_file = getattr(generated_video, "video", None)
            if video_file is None:
                raise VideoGenerationError("Veo completed without a downloadable video file")

            client.files.download(file=video_file)
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            video_file.save(str(path))

            if not path.exists() or path.stat().st_size == 0:
                raise VideoGenerationError(f"Downloaded Veo file missing or empty: {path}")

            # region agent log
            _debug_log(
                "H7",
                "generate_video/veo_client.py:generate_video:success",
                "veo generation saved file",
                {
                    "output_path": str(path),
                    "size_bytes": path.stat().st_size,
                    "normalized_duration": normalized_duration,
                    "normalized_aspect_ratio": normalized_aspect_ratio,
                    "audio": include_audio,
                },
            )
            # endregion
            return str(path)

        try:
            return retry_with_backoff(lambda: _do_call(audio))
        except Exception as exc:
            error_text = str(exc)
            if audio and "RESOURCE_EXHAUSTED" in error_text:
                # region agent log
                _debug_log(
                    "H12",
                    "generate_video/veo_client.py:generate_video:audio-fallback",
                    "retrying silent after audio quota error",
                    {
                        "requested_duration": duration,
                        "requested_aspect_ratio": aspect_ratio,
                        "output_path": output_path,
                    },
                )
                # endregion
                try:
                    return retry_with_backoff(lambda: _do_call(False))
                except Exception as fallback_exc:
                    # region agent log
                    _debug_log(
                        "H8",
                        "generate_video/veo_client.py:generate_video:error",
                        "veo generation failed after silent fallback",
                        {
                            "error_type": type(fallback_exc).__name__,
                            "error": str(fallback_exc),
                            "requested_duration": duration,
                            "requested_aspect_ratio": aspect_ratio,
                        },
                    )
                    # endregion
                    raise fallback_exc

            # region agent log
            _debug_log(
                "H8",
                "generate_video/veo_client.py:generate_video:error",
                "veo generation failed",
                {
                    "error_type": type(exc).__name__,
                    "error": error_text,
                    "requested_duration": duration,
                    "requested_aspect_ratio": aspect_ratio,
                },
            )
            # endregion
            raise


_rate_limiter = VeoRateLimiter()


def generate_video(
    video_spec: object,
    seed: int,
    output_path: str | None = None,
) -> VideoResult:
    """Backward-compatible helper that routes through `VeoClient`."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")

    prompt = getattr(video_spec, "scene_description", None) or str(video_spec)
    duration = int(getattr(video_spec, "duration", 8))
    aspect_ratio = str(getattr(video_spec, "aspect_ratio", "9:16"))
    path = output_path or f"/tmp/video_{seed}.mp4"

    _rate_limiter.wait_if_needed()

    def _do_call() -> VideoResult:
        _rate_limiter.record_call()
        client = VeoClient(api_key=api_key)
        saved_path = client.generate_video(
            prompt=prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            output_path=path,
        )
        return VideoResult(
            video_path=saved_path,
            model_used=MODEL_VEO,
            duration_seconds=client.normalize_duration(duration),
            tokens_consumed=0,
            metadata={
                "seed": seed,
                "aspect_ratio": client.normalize_aspect_ratio(aspect_ratio),
            },
        )

    return retry_with_backoff(_do_call)
