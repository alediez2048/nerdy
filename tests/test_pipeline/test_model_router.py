"""Tests for tiered model routing (P1-06)."""

from __future__ import annotations

import json

import pytest

from generate.model_router import (
    RoutingDecision,
    get_model_for_stage,
    get_routing_stats,
    route_ad,
)


def _make_config(lower: float = 5.5, upper: float = 7.0) -> dict:
    """Helper: build a config dict with improvable_range."""
    return {
        "improvable_range": [lower, upper],
        "ledger_path": "data/ledger.jsonl",
    }


# --- Routing Decision Tests ---


def test_score_below_lower_bound_discards() -> None:
    """Score < 5.5 routes to discard."""
    decision = route_ad(
        ad_id="ad_001",
        aggregate_score=4.0,
        campaign_goal="conversion",
        config=_make_config(),
    )
    assert decision.decision == "discard"
    assert decision.ad_id == "ad_001"
    assert decision.score == 4.0


def test_score_above_upper_bound_publishes() -> None:
    """Score >= 7.0 routes to publish."""
    decision = route_ad(
        ad_id="ad_002",
        aggregate_score=8.5,
        campaign_goal="conversion",
        config=_make_config(),
    )
    assert decision.decision == "publish"


def test_score_in_improvable_range_escalates() -> None:
    """Score in [5.5, 7.0) routes to escalate."""
    decision = route_ad(
        ad_id="ad_003",
        aggregate_score=6.2,
        campaign_goal="awareness",
        config=_make_config(),
    )
    assert decision.decision == "escalate"
    assert decision.model_used == "gemini-2.0-pro"


def test_boundary_lower_exact_escalates() -> None:
    """Score exactly at lower bound (5.5) should escalate, not discard."""
    decision = route_ad(
        ad_id="ad_004",
        aggregate_score=5.5,
        campaign_goal="conversion",
        config=_make_config(),
    )
    assert decision.decision == "escalate"


def test_boundary_upper_exact_publishes() -> None:
    """Score exactly at upper bound (7.0) should publish, not escalate."""
    decision = route_ad(
        ad_id="ad_005",
        aggregate_score=7.0,
        campaign_goal="conversion",
        config=_make_config(),
    )
    assert decision.decision == "publish"


def test_custom_improvable_range_overrides_defaults() -> None:
    """Custom config thresholds override the default [5.5, 7.0]."""
    config = _make_config(lower=4.0, upper=8.0)
    # 6.5 would normally publish with default range, but with [4.0, 8.0] it escalates
    decision = route_ad(
        ad_id="ad_006",
        aggregate_score=6.5,
        campaign_goal="conversion",
        config=config,
    )
    assert decision.decision == "escalate"

    # 3.5 would discard even with widened range
    decision2 = route_ad(
        ad_id="ad_007",
        aggregate_score=3.5,
        campaign_goal="conversion",
        config=config,
    )
    assert decision2.decision == "discard"


def test_routing_decision_has_reason() -> None:
    """Every routing decision includes a human-readable reason."""
    decision = route_ad(
        ad_id="ad_008",
        aggregate_score=6.0,
        campaign_goal="conversion",
        config=_make_config(),
    )
    assert isinstance(decision.reason, str)
    assert len(decision.reason) > 10


def test_routing_decision_logs_to_ledger(tmp_path: pytest.TempPathFactory) -> None:
    """Routing decisions are logged to the ledger."""
    ledger = str(tmp_path / "ledger.jsonl")
    config = _make_config()
    config["ledger_path"] = ledger

    route_ad(
        ad_id="ad_009",
        aggregate_score=6.0,
        campaign_goal="conversion",
        config=config,
        ledger_path=ledger,
    )

    with open(ledger) as f:
        events = [json.loads(line) for line in f]

    assert len(events) == 1
    assert events[0]["event_type"] == "AdRouted"
    assert events[0]["ad_id"] == "ad_009"
    assert events[0]["action"] == "triage"


# --- Model Selection Tests ---


def test_get_model_for_stage_first_draft() -> None:
    """First draft always uses Flash."""
    model = get_model_for_stage("first_draft")
    assert model == "gemini-2.0-flash"


def test_get_model_for_stage_escalation() -> None:
    """Escalation stage uses Pro."""
    model = get_model_for_stage("escalation")
    assert model == "gemini-2.0-pro"


def test_get_model_for_stage_evaluation() -> None:
    """Evaluation always uses Flash."""
    model = get_model_for_stage("evaluation")
    assert model == "gemini-2.0-flash"


# --- Routing Stats Tests ---


def test_get_routing_stats_computes_counts(tmp_path: pytest.TempPathFactory) -> None:
    """get_routing_stats correctly counts discard/escalate/publish from ledger."""
    ledger = str(tmp_path / "stats_ledger.jsonl")
    config = _make_config()
    config["ledger_path"] = ledger

    # Route 5 ads with different scores
    scores = [3.0, 4.5, 6.0, 6.5, 8.0]
    for i, score in enumerate(scores):
        route_ad(
            ad_id=f"ad_{i:03d}",
            aggregate_score=score,
            campaign_goal="conversion",
            config=config,
            ledger_path=ledger,
        )

    stats = get_routing_stats(ledger)
    assert stats["total_routed"] == 5
    assert stats["discarded"] == 2  # 3.0, 4.5
    assert stats["escalated"] == 2  # 6.0, 6.5
    assert stats["published"] == 1  # 8.0
