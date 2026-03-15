"""Tests for Nano Banana 2 cost-tier image model routing (P3-01).

Validates model selection logic, routed generation, per-model cost tracking,
and budget override behavior. All tests use mocked API calls.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from generate.image_generator import (
    MODEL_NANO_BANANA_2,
    MODEL_NANO_BANANA_PRO,
    ImageVariant,
    generate_image_routed,
    generate_variants_routed,
    select_image_model,
)
from evaluate.image_cost_tracker import (
    get_cost_per_model,
    get_image_cost_breakdown,
)
from iterate.ledger import log_event


# --- Model Selection ---


def test_anchor_routes_to_pro() -> None:
    """Anchor variant routes to Nano Banana Pro by default."""
    model = select_image_model("anchor")
    assert model == MODEL_NANO_BANANA_PRO


def test_tone_shift_routes_to_nb2() -> None:
    """Tone shift variant routes to Nano Banana 2 by default."""
    model = select_image_model("tone_shift")
    assert model == MODEL_NANO_BANANA_2


def test_composition_shift_routes_to_nb2() -> None:
    """Composition shift variant routes to Nano Banana 2 by default."""
    model = select_image_model("composition_shift")
    assert model == MODEL_NANO_BANANA_2


def test_budget_override_forces_nb2() -> None:
    """Low budget forces all variants (including anchor) to Nano Banana 2."""
    model = select_image_model("anchor", budget_remaining=0.50)
    assert model == MODEL_NANO_BANANA_2


def test_sufficient_budget_keeps_pro_for_anchor() -> None:
    """With enough budget, anchor still routes to Pro."""
    model = select_image_model("anchor", budget_remaining=10.0)
    assert model == MODEL_NANO_BANANA_PRO


def test_no_budget_defaults_to_normal_routing() -> None:
    """When budget_remaining is None, use default routing."""
    model = select_image_model("anchor", budget_remaining=None)
    assert model == MODEL_NANO_BANANA_PRO


# --- Routed Generation ---


@patch("generate.image_generator._call_image_api")
def test_routed_generation_returns_correct_model(mock_api: MagicMock, tmp_path: Path) -> None:
    """generate_image_routed() populates model_used based on routing."""
    mock_api.return_value = str(tmp_path / "test.png")
    (tmp_path / "test.png").write_bytes(b"fake")

    variant = generate_image_routed(
        prompt="test prompt",
        aspect_ratio="1:1",
        seed=42,
        output_path=str(tmp_path / "out.png"),
        ad_id="ad_001",
        variant_type="tone_shift",
    )
    assert isinstance(variant, ImageVariant)
    assert variant.model_used == MODEL_NANO_BANANA_2


@patch("generate.image_generator._call_image_api")
def test_routed_generation_anchor_uses_pro(mock_api: MagicMock, tmp_path: Path) -> None:
    """Anchor variant via routed generation uses Pro model."""
    mock_api.return_value = str(tmp_path / "test.png")
    (tmp_path / "test.png").write_bytes(b"fake")

    variant = generate_image_routed(
        prompt="test prompt",
        aspect_ratio="1:1",
        seed=42,
        output_path=str(tmp_path / "out.png"),
        ad_id="ad_001",
        variant_type="anchor",
    )
    assert variant.model_used == MODEL_NANO_BANANA_PRO


# --- Routed Variant Generation ---


@patch("generate.image_generator._call_image_api")
def test_generate_variants_routed_mixed_models(mock_api: MagicMock, tmp_path: Path) -> None:
    """generate_variants_routed() uses Pro for anchor, NB2 for others."""
    mock_api.return_value = str(tmp_path / "test.png")
    (tmp_path / "test.png").write_bytes(b"fake")

    mock_spec = MagicMock()
    mock_spec.aspect_ratio = "1:1"
    mock_spec.spec_hash.return_value = "abc123"

    variants = generate_variants_routed(
        visual_spec=mock_spec,
        ad_id="ad_001",
        seed=42,
        output_dir=str(tmp_path),
    )
    assert len(variants) == 3
    models = {v.variant_type: v.model_used for v in variants}
    assert models["anchor"] == MODEL_NANO_BANANA_PRO
    assert models["tone_shift"] == MODEL_NANO_BANANA_2
    assert models["composition_shift"] == MODEL_NANO_BANANA_2


# --- Cost Tracking ---


def test_cost_breakdown_separates_models(tmp_path: Path) -> None:
    """ImageCostBreakdown includes pro_tokens and flash_tokens."""
    ledger_path = str(tmp_path / "ledger.jsonl")

    # Pro generation
    log_event(ledger_path, {
        "event_type": "ImageGenerated",
        "ad_id": "ad_001",
        "brief_id": "b001",
        "cycle_number": 1,
        "action": "image-generation",
        "inputs": {},
        "outputs": {},
        "scores": {},
        "tokens_consumed": 500,
        "model_used": MODEL_NANO_BANANA_PRO,
        "seed": "42",
    })
    # Flash generation
    log_event(ledger_path, {
        "event_type": "ImageGenerated",
        "ad_id": "ad_001",
        "brief_id": "b001",
        "cycle_number": 1,
        "action": "image-generation",
        "inputs": {},
        "outputs": {},
        "scores": {},
        "tokens_consumed": 200,
        "model_used": MODEL_NANO_BANANA_2,
        "seed": "43",
    })

    breakdown = get_image_cost_breakdown("ad_001", ledger_path)
    assert breakdown.pro_tokens == 500
    assert breakdown.flash_tokens == 200
    assert breakdown.generation_tokens == 700


def test_get_cost_per_model(tmp_path: Path) -> None:
    """get_cost_per_model() aggregates tokens by model_used."""
    ledger_path = str(tmp_path / "ledger.jsonl")

    for i, (model, tokens) in enumerate([
        (MODEL_NANO_BANANA_PRO, 500),
        (MODEL_NANO_BANANA_2, 200),
        (MODEL_NANO_BANANA_2, 150),
        (MODEL_NANO_BANANA_PRO, 300),
    ]):
        log_event(ledger_path, {
            "event_type": "ImageGenerated",
            "ad_id": f"ad_{i:03d}",
            "brief_id": "b001",
            "cycle_number": 1,
            "action": "image-generation",
            "inputs": {},
            "outputs": {},
            "scores": {},
            "tokens_consumed": tokens,
            "model_used": model,
            "seed": str(i),
        })

    costs = get_cost_per_model(ledger_path)
    assert costs[MODEL_NANO_BANANA_PRO] == 800
    assert costs[MODEL_NANO_BANANA_2] == 350


def test_get_cost_per_model_empty_ledger(tmp_path: Path) -> None:
    """get_cost_per_model() returns empty dict for empty ledger."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    Path(ledger_path).touch()
    costs = get_cost_per_model(ledger_path)
    assert costs == {}
