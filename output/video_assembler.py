"""Video ad assembly — collects copy + video from ledger events (PC-03).

Mirrors output/assembler.py but for video sessions: reads AdGenerated for copy,
VideoSelected for the winning video path, and VideoBlocked for copy-only fallback.
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from iterate.ledger import read_events_filtered

logger = logging.getLogger(__name__)


@dataclass
class VideoAssembledAd:
    """A fully assembled video ad ready for export."""

    ad_id: str
    brief_id: str
    primary_text: str
    headline: str
    description: str
    cta_button: str
    winning_video_path: str | None
    video_scores: dict[str, Any] | None
    formats: list[str]
    audience: str
    campaign_goal: str
    persona: str
    seed: int


def assemble_video_ad(ad_id: str, ledger_path: str) -> VideoAssembledAd:
    """Assemble a video ad from ledger events.

    Reads copy from AdGenerated, video path from VideoSelected,
    falls back to copy-only if VideoBlocked or no video events exist.
    """
    gen_events = read_events_filtered(ledger_path, event_type="AdGenerated", ad_id=ad_id)
    primary_text = ""
    headline = ""
    description = ""
    cta_button = ""
    brief_id = ""
    audience = ""
    campaign_goal = ""
    persona = ""
    seed = 0

    if gen_events:
        latest = gen_events[-1]
        outputs = latest.get("outputs", {})
        primary_text = outputs.get("primary_text", "")
        headline = outputs.get("headline", "")
        description = outputs.get("description", "")
        cta_button = outputs.get("cta_button", outputs.get("cta", ""))
        brief_id = latest.get("brief_id", "")
        audience = outputs.get("audience", "")
        campaign_goal = outputs.get("campaign_goal", "")
        persona = outputs.get("persona", "")
        seed = latest.get("seed", 0)
        if isinstance(seed, str):
            try:
                seed = int(seed)
            except ValueError:
                seed = 0

    select_events = read_events_filtered(
        ledger_path, event_type="VideoSelected", ad_id=ad_id
    )

    if select_events:
        latest = select_events[-1]
        outputs = latest.get("outputs", {})
        winning_video_path = outputs.get("winner_video_path")
        video_scores: dict[str, Any] | None = {
            "composite_score": outputs.get("composite_score", 0.0),
            "attribute_pass_pct": outputs.get("attribute_pass_pct", 0.0),
            "coherence_avg": outputs.get("coherence_avg", 0.0),
        }
        formats = ["copy", "video"]
    else:
        winning_video_path = None
        video_scores = None
        formats = ["copy"]

    return VideoAssembledAd(
        ad_id=ad_id,
        brief_id=brief_id,
        primary_text=primary_text,
        headline=headline,
        description=description,
        cta_button=cta_button,
        winning_video_path=winning_video_path,
        video_scores=video_scores,
        formats=formats,
        audience=audience,
        campaign_goal=campaign_goal,
        persona=persona,
        seed=seed,
    )


def export_video_ads(
    assembled_ads: list[VideoAssembledAd], output_dir: str
) -> list[str]:
    """Export assembled video ads to disk.

    Per ad: creates a directory, writes metadata.json, copies video MP4 if present.
    Returns list of output directory paths.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    dirs: list[str] = []

    for ad in assembled_ads:
        ad_dir = out / ad.ad_id
        ad_dir.mkdir(parents=True, exist_ok=True)

        metadata = {
            "ad_id": ad.ad_id,
            "brief_id": ad.brief_id,
            "primary_text": ad.primary_text,
            "headline": ad.headline,
            "description": ad.description,
            "cta_button": ad.cta_button,
            "formats": ad.formats,
            "audience": ad.audience,
            "campaign_goal": ad.campaign_goal,
            "persona": ad.persona,
            "seed": ad.seed,
            "video_scores": ad.video_scores,
        }
        (ad_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

        if ad.winning_video_path and Path(ad.winning_video_path).exists():
            dest = ad_dir / Path(ad.winning_video_path).name
            shutil.copy2(ad.winning_video_path, dest)

        dirs.append(str(ad_dir))

    return dirs
