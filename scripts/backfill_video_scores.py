#!/usr/bin/env python3
"""Backfill video quality scores for all selected videos on disk.

Reads session ledgers, finds VideoSelected events with winner_video_path,
runs the PD-14 video scorer on each, and appends VideoScored events.

Usage:
    python scripts/backfill_video_scores.py [--dry-run]
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


def find_videos_to_score() -> list[dict]:
    """Find all selected videos that haven't been scored yet."""
    session_ledgers = sorted(Path("data/sessions").glob("*/ledger.jsonl"))
    to_score = []

    for ledger_path in session_ledgers:
        session_id = ledger_path.parent.name
        events = read_events(str(ledger_path))

        already_scored = set(
            e.get("ad_id") for e in events if e.get("event_type") == "VideoScored"
        )

        copy_by_ad: dict[str, dict] = {}
        for e in events:
            if e.get("event_type") in ("AdGenerated", "AdRegenerated"):
                copy_by_ad[e.get("ad_id", "")] = e.get("outputs", {})

        for e in events:
            if e.get("event_type") != "VideoSelected":
                continue
            ad_id = e.get("ad_id", "")
            if ad_id in already_scored:
                continue
            video_path = e.get("outputs", {}).get("winner_video_path")
            if not video_path or not Path(video_path).exists():
                continue

            to_score.append({
                "session_id": session_id,
                "ad_id": ad_id,
                "brief_id": e.get("brief_id", ""),
                "video_path": video_path,
                "copy": copy_by_ad.get(ad_id, {}),
                "ledger_path": str(ledger_path),
            })

    return to_score


def run_backfill(dry_run: bool = False) -> None:
    """Score all unscored videos and append events to session ledgers."""
    items = find_videos_to_score()
    logger.info("Found %d videos to score", len(items))

    if dry_run:
        for item in items:
            logger.info(
                "  [DRY RUN] Would score %s (%s) in %s",
                item["ad_id"], Path(item["video_path"]).name, item["session_id"],
            )
        return

    if not items:
        logger.info("Nothing to score — all videos already have VideoScored events")
        return

    from evaluate.video_scorer import score_video

    scored = 0
    failed = 0
    total_tokens = 0

    for i, item in enumerate(items, 1):
        logger.info(
            "[%d/%d] Scoring %s (%s)...",
            i, len(items), item["ad_id"], Path(item["video_path"]).name,
        )

        try:
            result = score_video(
                video_path=item["video_path"],
                ad_copy=item["copy"],
                ad_id=item["ad_id"],
            )

            if result.avg_score == 0.0:
                logger.warning("  Zero score returned — skipping ledger write")
                failed += 1
                continue

            log_event(item["ledger_path"], {
                "event_type": "VideoScored",
                "ad_id": item["ad_id"],
                "brief_id": item["brief_id"],
                "cycle_number": 0,
                "action": "video_scored_backfill",
                "tokens_consumed": result.tokens_consumed,
                "model_used": "gemini-2.0-flash",
                "seed": "0",
                "outputs": {
                    "video_path": item["video_path"],
                    "video_scores": result.scores,
                    "video_avg_score": result.avg_score,
                    "rationales": result.rationales,
                },
            })

            scored += 1
            total_tokens += result.tokens_consumed
            logger.info(
                "  Scored: avg=%.1f (hook=%.1f quality=%.1f narrative=%.1f coherence=%.1f ugc=%.1f) tokens=%d",
                result.avg_score,
                result.scores.get("hook_strength", 0),
                result.scores.get("visual_quality", 0),
                result.scores.get("narrative_flow", 0),
                result.scores.get("copy_video_coherence", 0),
                result.scores.get("ugc_authenticity", 0),
                result.tokens_consumed,
            )

            # Longer pause for video — upload + processing takes more server resources
            if i < len(items):
                time.sleep(3)

        except Exception as e:
            logger.error("  Failed to score %s: %s", item["ad_id"], e)
            failed += 1

    logger.info(
        "Backfill complete: %d scored, %d failed, %d total tokens",
        scored, failed, total_tokens,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill video quality scores")
    parser.add_argument("--dry-run", action="store_true", help="List videos without scoring")
    args = parser.parse_args()

    if not os.getenv("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY not set — add it to .env")
        sys.exit(1)

    run_backfill(dry_run=args.dry_run)
