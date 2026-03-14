"""Tests for image cost tracking + unified cost metrics (P1-19)."""

from __future__ import annotations

from pathlib import Path

from iterate.ledger import log_event
from evaluate.image_cost_tracker import (
    ImageCostBreakdown,
    UnifiedCost,
    get_image_cost_breakdown,
    get_unified_cost,
    track_variant_selection,
    get_variant_win_rates,
)


def _log_image_event(
    ledger_path: str,
    ad_id: str = "ad_001",
    action: str = "image-generation",
    variant_type: str = "anchor",
    tokens: int = 1000,
    is_regen: bool = False,
    aspect_ratio: str = "1:1",
) -> None:
    """Log an image-related event to the ledger."""
    log_event(ledger_path, {
        "event_type": "ImageGenerated",
        "ad_id": ad_id,
        "brief_id": "b001",
        "cycle_number": 1,
        "action": "image-regen" if is_regen else "image-generation",
        "inputs": {"variant_type": variant_type, "aspect_ratio": aspect_ratio},
        "outputs": {"is_regen": is_regen},
        "scores": {},
        "tokens_consumed": tokens,
        "model_used": "gemini-2.0-flash-preview-image-generation",
        "seed": "42",
    })


def _log_eval_event(
    ledger_path: str,
    ad_id: str = "ad_001",
    eval_type: str = "attribute_eval",
    tokens: int = 200,
) -> None:
    """Log an image evaluation event to the ledger."""
    log_event(ledger_path, {
        "event_type": "ImageEvaluated",
        "ad_id": ad_id,
        "brief_id": "b001",
        "cycle_number": 1,
        "action": eval_type,
        "inputs": {},
        "outputs": {},
        "scores": {},
        "tokens_consumed": tokens,
        "model_used": "gemini-2.0-flash",
        "seed": "42",
    })


def _log_text_event(
    ledger_path: str,
    ad_id: str = "ad_001",
    tokens: int = 500,
) -> None:
    """Log a text generation event to the ledger."""
    log_event(ledger_path, {
        "event_type": "AdGenerated",
        "ad_id": ad_id,
        "brief_id": "b001",
        "cycle_number": 1,
        "action": "generation",
        "inputs": {},
        "outputs": {},
        "scores": {},
        "tokens_consumed": tokens,
        "model_used": "gemini-2.0-flash",
        "seed": "42",
    })


# --- Image Cost Breakdown ---


def test_image_cost_breakdown_generation(tmp_path: Path) -> None:
    """Image generation costs tracked with correct per-variant totals."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _log_image_event(ledger_path, variant_type="anchor", tokens=1000)
    _log_image_event(ledger_path, variant_type="tone_shift", tokens=1000)
    _log_image_event(ledger_path, variant_type="composition_shift", tokens=1000)

    breakdown = get_image_cost_breakdown("ad_001", ledger_path)
    assert isinstance(breakdown, ImageCostBreakdown)
    assert breakdown.generation_tokens == 3000
    assert breakdown.total_image_tokens == 3000


def test_image_cost_breakdown_evaluation(tmp_path: Path) -> None:
    """Image evaluation costs tracked separately."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _log_eval_event(ledger_path, eval_type="attribute_eval", tokens=200)
    _log_eval_event(ledger_path, eval_type="coherence_eval", tokens=300)

    breakdown = get_image_cost_breakdown("ad_001", ledger_path)
    assert breakdown.evaluation_tokens == 500


def test_image_cost_breakdown_regen_separate(tmp_path: Path) -> None:
    """Regen costs attributed separately from initial generation."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _log_image_event(ledger_path, variant_type="anchor", tokens=1000, is_regen=False)
    _log_image_event(ledger_path, variant_type="anchor", tokens=1000, is_regen=True)

    breakdown = get_image_cost_breakdown("ad_001", ledger_path)
    assert breakdown.generation_tokens == 1000
    assert breakdown.regen_tokens == 1000
    assert breakdown.total_image_tokens == 2000


# --- Unified Cost ---


def test_unified_cost_combines_text_and_image(tmp_path: Path) -> None:
    """Unified cost combines text + image correctly."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _log_text_event(ledger_path, tokens=500)
    _log_image_event(ledger_path, tokens=1000)
    _log_eval_event(ledger_path, tokens=200)

    cost = get_unified_cost("ad_001", ledger_path)
    assert isinstance(cost, UnifiedCost)
    assert cost.text_tokens == 500
    assert cost.image_tokens == 1200  # 1000 gen + 200 eval
    assert cost.total_tokens == 1700


# --- Variant Win Rates ---


def test_variant_win_rate_calculation(tmp_path: Path) -> None:
    """Variant win rates computed correctly."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    track_variant_selection("ad_001", "anchor", ["anchor", "tone_shift", "composition_shift"], ledger_path)
    track_variant_selection("ad_002", "anchor", ["anchor", "tone_shift", "composition_shift"], ledger_path)
    track_variant_selection("ad_003", "tone_shift", ["anchor", "tone_shift", "composition_shift"], ledger_path)

    rates = get_variant_win_rates(ledger_path)
    assert abs(rates["anchor"] - 2 / 3) < 0.01
    assert abs(rates["tone_shift"] - 1 / 3) < 0.01
    assert rates.get("composition_shift", 0.0) == 0.0


def test_variant_dominance_flag(tmp_path: Path) -> None:
    """Flags when one strategy dominates >80%."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    for i in range(9):
        track_variant_selection(f"ad_{i:03d}", "anchor", ["anchor", "tone_shift", "composition_shift"], ledger_path)
    track_variant_selection("ad_009", "tone_shift", ["anchor", "tone_shift", "composition_shift"], ledger_path)

    rates = get_variant_win_rates(ledger_path)
    # anchor wins 9/10 = 90% > 80% threshold
    assert rates["anchor"] > 0.8


def test_empty_ledger_returns_zero_costs(tmp_path: Path) -> None:
    """Empty ledger returns zero costs without errors."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    breakdown = get_image_cost_breakdown("ad_001", ledger_path)
    assert breakdown.total_image_tokens == 0
