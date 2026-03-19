"""Kling 2.6 Pro API client with rate limiting (PC-01).

Async task-based workflow: submit → poll → download.
Uses Bearer token auth with KLING_API_KEY.
"""

from __future__ import annotations

import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import requests

from iterate.retry import retry_with_backoff

logger = logging.getLogger(__name__)

MODEL_KLING = "kling-v2.6-pro"
BASE_URL = "https://api.klingapi.com"
DEFAULT_NEGATIVE = "blur, distort, low quality, brand logos, trademarks"


class VideoGenerationError(Exception):
    """Raised when video generation fails after retries."""


@dataclass
class TaskResult:
    """Result from polling a Kling generation task."""

    status: str
    video_url: str | None = None
    error_message: str | None = None
    metadata: dict = field(default_factory=dict)


class KlingClient:
    """Kling 2.6 Pro text-to-video client.

    Args:
        api_key: Kling API key. Defaults to KLING_API_KEY env var.
        rpm: Max requests per minute for rate limiting.
        base_url: API base URL.
    """

    def __init__(
        self,
        api_key: str | None = None,
        rpm: int = 10,
        base_url: str = BASE_URL,
    ):
        self.api_key = api_key or os.getenv("KLING_API_KEY", "")
        if not self.api_key:
            raise RuntimeError(
                "KLING_API_KEY not set — add it to .env or pass api_key="
            )
        self.base_url = base_url
        self.rpm = rpm
        self._call_timestamps: deque[float] = deque()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _rate_limit_wait(self) -> None:
        """Block until we're under the RPM cap."""
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

    def submit_text2video(
        self,
        prompt: str,
        duration: int = 10,
        aspect_ratio: str = "9:16",
        audio: bool = False,
        negative_prompt: str = DEFAULT_NEGATIVE,
        mode: str = "standard",
    ) -> str:
        """Submit a text-to-video generation task.

        Returns the task_id for polling.
        """
        self._rate_limit_wait()

        body = {
            "model": MODEL_KLING,
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "mode": mode,
            "sound": audio,
            "negative_prompt": negative_prompt,
        }

        def _do_submit() -> str:
            resp = requests.post(
                f"{self.base_url}/v1/videos/text2video",
                headers=self._headers(),
                json=body,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            task_id = data.get("task_id", "")
            if not task_id:
                raise VideoGenerationError(f"No task_id in response: {data}")
            logger.info("Kling task submitted: %s (duration=%ds, audio=%s)", task_id, duration, audio)
            return task_id

        return retry_with_backoff(_do_submit)

    def poll_task(
        self,
        task_id: str,
        timeout_seconds: int = 120,
        poll_interval: float = 5.0,
    ) -> TaskResult:
        """Poll until task completes or fails.

        Raises VideoGenerationError on timeout.
        """
        start = time.time()
        url = f"{self.base_url}/v1/videos/{task_id}"

        while True:
            resp = requests.get(url, headers=self._headers(), timeout=30)
            resp.raise_for_status()
            data = resp.json()

            status = data.get("status", "unknown")

            if status == "completed":
                video_url = data.get("url") or data.get("video_url", "")
                return TaskResult(
                    status="completed",
                    video_url=video_url,
                    metadata=data.get("metadata", {}),
                )

            if status == "failed":
                error = data.get("error", {})
                msg = error.get("message", "Unknown error") if isinstance(error, dict) else str(error)
                return TaskResult(status="failed", error_message=msg)

            elapsed = time.time() - start
            if elapsed >= timeout_seconds:
                raise VideoGenerationError(
                    f"Task {task_id} timed out after {timeout_seconds}s (status={status})"
                )

            logger.debug("Task %s: %s (%.0fs elapsed)", task_id, status, elapsed)
            time.sleep(poll_interval)

    def download_video(self, video_url: str, output_path: str) -> str:
        """Download video from URL to local file.

        Returns the output path on success.
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        resp = requests.get(video_url, stream=True, timeout=60)
        resp.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        size = Path(output_path).stat().st_size if Path(output_path).exists() else 0
        if size == 0:
            raise VideoGenerationError(f"Downloaded file is empty: {output_path}")

        logger.info("Downloaded video (%d bytes) to %s", size, output_path)
        return output_path

    def generate_video(
        self,
        prompt: str,
        duration: int = 10,
        aspect_ratio: str = "9:16",
        audio: bool = False,
        negative_prompt: str = DEFAULT_NEGATIVE,
        output_path: str = "output/videos/video.mp4",
        mode: str = "standard",
    ) -> str:
        """End-to-end: submit → poll → download.

        Returns the local file path of the downloaded video.
        Raises VideoGenerationError on any failure.
        """
        task_id = self.submit_text2video(
            prompt=prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            audio=audio,
            negative_prompt=negative_prompt,
            mode=mode,
        )

        result = self.poll_task(task_id)

        if result.status == "failed":
            raise VideoGenerationError(
                f"Kling task {task_id} failed: {result.error_message}"
            )

        if not result.video_url:
            raise VideoGenerationError(
                f"Kling task {task_id} completed but no video URL returned"
            )

        return self.download_video(result.video_url, output_path)
