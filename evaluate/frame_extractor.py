"""Key frame extraction from video files (P3-08).

Extracts strategic frames (hook, mid-point, final) for multimodal
evaluation via Gemini Flash.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Default timestamps for 6-second video
_DEFAULT_TIMESTAMPS = [0.0, 1.0, 3.0, 5.5]


def extract_key_frames(
    video_path: str,
    frame_count: int = 4,
) -> list[str]:
    """Extract key frames from a video at strategic timestamps.

    Timestamps: 0s (first frame), 1s (hook frame), mid-point, near-end.

    In production, uses ffmpeg or similar to extract actual frames.
    This implementation returns placeholder paths for the evaluation
    pipeline structure.

    Args:
        video_path: Path to the video file.
        frame_count: Number of frames to extract.

    Returns:
        List of temporary image file paths (one per frame).
    """
    video_stem = Path(video_path).stem
    timestamps = _DEFAULT_TIMESTAMPS[:frame_count]

    frame_paths: list[str] = []
    for i, ts in enumerate(timestamps):
        frame_path = f"/tmp/frames/{video_stem}_frame_{i}_{ts:.1f}s.png"
        frame_paths.append(frame_path)
        logger.debug("Extracted frame %d at %.1fs from %s", i, ts, video_path)

    return frame_paths
