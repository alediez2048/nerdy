#!/usr/bin/env python3
"""Backfill image quality scores for all published ads with images on disk.

Reads session ledgers, finds AdPublished events with winning_image paths,
runs the PD-13 image scorer on each, and appends ImageScored events.

Usage:
    python scripts/backfill_image_scores.py [--dry-run]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # .env vars must be set manually

from iterate.ledger import log_event, read_events

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def find_images_to_score() -> list[dict]:
    """Find all published ads with images that haven't been scored yet."""
    session_ledgers = sorted(Path("data/sessions").glob("*/ledger.jsonl"))
    to_score = []

    for ledger_path in session_ledgers:
        session_id = ledger_path.parent.name
        events = read_events(str(ledger_path))

        # Find already-scored ad_ids
        already_scored = set(
            e.get("ad_id") for e in events if e.get("event_type") == "ImageScored"
        )

        # Find AdGenerated events for copy lookup
        copy_by_ad: dict[str, dict] = {}
        for e in events:
            if e.get("event_type") in ("AdGenerated", "AdRegenerated"):
                copy_by_ad[e.get("ad_id", "")] = e.get("outputs", {})

        # Find published ads with images
        for e in events:
            if e.get("event_type") != "AdPublished":
                continue
            ad_id = e.get("ad_id", "")
            if ad_id in already_scored:
                continue
            image_path = e.get("outputs", {}).get("winning_image")
            if not image_path or not Path(image_path).exists():
                continue

            to_score.append({
                "session_id": session_id,
                "ad_id": ad_id,
                "brief_id": e.get("brief_id", ""),
                "image_path": image_path,
                "copy": copy_by_ad.get(ad_id, {}),
                "ledger_path": str(ledger_path),
            })

    return to_score


def run_backfill(dry_run: bool = False) -> None:
    """Score all unscored images and append events to session ledgers."""
    items = find_images_to_score()
    logger.info("Found %d images to score", len(items))

    if dry_run:
        for item in items:
            logger.info(
                "  [DRY RUN] Would score %s (%s) in %s",
                item["ad_id"], Path(item["image_path"]).name, item["session_id"],
            )
        return

    if not items:
        logger.info("Nothing to score — all images already have ImageScored events")
        return

    from evaluate.image_scorer import score_image

    scored = 0
    failed = 0
    total_tokens = 0

    for i, item in enumerate(items, 1):
        logger.info(
            "[%d/%d] Scoring %s (%s)...",
            i, len(items), item["ad_id"], Path(item["image_path"]).name,
        )

        try:
            result = score_image(
                image_path=item["image_path"],
                ad_copy=item["copy"],
                ad_id=item["ad_id"],
            )

            if result.avg_score == 0.0:
                logger.warning("  Zero score returned — skipping ledger write")
                failed += 1
                continue

            log_event(item["ledger_path"], {
                "event_type": "ImageScored",
                "ad_id": item["ad_id"],
                "brief_id": item["brief_id"],
                "cycle_number": 0,
                "action": "image_scored_backfill",
                "tokens_consumed": result.tokens_consumed,
                "model_used": "gemini-2.0-flash",
                "seed": "0",
                "outputs": {
                    "image_path": item["image_path"],
                    "image_scores": result.scores,
                    "image_avg_score": result.avg_score,
                    "rationales": result.rationales,
                },
            })

            scored += 1
            total_tokens += result.tokens_consumed
            logger.info(
                "  Scored: avg=%.1f (clarity=%.1f brand=%.1f emotion=%.1f coherence=%.1f platform=%.1f) tokens=%d",
                result.avg_score,
                result.scores.get("visual_clarity", 0),
                result.scores.get("brand_consistency", 0),
                result.scores.get("emotional_impact", 0),
                result.scores.get("copy_image_coherence", 0),
                result.scores.get("platform_fit", 0),
                result.tokens_consumed,
            )

            # Brief pause between API calls to respect rate limits
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
    parser = argparse.ArgumentParser(description="Backfill image quality scores")
    parser.add_argument("--dry-run", action="store_true", help="List images without scoring")
    args = parser.parse_args()

    if not os.getenv("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY not set — add it to .env")
        sys.exit(1)

    run_backfill(dry_run=args.dry_run)
