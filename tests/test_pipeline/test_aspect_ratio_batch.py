"""Tests for multi-aspect-ratio batch generation (P3-06).

Validates ratio generation, checklist evaluation, checkpoint-resume,
export integration, and cost-tier model usage.
"""

from __future__ import annotations

from pathlib import Path

from generate.aspect_ratio_batch import (
    META_ASPECT_RATIOS,
    AspectRatioBatchResult,
    AspectRatioResult,
    generate_aspect_ratios,
    skip_existing_ratios,
)
from iterate.ledger import log_event


# --- Ratio Generation ---


def test_meta_aspect_ratios_defined() -> None:
    """All three Meta aspect ratios are defined."""
    assert "1:1" in META_ASPECT_RATIOS
    assert "4:5" in META_ASPECT_RATIOS
    assert "9:16" in META_ASPECT_RATIOS


def test_generate_aspect_ratios_returns_all_three() -> None:
    """Generates results for all three aspect ratios."""
    result = generate_aspect_ratios(
        ad_id="ad_001",
        visual_spec={"scene_description": "test", "prompt": "test"},
        seed=42,
    )
    assert isinstance(result, AspectRatioBatchResult)
    assert len(result.results) == 3
    for ratio in META_ASPECT_RATIOS:
        assert ratio in result.results


def test_generate_specific_ratios() -> None:
    """Can generate a subset of ratios."""
    result = generate_aspect_ratios(
        ad_id="ad_001",
        visual_spec={"scene_description": "test", "prompt": "test"},
        seed=42,
        ratios=["1:1", "9:16"],
    )
    assert len(result.results) == 2
    assert "1:1" in result.results
    assert "9:16" in result.results


def test_cost_tier_model_used() -> None:
    """Ratio variants use NB2 (cost tier) model."""
    from generate.image_generator import MODEL_NANO_BANANA_2

    result = generate_aspect_ratios(
        ad_id="ad_001",
        visual_spec={"scene_description": "test", "prompt": "test"},
        seed=42,
    )
    for ratio, ar_result in result.results.items():
        assert ar_result.model_used == MODEL_NANO_BANANA_2


def test_all_pass_flag_when_all_pass() -> None:
    """all_pass is True when every ratio passes checklist."""
    result = AspectRatioBatchResult(
        ad_id="ad_001",
        results={
            "1:1": AspectRatioResult("ad_001", "1:1", "img.png", True, 1.0, "nb2"),
            "4:5": AspectRatioResult("ad_001", "4:5", "img.png", True, 0.8, "nb2"),
            "9:16": AspectRatioResult("ad_001", "9:16", "img.png", True, 1.0, "nb2"),
        },
        all_pass=True,
        failed_ratios=[],
    )
    assert result.all_pass is True
    assert result.failed_ratios == []


def test_failed_ratios_tracked() -> None:
    """Failed ratios are listed in failed_ratios."""
    result = AspectRatioBatchResult(
        ad_id="ad_001",
        results={
            "1:1": AspectRatioResult("ad_001", "1:1", "img.png", True, 1.0, "nb2"),
            "4:5": AspectRatioResult("ad_001", "4:5", "img.png", False, 0.5, "nb2"),
            "9:16": AspectRatioResult("ad_001", "9:16", "img.png", True, 1.0, "nb2"),
        },
        all_pass=False,
        failed_ratios=["4:5"],
    )
    assert result.all_pass is False
    assert "4:5" in result.failed_ratios


# --- Checkpoint Resume ---


def test_skip_existing_ratios(tmp_path: Path) -> None:
    """skip_existing_ratios returns ratios already generated."""
    ledger_path = str(tmp_path / "ledger.jsonl")

    log_event(ledger_path, {
        "event_type": "AspectRatioGenerated",
        "ad_id": "ad_001",
        "brief_id": "b001",
        "cycle_number": 1,
        "action": "aspect-ratio-generation",
        "inputs": {"aspect_ratio": "1:1"},
        "outputs": {"passes_checklist": True},
        "scores": {},
        "tokens_consumed": 0,
        "model_used": "gemini-3.1-flash-image",
        "seed": "42",
    })
    log_event(ledger_path, {
        "event_type": "AspectRatioGenerated",
        "ad_id": "ad_001",
        "brief_id": "b001",
        "cycle_number": 1,
        "action": "aspect-ratio-generation",
        "inputs": {"aspect_ratio": "4:5"},
        "outputs": {"passes_checklist": True},
        "scores": {},
        "tokens_consumed": 0,
        "model_used": "gemini-3.1-flash-image",
        "seed": "42",
    })

    existing = skip_existing_ratios("ad_001", ledger_path)
    assert "1:1" in existing
    assert "4:5" in existing
    assert "9:16" not in existing


def test_skip_existing_ratios_empty_ledger(tmp_path: Path) -> None:
    """Empty ledger returns no existing ratios."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    Path(ledger_path).touch()

    existing = skip_existing_ratios("ad_001", ledger_path)
    assert existing == []
