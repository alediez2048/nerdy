"""Tests for three-format ad assembly (P3-11).

Validates copy + image + video assembly, placement mapping,
graceful degradation, and metadata output.
"""

from __future__ import annotations

from output.three_format_assembler import (
    ThreeFormatAd,
    assemble_three_format,
)
from output.placement import (
    PlacementMap,
    map_placements,
)


# --- Three-Format Assembly ---


def test_three_format_assembly_with_video() -> None:
    """Assembly with video produces all three formats."""
    ad = assemble_three_format(
        ad_id="ad_001",
        copy={"headline": "Test", "primary_text": "Body"},
        image_paths={"1:1": "img_1x1.png", "4:5": "img_4x5.png", "9:16": "img_9x16.png"},
        video_path="video.mp4",
        video_metadata={"duration": 6, "model_used": "veo-3.1-fast"},
    )
    assert isinstance(ad, ThreeFormatAd)
    assert ad.has_video is True
    assert ad.video_path == "video.mp4"
    assert ad.format_flags["video"] is True


def test_two_format_assembly_no_video() -> None:
    """Assembly without video (degraded) produces copy + image only."""
    ad = assemble_three_format(
        ad_id="ad_001",
        copy={"headline": "Test", "primary_text": "Body"},
        image_paths={"1:1": "img_1x1.png", "9:16": "img_9x16.png"},
        video_path=None,
    )
    assert ad.has_video is False
    assert ad.video_path is None
    assert ad.format_flags["video"] is False
    assert ad.format_flags["image"] is True


def test_metadata_includes_video_when_present() -> None:
    """Metadata dict includes video info when video is present."""
    ad = assemble_three_format(
        ad_id="ad_001",
        copy={"headline": "Test"},
        image_paths={"1:1": "img.png"},
        video_path="video.mp4",
        video_metadata={"duration": 6},
    )
    meta = ad.to_metadata()
    assert "video" in meta
    assert meta["video"]["path"] == "video.mp4"
    assert meta["video"]["duration"] == 6


def test_metadata_flags_image_only_when_no_video() -> None:
    """Metadata flags image-only when video is absent."""
    ad = assemble_three_format(
        ad_id="ad_001",
        copy={"headline": "Test"},
        image_paths={"1:1": "img.png"},
        video_path=None,
    )
    meta = ad.to_metadata()
    assert meta["format_mode"] == "image-only"


# --- Placement Mapping ---


def test_placement_map_three_format() -> None:
    """Three-format ad maps to Feed, Stories, and Reels."""
    ad = assemble_three_format(
        ad_id="ad_001",
        copy={"headline": "Test"},
        image_paths={"1:1": "img_1x1.png", "9:16": "img_9x16.png"},
        video_path="video.mp4",
    )
    pm = map_placements(ad)
    assert isinstance(pm, PlacementMap)
    assert "feed" in pm.placements
    assert "stories" in pm.placements
    assert "reels" in pm.placements
    assert pm.placements["reels"]["video"] == "video.mp4"


def test_placement_map_two_format() -> None:
    """Two-format ad (no video) maps to Feed and Stories only."""
    ad = assemble_three_format(
        ad_id="ad_001",
        copy={"headline": "Test"},
        image_paths={"1:1": "img_1x1.png", "9:16": "img_9x16.png"},
        video_path=None,
    )
    pm = map_placements(ad)
    assert "feed" in pm.placements
    assert "stories" in pm.placements
    # Reels requires video
    assert pm.placements.get("reels", {}).get("video") is None


def test_placement_format_availability() -> None:
    """PlacementMap includes format availability flags."""
    ad = assemble_three_format(
        ad_id="ad_001",
        copy={"headline": "Test"},
        image_paths={"1:1": "img.png"},
        video_path="video.mp4",
    )
    pm = map_placements(ad)
    assert pm.format_available["image"] is True
    assert pm.format_available["video"] is True
