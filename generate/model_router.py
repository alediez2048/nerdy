"""Tiered model routing for cost-efficient ad processing (P1-06, R1-Q4).

Routes ads into three tiers based on weighted evaluation score:
  - **Discard** (< lower bound): Too weak to salvage — skip Pro tokens.
  - **Escalate** (lower bound to upper bound): Improvable — worth Pro spend.
  - **Publish** (>= upper bound): Already good — no further spend needed.

Thresholds are config-driven via `improvable_range` in data/config.yaml.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from iterate.ledger import log_event, read_events

logger = logging.getLogger(__name__)

_DEFAULT_IMPROVABLE_RANGE = [5.5, 7.0]

_MODEL_MAP: dict[str, str] = {
    "first_draft": "gemini-2.0-flash",
    "evaluation": "gemini-2.0-flash",
    "escalation": "gemini-2.0-pro",
    "regeneration": "gemini-2.0-pro",
}


@dataclass
class RoutingDecision:
    """Result of routing an ad to a processing tier."""

    ad_id: str
    score: float
    decision: str  # "discard" | "escalate" | "publish"
    model_used: str
    reason: str


def route_ad(
    ad_id: str,
    aggregate_score: float,
    campaign_goal: str,
    config: dict[str, Any],
    ledger_path: str | None = None,
) -> RoutingDecision:
    """Route an ad based on its weighted evaluation score.

    Args:
        ad_id: Unique ad identifier.
        aggregate_score: Weighted average from evaluate_with_weights.
        campaign_goal: "awareness" or "conversion".
        config: Config dict containing improvable_range and ledger_path.
        ledger_path: Override ledger path for logging.

    Returns:
        RoutingDecision with tier assignment and reason.
    """
    improvable_range = config.get("improvable_range", _DEFAULT_IMPROVABLE_RANGE)
    lower_bound = improvable_range[0]
    upper_bound = improvable_range[1]

    if aggregate_score < lower_bound:
        decision = RoutingDecision(
            ad_id=ad_id,
            score=aggregate_score,
            decision="discard",
            model_used="gemini-2.0-flash",
            reason=f"Score {aggregate_score:.2f} below improvable range floor {lower_bound:.1f} — not worth Pro tokens",
        )
    elif aggregate_score >= upper_bound:
        decision = RoutingDecision(
            ad_id=ad_id,
            score=aggregate_score,
            decision="publish",
            model_used="gemini-2.0-flash",
            reason=f"Score {aggregate_score:.2f} meets quality threshold {upper_bound:.1f} — publish directly",
        )
    else:
        decision = RoutingDecision(
            ad_id=ad_id,
            score=aggregate_score,
            decision="escalate",
            model_used="gemini-2.0-pro",
            reason=f"Score {aggregate_score:.2f} in improvable range [{lower_bound:.1f}, {upper_bound:.1f}) — escalate to Pro",
        )

    logger.info("Routed %s: %s (score=%.2f)", ad_id, decision.decision, aggregate_score)

    led_path = ledger_path or config.get("ledger_path", "data/ledger.jsonl")
    log_event(
        led_path,
        {
            "event_type": "AdRouted",
            "ad_id": ad_id,
            "brief_id": _extract_brief_id(ad_id),
            "cycle_number": 0,
            "action": "triage",
            "tokens_consumed": 0,
            "model_used": decision.model_used,
            "seed": "0",
            "inputs": {
                "aggregate_score": aggregate_score,
                "campaign_goal": campaign_goal,
                "improvable_range": improvable_range,
            },
            "outputs": {
                "decision": decision.decision,
                "reason": decision.reason,
            },
        },
    )

    return decision


def get_model_for_stage(stage: str) -> str:
    """Return the model identifier for a given pipeline stage.

    Args:
        stage: One of "first_draft", "evaluation", "escalation", "regeneration".

    Returns:
        Model identifier string.
    """
    return _MODEL_MAP.get(stage, "gemini-2.0-flash")


def get_routing_stats(ledger_path: str) -> dict[str, Any]:
    """Compute routing statistics from the ledger.

    Args:
        ledger_path: Path to the JSONL ledger file.

    Returns:
        Dict with total_routed, discarded, escalated, published counts.
    """
    events = read_events(ledger_path)
    routing_events = [e for e in events if e.get("event_type") == "AdRouted"]

    discarded = sum(1 for e in routing_events if e.get("outputs", {}).get("decision") == "discard")
    escalated = sum(1 for e in routing_events if e.get("outputs", {}).get("decision") == "escalate")
    published = sum(1 for e in routing_events if e.get("outputs", {}).get("decision") == "publish")

    return {
        "total_routed": len(routing_events),
        "discarded": discarded,
        "escalated": escalated,
        "published": published,
    }


def _extract_brief_id(ad_id: str) -> str:
    """Extract brief_id from ad_id format 'ad_<brief>_c<cycle>'."""
    if ad_id.startswith("ad_") and "_c" in ad_id:
        parts = ad_id.split("_")
        if len(parts) >= 2:
            return parts[1]
    return "unknown"
