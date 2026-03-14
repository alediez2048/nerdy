"""Full ad assembly — collects copy, image, and metadata from ledger (P1-18).

Reads the append-only ledger to assemble each published ad into a structured
object with copy JSON, winning image path, text scores, and image selection
metadata. State Is Sacred (Pillar 5) — all data comes from the ledger.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from iterate.ledger import read_events_filtered

logger = logging.getLogger(__name__)


@dataclass
class AssembledAd:
    """A fully assembled ad ready for export."""

    ad_id: str
    copy: dict[str, str]
    winning_image_path: str
    text_scores: dict[str, float]
    image_selection: dict[str, Any]
    generation_metadata: dict[str, Any] = field(default_factory=dict)


def assemble_ad(ad_id: str, ledger_path: str) -> AssembledAd:
    """Assemble a published ad from ledger events.

    Collects copy, winning image, text scores, and image selection metadata.

    Args:
        ad_id: The ad identifier.
        ledger_path: Path to the JSONL ledger.

    Returns:
        AssembledAd with all components populated.
    """
    # Get copy from AdGenerated event
    gen_events = read_events_filtered(ledger_path, event_type="AdGenerated", ad_id=ad_id)
    copy: dict[str, str] = {}
    gen_meta: dict[str, Any] = {}
    if gen_events:
        latest = gen_events[-1]
        outputs = latest.get("outputs", {})
        copy = {
            "primary_text": outputs.get("primary_text", ""),
            "headline": outputs.get("headline", ""),
            "description": outputs.get("description", ""),
            "cta": outputs.get("cta", ""),
        }
        gen_meta = {
            "cycle_number": latest.get("cycle_number", 0),
            "seed": latest.get("seed", ""),
            "model_used": latest.get("model_used", ""),
            "tokens_consumed": latest.get("tokens_consumed", 0),
        }

    # Get text scores from AdEvaluated event
    eval_events = read_events_filtered(ledger_path, event_type="AdEvaluated", ad_id=ad_id)
    text_scores: dict[str, float] = {}
    if eval_events:
        text_scores = eval_events[-1].get("scores", {})

    # Get winning image from ImageSelected event
    select_events = read_events_filtered(ledger_path, event_type="ImageSelected", ad_id=ad_id)
    winning_image_path = ""
    image_selection: dict[str, Any] = {}
    if select_events:
        latest = select_events[-1]
        outputs = latest.get("outputs", {})
        winning_image_path = outputs.get("winner_image_path", "")
        image_selection = {
            "winner_variant": outputs.get("winner_variant", ""),
            "composite_score": outputs.get("composite_score", 0.0),
            "attribute_pass_pct": outputs.get("attribute_pass_pct", 0.0),
            "coherence_avg": outputs.get("coherence_avg", 0.0),
        }

    return AssembledAd(
        ad_id=ad_id,
        copy=copy,
        winning_image_path=winning_image_path,
        text_scores=text_scores,
        image_selection=image_selection,
        generation_metadata=gen_meta,
    )


def is_publishable(ad_id: str, ledger_path: str) -> bool:
    """Check if an ad is publishable (passed text + has winning image, not blocked).

    Args:
        ad_id: The ad identifier.
        ledger_path: Path to the JSONL ledger.

    Returns:
        True if ad has AdPublished event, ImageSelected event, and no ImageBlocked event.
    """
    published = read_events_filtered(ledger_path, event_type="AdPublished", ad_id=ad_id)
    if not published:
        return False

    selected = read_events_filtered(ledger_path, event_type="ImageSelected", ad_id=ad_id)
    if not selected:
        return False

    blocked = read_events_filtered(ledger_path, event_type="ImageBlocked", ad_id=ad_id)
    if blocked:
        return False

    return True
