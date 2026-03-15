"""Meta placement mapping for multi-format ads (P3-11, PRD 4.9.7).

Maps creative assets to Meta placements: Feed (1:1/4:5), Stories (9:16),
Reels (9:16 video). Handles both three-format and two-format ads.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from output.three_format_assembler import ThreeFormatAd

logger = logging.getLogger(__name__)


@dataclass
class PlacementMap:
    """Mapping of creative assets to Meta placements."""

    ad_id: str
    placements: dict[str, dict[str, str | None]]
    format_available: dict[str, bool] = field(default_factory=dict)


def map_placements(assembled_ad: ThreeFormatAd) -> PlacementMap:
    """Map assembled ad assets to Meta placements.

    Feed: 1:1 or 4:5 image + copy
    Stories: 9:16 image + 9:16 video (if available) + copy
    Reels: 9:16 video (if available) + copy

    Args:
        assembled_ad: The assembled three-format ad.

    Returns:
        PlacementMap with per-placement asset mapping.
    """
    images = assembled_ad.image_paths
    video = assembled_ad.video_path

    # Feed: prefer 4:5, fall back to 1:1
    feed_image = images.get("4:5") or images.get("1:1")
    feed = {"image": feed_image, "copy": "included"}

    # Stories: 9:16 image + optional video
    stories_image = images.get("9:16")
    stories: dict[str, str | None] = {
        "image": stories_image,
        "video": video,
        "copy": "included",
    }

    # Reels: video only (requires video)
    reels: dict[str, str | None] = {
        "video": video,
        "copy": "included",
    }

    placements: dict[str, dict[str, str | None]] = {
        "feed": feed,
        "stories": stories,
    }
    if video:
        placements["reels"] = reels

    format_available = {
        "copy": True,
        "image": len(images) > 0,
        "video": assembled_ad.has_video,
    }

    return PlacementMap(
        ad_id=assembled_ad.ad_id,
        placements=placements,
        format_available=format_available,
    )
