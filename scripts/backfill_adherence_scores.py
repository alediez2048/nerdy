#!/usr/bin/env python3
"""Backfill brief adherence scores for all published/selected ads.

Reads session ledgers, finds AdPublished/VideoSelected events, loads
session config from the ledger's BriefExpanded event or defaults,
runs PD-12 brief adherence scorer, and appends BriefAdherenceScored events.

Usage:
    python scripts/backfill_adherence_scores.py [--dry-run]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from iterate.ledger import log_event, read_events

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _extract_session_config(events: list[dict]) -> dict:
    """Extract session config from BriefExpanded or AdGenerated events."""
    for e in events:
        if e.get("event_type") == "BriefExpanded":
            inputs = e.get("inputs", {})
            if inputs.get("audience") or inputs.get("campaign_goal"):
                return inputs
    # Fallback: try to infer from any event that has these fields
    for e in events:
        inputs = e.get("inputs", {})
        if inputs.get("audience"):
            return inputs
    return {}


def find_ads_to_score() -> list[dict]:
    """Find all published/selected ads that haven't been adherence-scored yet."""
    session_ledgers = sorted(Path("data/sessions").glob("*/ledger.jsonl"))
    to_score = []

    for ledger_path in session_ledgers:
        session_id = ledger_path.parent.name
        events = read_events(str(ledger_path))

        already_scored = set(
            e.get("ad_id") for e in events if e.get("event_type") == "BriefAdherenceScored"
        )

        # Get copy from AdGenerated events
        copy_by_ad: dict[str, dict] = {}
        for e in events:
            if e.get("event_type") in ("AdGenerated", "AdRegenerated"):
                copy_by_ad[e.get("ad_id", "")] = e.get("outputs", {})

        # Get session config
        session_config = _extract_session_config(events)

        # Find published ads
        for e in events:
            if e.get("event_type") not in ("AdPublished", "VideoSelected"):
                continue
            ad_id = e.get("ad_id", "")
            if ad_id in already_scored:
                continue

            copy = copy_by_ad.get(ad_id, {})
            if not copy.get("primary_text") and not copy.get("headline"):
                continue

            # Get image/video path if available
            image_path = None
            video_path = None
            if e.get("event_type") == "AdPublished":
                image_path = e.get("outputs", {}).get("winning_image")
                if image_path and not Path(image_path).exists():
                    image_path = None
            elif e.get("event_type") == "VideoSelected":
                video_path = e.get("outputs", {}).get("winner_video_path")
                if video_path and not Path(video_path).exists():
                    video_path = None

            to_score.append({
                "session_id": session_id,
                "ad_id": ad_id,
                "brief_id": e.get("brief_id", ""),
                "copy": copy,
                "session_config": session_config,
                "image_path": image_path,
                "video_path": video_path,
                "ledger_path": str(ledger_path),
            })

    return to_score


def run_backfill(dry_run: bool = False) -> None:
    """Score all unscored ads for brief adherence."""
    items = find_ads_to_score()
    logger.info("Found %d ads to score for brief adherence", len(items))

    if dry_run:
        for item in items:
            media = "video" if item["video_path"] else ("image" if item["image_path"] else "copy-only")
            config = item["session_config"]
            logger.info(
                "  [DRY RUN] %s in %s (%s) — audience=%s persona=%s",
                item["ad_id"], item["session_id"], media,
                config.get("audience", "?"), config.get("persona", "?"),
            )
        return

    if not items:
        logger.info("Nothing to score — all ads already have BriefAdherenceScored events")
        return

    from evaluate.brief_adherence import score_brief_adherence

    scored = 0
    failed = 0
    total_tokens = 0

    for i, item in enumerate(items, 1):
        media = "video" if item["video_path"] else ("image" if item["image_path"] else "copy-only")
        logger.info(
            "[%d/%d] Scoring %s (%s)...",
            i, len(items), item["ad_id"], media,
        )

        try:
            result = score_brief_adherence(
                ad_copy=item["copy"],
                session_config=item["session_config"],
                ad_id=item["ad_id"],
                image_path=item["image_path"],
                video_path=item["video_path"],
            )

            if result.avg_score == 0.0:
                logger.warning("  Zero score returned — skipping ledger write")
                failed += 1
                continue

            log_event(item["ledger_path"], {
                "event_type": "BriefAdherenceScored",
                "ad_id": item["ad_id"],
                "brief_id": item["brief_id"],
                "cycle_number": 0,
                "action": "brief_adherence_backfill",
                "tokens_consumed": result.tokens_consumed,
                "model_used": "gemini-2.0-flash",
                "seed": "0",
                "outputs": {
                    "scores": result.scores,
                    "avg_score": result.avg_score,
                    "rationales": result.rationales,
                },
            })

            scored += 1
            total_tokens += result.tokens_consumed
            logger.info(
                "  Scored: avg=%.1f (audience=%.1f goal=%.1f persona=%.1f message=%.1f format=%.1f) tokens=%d",
                result.avg_score,
                result.scores.get("audience_match", 0),
                result.scores.get("goal_alignment", 0),
                result.scores.get("persona_fit", 0),
                result.scores.get("message_delivery", 0),
                result.scores.get("format_adherence", 0),
                result.tokens_consumed,
            )

            # Pause between API calls
            if i < len(items):
                time.sleep(1.5)

        except Exception as e:
            logger.error("  Failed to score %s: %s", item["ad_id"], e)
            failed += 1

    logger.info(
        "Backfill complete: %d scored, %d failed, %d total tokens",
        scored, failed, total_tokens,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill brief adherence scores")
    parser.add_argument("--dry-run", action="store_true", help="List ads without scoring")
    args = parser.parse_args()

    if not os.getenv("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY not set — add it to .env")
        sys.exit(1)

    run_backfill(dry_run=args.dry_run)
