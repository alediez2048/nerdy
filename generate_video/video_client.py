"""VideoGenerationClient protocol — provider-agnostic interface (Fal.ai migration).

Every video backend (Fal, Veo, Kling) implements this protocol so the
orchestrator, pipeline task, and tests never import a concrete client.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class VideoGenerationClient(Protocol):
    """Minimal contract every video provider must satisfy."""

    model_used: str

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
        """Generate a video and save it to *output_path*. Return the path."""
        ...

    def normalize_duration(self, duration: int) -> int:
        """Clamp *duration* to a value the provider supports."""
        ...

    def normalize_aspect_ratio(self, aspect_ratio: str) -> str:
        """Clamp *aspect_ratio* to a value the provider supports."""
        ...
