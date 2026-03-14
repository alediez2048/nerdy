"""Tests for token attribution engine (P1-11)."""

from __future__ import annotations

import json

import pytest

from iterate.token_tracker import (
    TokenSummary,
    aggregate_by_model,
    aggregate_by_stage,
    cost_per_publishable_ad,
    get_stage_from_event,
    get_token_summary,
    marginal_quality_gain,
)


def _write_ledger(path: str, events: list[dict]) -> None:
    with open(path, "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


def _base_event(event_type: str, ad_id: str, tokens: int, model: str = "gemini-2.0-flash", **extra) -> dict:
    """Build a minimal ledger event."""
    event = {
        "event_type": event_type,
        "ad_id": ad_id,
        "brief_id": "b001",
        "cycle_number": 0,
        "action": "test",
        "tokens_consumed": tokens,
        "model_used": model,
        "seed": "0",
        "inputs": {},
        "outputs": {},
    }
    event.update(extra)
    return event


# --- get_stage_from_event Tests ---


def test_stage_mapping_known_types() -> None:
    """All known event types map to correct stages."""
    assert get_stage_from_event({"event_type": "AdGenerated"}) == "generation"
    assert get_stage_from_event({"event_type": "BriefExpanded"}) == "generation"
    assert get_stage_from_event({"event_type": "AdEvaluated"}) == "evaluation"
    assert get_stage_from_event({"event_type": "AdRegenerated"}) == "regeneration"
    assert get_stage_from_event({"event_type": "ContextDistilled"}) == "distillation"
    assert get_stage_from_event({"event_type": "AdRouted"}) == "routing"
    assert get_stage_from_event({"event_type": "BriefMutated"}) == "mutation"


def test_stage_mapping_unknown_returns_other() -> None:
    """Unknown event types return 'other'."""
    assert get_stage_from_event({"event_type": "SomethingNew"}) == "other"
    assert get_stage_from_event({}) == "other"


# --- aggregate_by_stage Tests ---


def test_aggregate_by_stage_sums_correctly(tmp_path: pytest.TempPathFactory) -> None:
    """Tokens are summed correctly by stage."""
    ledger = str(tmp_path / "ledger.jsonl")
    events = [
        _base_event("AdGenerated", "ad_001", 100),
        _base_event("AdEvaluated", "ad_001", 200),
        _base_event("AdGenerated", "ad_002", 150),
        _base_event("AdRegenerated", "ad_001", 300),
    ]
    _write_ledger(ledger, events)

    result = aggregate_by_stage(ledger)
    assert result["generation"] == 250  # 100 + 150
    assert result["evaluation"] == 200
    assert result["regeneration"] == 300


# --- aggregate_by_model Tests ---


def test_aggregate_by_model_separates_flash_pro(tmp_path: pytest.TempPathFactory) -> None:
    """Flash and Pro tokens tracked separately."""
    ledger = str(tmp_path / "ledger.jsonl")
    events = [
        _base_event("AdGenerated", "ad_001", 100, model="gemini-2.0-flash"),
        _base_event("AdRegenerated", "ad_001", 500, model="gemini-2.0-pro"),
        _base_event("AdEvaluated", "ad_001", 200, model="gemini-2.0-flash"),
    ]
    _write_ledger(ledger, events)

    result = aggregate_by_model(ledger)
    assert result["gemini-2.0-flash"] == 300
    assert result["gemini-2.0-pro"] == 500


# --- cost_per_publishable_ad Tests ---


def test_cost_per_publishable_ad_correct_ratio(tmp_path: pytest.TempPathFactory) -> None:
    """Tokens / published count computed correctly."""
    ledger = str(tmp_path / "ledger.jsonl")
    events = [
        _base_event("AdGenerated", "ad_001", 100),
        _base_event("AdEvaluated", "ad_001", 200),
        _base_event("AdPublished", "ad_001", 0),
        _base_event("AdGenerated", "ad_002", 100),
        _base_event("AdEvaluated", "ad_002", 200),
        _base_event("AdPublished", "ad_002", 0),
        _base_event("AdGenerated", "ad_003", 100),
        _base_event("AdDiscarded", "ad_003", 0),
    ]
    _write_ledger(ledger, events)

    result = cost_per_publishable_ad(ledger)
    # Total tokens: 700, published: 2 → 350
    assert abs(result - 350.0) < 0.01


def test_cost_per_publishable_ad_zero_published_returns_inf(tmp_path: pytest.TempPathFactory) -> None:
    """Returns inf when no ads published."""
    ledger = str(tmp_path / "ledger.jsonl")
    events = [
        _base_event("AdGenerated", "ad_001", 100),
        _base_event("AdDiscarded", "ad_001", 0),
    ]
    _write_ledger(ledger, events)

    result = cost_per_publishable_ad(ledger)
    assert result == float("inf")


# --- marginal_quality_gain Tests ---


def test_marginal_quality_gain_with_regen(tmp_path: pytest.TempPathFactory) -> None:
    """Returns correct deltas for an ad with regeneration cycles."""
    ledger = str(tmp_path / "ledger.jsonl")
    events = [
        _base_event("AdEvaluated", "ad_001", 200, cycle_number=1,
                     outputs={"aggregate_score": 6.0}),
        _base_event("AdEvaluated", "ad_001", 200, cycle_number=2,
                     outputs={"aggregate_score": 7.2}),
        _base_event("AdEvaluated", "ad_001", 200, cycle_number=3,
                     outputs={"aggregate_score": 7.5}),
    ]
    _write_ledger(ledger, events)

    deltas = marginal_quality_gain(ledger, "ad_001")
    assert len(deltas) == 2
    assert abs(deltas[0] - 1.2) < 0.01  # 7.2 - 6.0
    assert abs(deltas[1] - 0.3) < 0.01  # 7.5 - 7.2


def test_marginal_quality_gain_no_regen(tmp_path: pytest.TempPathFactory) -> None:
    """Returns empty list for first-pass publish (no regeneration)."""
    ledger = str(tmp_path / "ledger.jsonl")
    events = [
        _base_event("AdEvaluated", "ad_001", 200, cycle_number=1,
                     outputs={"aggregate_score": 8.0}),
    ]
    _write_ledger(ledger, events)

    deltas = marginal_quality_gain(ledger, "ad_001")
    assert deltas == []


# --- get_token_summary Tests ---


def test_get_token_summary_aggregates_all(tmp_path: pytest.TempPathFactory) -> None:
    """Summary includes all metrics."""
    ledger = str(tmp_path / "ledger.jsonl")
    events = [
        _base_event("AdGenerated", "ad_001", 100, model="gemini-2.0-flash"),
        _base_event("AdEvaluated", "ad_001", 200, model="gemini-2.0-flash"),
        _base_event("AdPublished", "ad_001", 0),
        _base_event("AdGenerated", "ad_002", 150, model="gemini-2.0-flash"),
        _base_event("AdEvaluated", "ad_002", 200, model="gemini-2.0-pro"),
        _base_event("AdDiscarded", "ad_002", 0),
    ]
    _write_ledger(ledger, events)

    summary = get_token_summary(ledger)
    assert isinstance(summary, TokenSummary)
    assert summary.total_tokens == 650
    assert summary.ads_published == 1
    assert summary.ads_discarded == 1
    assert summary.cost_per_published == 650.0
    assert "generation" in summary.by_stage
    assert "evaluation" in summary.by_stage
