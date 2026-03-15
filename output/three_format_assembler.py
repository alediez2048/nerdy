"""Three-format ad assembly — copy + image + video (P3-11, PRD 4.9.7).

Extends P1-18 assembly to include optional video. Handles graceful
degradation: video-blocked ads export with copy + image only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ThreeFormatAd:
    """An assembled ad with up to three formats."""

    ad_id: str
    copy: dict
    image_paths: dict[str, str]  # aspect_ratio → path
    video_path: str | None
    video_metadata: dict = field(default_factory=dict)
    has_video: bool = False
    format_flags: dict[str, bool] = field(default_factory=dict)

    def to_metadata(self) -> dict:
        """Generate metadata dict for export."""
        meta: dict = {
            "ad_id": self.ad_id,
            "format_mode": "three-format" if self.has_video else "image-only",
            "format_flags": self.format_flags,
            "images": self.image_paths,
        }
        if self.has_video and self.video_path:
            meta["video"] = {
                "path": self.video_path,
                **self.video_metadata,
            }
        return meta


def assemble_three_format(
    ad_id: str,
    copy: dict,
    image_paths: dict[str, str],
    video_path: str | None = None,
    video_metadata: dict | None = None,
) -> ThreeFormatAd:
    """Assemble a three-format ad (copy + image + optional video).

    Args:
        ad_id: The ad identifier.
        copy: Structured copy dict (headline, primary_text, etc.).
        image_paths: Dict of aspect_ratio → image file path.
        video_path: Path to winning video, or None for degraded ads.
        video_metadata: Optional video metadata (duration, model, etc.).

    Returns:
        ThreeFormatAd with format flags set.
    """
    has_video = video_path is not None

    format_flags = {
        "copy": True,
        "image": len(image_paths) > 0,
        "video": has_video,
    }

    ad = ThreeFormatAd(
        ad_id=ad_id,
        copy=copy,
        image_paths=image_paths,
        video_path=video_path,
        video_metadata=video_metadata or {},
        has_video=has_video,
        format_flags=format_flags,
    )

    mode = "three-format" if has_video else "image-only"
    logger.info("Assembled %s ad %s (%d images, video=%s)",
                 mode, ad_id, len(image_paths), has_video)

    return ad
