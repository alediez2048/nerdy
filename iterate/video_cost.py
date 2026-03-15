"""Video cost tracking — per-video, per-variant, per-regen (P3-12, PRD 4.9.8).

Tracks Veo generation costs at $0.15/sec. Supports audio vs silent
breakdown, regen cost separation, and cross-format aggregation via ledger.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from iterate.ledger import read_events

logger = logging.getLogger(__name__)

VEO_COST_PER_SECOND: float = 0.15


@dataclass
class VideoCostEntry:
    """Cost record for a single video generation."""

    ad_id: str
    variant_id: str
    duration: float
    cost_usd: float
    audio_mode: str
    is_regen: bool


@dataclass
class VideoCostSummary:
    """Aggregated video cost summary across all ads."""

    total_videos: int
    total_cost_usd: float
    total_regen_cost_usd: float
    avg_cost_per_ad: float
    regen_overhead_pct: float


def track_video_cost(
    ad_id: str,
    variant_id: str,
    generation_metadata: dict,
) -> VideoCostEntry:
    """Create a cost entry for a single video generation.

    Args:
        ad_id: The ad identifier.
        variant_id: The variant identifier (e.g. "anchor", "alternative", "regen_1").
        generation_metadata: Dict with duration, audio_mode, and optional is_regen.

    Returns:
        VideoCostEntry with calculated cost.
    """
    duration = generation_metadata.get("duration", 0)
    audio_mode = generation_metadata.get("audio_mode", "silent")
    is_regen = generation_metadata.get("is_regen", False)
    cost_usd = duration * VEO_COST_PER_SECOND

    entry = VideoCostEntry(
        ad_id=ad_id,
        variant_id=variant_id,
        duration=duration,
        cost_usd=cost_usd,
        audio_mode=audio_mode,
        is_regen=is_regen,
    )

    logger.info(
        "Video cost: ad=%s variant=%s duration=%.1fs cost=$%.2f audio=%s regen=%s",
        ad_id, variant_id, duration, cost_usd, audio_mode, is_regen,
    )
    return entry


def get_video_costs_by_ad(ad_id: str, ledger_path: str) -> list[VideoCostEntry]:
    """Extract video cost entries for a specific ad from the ledger.

    Reads VideoGenerated events for the given ad and builds cost entries.

    Args:
        ad_id: The ad identifier.
        ledger_path: Path to the JSONL ledger file.

    Returns:
        List of VideoCostEntry for the ad.
    """
    events = read_events(ledger_path)
    costs: list[VideoCostEntry] = []

    for event in events:
        if event.get("event_type") != "VideoGenerated":
            continue
        if event.get("ad_id") != ad_id:
            continue

        outputs = event.get("outputs", {})
        inputs = event.get("inputs", {})
        duration = outputs.get("duration", 0)
        audio_mode = outputs.get("audio_mode", "silent")
        is_regen = outputs.get("is_regen", False)
        variant_id = inputs.get("variant_id", "unknown")

        costs.append(VideoCostEntry(
            ad_id=ad_id,
            variant_id=variant_id,
            duration=duration,
            cost_usd=duration * VEO_COST_PER_SECOND,
            audio_mode=audio_mode,
            is_regen=is_regen,
        ))

    return costs


def get_video_cost_summary(ledger_path: str) -> VideoCostSummary:
    """Compute aggregated video cost summary from the ledger.

    Args:
        ledger_path: Path to the JSONL ledger file.

    Returns:
        VideoCostSummary with totals, averages, and regen overhead.
    """
    events = read_events(ledger_path)
    video_events = [e for e in events if e.get("event_type") == "VideoGenerated"]

    total_cost = 0.0
    regen_cost = 0.0
    ad_ids: set[str] = set()

    for event in video_events:
        outputs = event.get("outputs", {})
        duration = outputs.get("duration", 0)
        is_regen = outputs.get("is_regen", False)
        cost = duration * VEO_COST_PER_SECOND

        total_cost += cost
        if is_regen:
            regen_cost += cost
        ad_ids.add(event.get("ad_id", ""))

    num_ads = max(len(ad_ids), 1)
    num_videos = len(video_events)
    regen_pct = (regen_cost / total_cost * 100) if total_cost > 0 else 0.0

    return VideoCostSummary(
        total_videos=num_videos,
        total_cost_usd=total_cost,
        total_regen_cost_usd=regen_cost,
        avg_cost_per_ad=total_cost / num_ads,
        regen_overhead_pct=regen_pct,
    )
