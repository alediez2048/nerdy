"""Image cost tracking + unified cost metrics (P1-19, R1-Q7).

Extends the token attribution engine (P1-11) to track image pipeline costs:
per-image, per-variant, per-regen, per-aspect-ratio. Computes unified
cost-per-publishable-ad across text + image. Tracks variant win rates.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass

from iterate.ledger import log_event, read_events, read_events_filtered

logger = logging.getLogger(__name__)

# Image-related event types
_IMAGE_GEN_EVENTS = {"ImageGenerated"}
_IMAGE_EVAL_EVENTS = {"ImageEvaluated"}
_TEXT_EVENTS = {"AdGenerated", "BriefExpanded", "AdEvaluated", "AdRegenerated"}


@dataclass
class ImageCostBreakdown:
    """Cost breakdown for image pipeline of a single ad."""

    ad_id: str
    generation_tokens: int
    evaluation_tokens: int
    regen_tokens: int
    total_image_tokens: int


@dataclass
class UnifiedCost:
    """Combined text + image cost for a single ad."""

    ad_id: str
    text_tokens: int
    image_tokens: int
    total_tokens: int


def get_image_cost_breakdown(ad_id: str, ledger_path: str) -> ImageCostBreakdown:
    """Compute image pipeline cost breakdown for an ad.

    Args:
        ad_id: The ad identifier.
        ledger_path: Path to the JSONL ledger.

    Returns:
        ImageCostBreakdown with generation, evaluation, and regen tokens.
    """
    events = read_events(ledger_path)
    ad_events = [e for e in events if e.get("ad_id") == ad_id]

    generation_tokens = 0
    evaluation_tokens = 0
    regen_tokens = 0

    for event in ad_events:
        event_type = event.get("event_type", "")
        tokens = event.get("tokens_consumed", 0)

        if event_type in _IMAGE_GEN_EVENTS:
            action = event.get("action", "")
            if action == "image-regen" or event.get("outputs", {}).get("is_regen"):
                regen_tokens += tokens
            else:
                generation_tokens += tokens
        elif event_type in _IMAGE_EVAL_EVENTS:
            evaluation_tokens += tokens

    total = generation_tokens + evaluation_tokens + regen_tokens

    return ImageCostBreakdown(
        ad_id=ad_id,
        generation_tokens=generation_tokens,
        evaluation_tokens=evaluation_tokens,
        regen_tokens=regen_tokens,
        total_image_tokens=total,
    )


def get_unified_cost(ad_id: str, ledger_path: str) -> UnifiedCost:
    """Compute unified text + image cost for an ad.

    Args:
        ad_id: The ad identifier.
        ledger_path: Path to the JSONL ledger.

    Returns:
        UnifiedCost with text, image, and total tokens.
    """
    events = read_events(ledger_path)
    ad_events = [e for e in events if e.get("ad_id") == ad_id]

    text_tokens = 0
    image_tokens = 0

    for event in ad_events:
        event_type = event.get("event_type", "")
        tokens = event.get("tokens_consumed", 0)

        if event_type in _TEXT_EVENTS:
            text_tokens += tokens
        elif event_type in _IMAGE_GEN_EVENTS or event_type in _IMAGE_EVAL_EVENTS:
            image_tokens += tokens

    return UnifiedCost(
        ad_id=ad_id,
        text_tokens=text_tokens,
        image_tokens=image_tokens,
        total_tokens=text_tokens + image_tokens,
    )


def track_variant_selection(
    ad_id: str,
    winner_type: str,
    all_types: list[str],
    ledger_path: str,
) -> None:
    """Record which variant strategy won Pareto selection.

    Args:
        ad_id: The ad identifier.
        winner_type: The winning variant type.
        all_types: All variant types that competed.
        ledger_path: Path to the JSONL ledger.
    """
    log_event(ledger_path, {
        "event_type": "VariantSelected",
        "ad_id": ad_id,
        "brief_id": "",
        "cycle_number": 0,
        "action": "variant-selection",
        "inputs": {"all_types": all_types},
        "outputs": {"winner_type": winner_type},
        "scores": {},
        "tokens_consumed": 0,
        "model_used": "",
        "seed": "",
    })


def get_variant_win_rates(ledger_path: str) -> dict[str, float]:
    """Compute win rate per variant type from ledger.

    Args:
        ledger_path: Path to the JSONL ledger.

    Returns:
        Dict mapping variant type to win rate (0.0–1.0).
    """
    events = read_events_filtered(ledger_path, event_type="VariantSelected")

    if not events:
        return {}

    wins: dict[str, int] = defaultdict(int)
    total = len(events)

    for event in events:
        winner = event.get("outputs", {}).get("winner_type", "")
        if winner:
            wins[winner] += 1

    rates = {vtype: count / total for vtype, count in wins.items()}

    # Log dominance warning
    for vtype, rate in rates.items():
        if rate > 0.8:
            logger.warning(
                "Variant %s dominates at %.0f%% — consider reducing to 2 variants",
                vtype, rate * 100,
            )

    return rates
