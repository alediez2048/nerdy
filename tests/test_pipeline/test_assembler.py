"""Tests for full ad assembly + export (P1-18)."""

from __future__ import annotations

import json
from pathlib import Path

from output.assembler import (
    AssembledAd,
    assemble_ad,
    is_publishable,
)
from output.exporter import (
    export_ad,
    export_batch,
    ExportSummary,
)
from iterate.ledger import log_event


def _seed_ledger(ledger_path: str, ad_id: str = "ad_001", image_blocked: bool = False) -> None:
    """Seed a ledger with a complete ad lifecycle for testing."""
    # Ad generated
    log_event(ledger_path, {
        "event_type": "AdGenerated",
        "ad_id": ad_id,
        "brief_id": "b001",
        "cycle_number": 1,
        "action": "generation",
        "inputs": {"audience": "parents", "campaign_goal": "conversion"},
        "outputs": {
            "primary_text": "Expert SAT tutors help your child succeed.",
            "headline": "Ace the SAT",
            "description": "1-on-1 personalized tutoring",
            "cta": "Learn More",
        },
        "scores": {},
        "tokens_consumed": 500,
        "model_used": "gemini-2.0-flash",
        "seed": "42",
    })

    # Ad evaluated
    log_event(ledger_path, {
        "event_type": "AdEvaluated",
        "ad_id": ad_id,
        "brief_id": "b001",
        "cycle_number": 1,
        "action": "evaluation",
        "inputs": {},
        "outputs": {},
        "scores": {
            "clarity": 8.0,
            "value_proposition": 7.5,
            "cta": 7.0,
            "brand_voice": 8.0,
            "emotional_resonance": 7.5,
            "weighted_average": 7.6,
        },
        "tokens_consumed": 300,
        "model_used": "gemini-2.0-flash",
        "seed": "42",
    })

    # Ad published
    log_event(ledger_path, {
        "event_type": "AdPublished",
        "ad_id": ad_id,
        "brief_id": "b001",
        "cycle_number": 1,
        "action": "publish",
        "inputs": {},
        "outputs": {},
        "scores": {"weighted_average": 7.6},
        "tokens_consumed": 0,
        "model_used": "",
        "seed": "42",
    })

    # Image generated
    log_event(ledger_path, {
        "event_type": "ImageGenerated",
        "ad_id": ad_id,
        "brief_id": "b001",
        "cycle_number": 1,
        "action": "image-generation",
        "inputs": {},
        "outputs": {"variant_type": "anchor", "image_path": "/tmp/anchor.png"},
        "scores": {},
        "tokens_consumed": 0,
        "model_used": "gemini-2.0-flash",
        "seed": "42",
    })

    # Image selected
    log_event(ledger_path, {
        "event_type": "ImageSelected",
        "ad_id": ad_id,
        "brief_id": "b001",
        "cycle_number": 1,
        "action": "image-selection",
        "inputs": {},
        "outputs": {
            "winner_variant": "anchor",
            "winner_image_path": "/tmp/anchor.png",
            "composite_score": 0.88,
            "attribute_pass_pct": 1.0,
            "coherence_avg": 0.8,
        },
        "scores": {},
        "tokens_consumed": 0,
        "model_used": "",
        "seed": "42",
    })

    if image_blocked:
        log_event(ledger_path, {
            "event_type": "ImageBlocked",
            "ad_id": ad_id,
            "brief_id": "b001",
            "cycle_number": 1,
            "action": "image-blocked",
            "inputs": {},
            "outputs": {"weakest_dimension": "no_artifacts"},
            "scores": {},
            "tokens_consumed": 0,
            "model_used": "",
            "seed": "42",
        })


# --- Assembly Tests ---


def test_assemble_ad_collects_copy_and_metadata(tmp_path: Path) -> None:
    """Assembly collects correct copy, image, and metadata from ledger."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _seed_ledger(ledger_path)

    assembled = assemble_ad("ad_001", ledger_path)
    assert isinstance(assembled, AssembledAd)
    assert assembled.ad_id == "ad_001"
    assert assembled.copy["headline"] == "Ace the SAT"
    assert assembled.copy["primary_text"]
    assert assembled.winning_image_path == "/tmp/anchor.png"
    assert assembled.text_scores["weighted_average"] == 7.6


def test_is_publishable_true_for_passing_ad(tmp_path: Path) -> None:
    """is_publishable returns True for ads with passing text + winning image."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _seed_ledger(ledger_path)
    assert is_publishable("ad_001", ledger_path) is True


def test_is_publishable_false_for_image_blocked(tmp_path: Path) -> None:
    """is_publishable returns False for image-blocked ads."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _seed_ledger(ledger_path, image_blocked=True)
    assert is_publishable("ad_001", ledger_path) is False


def test_is_publishable_false_for_missing_ad(tmp_path: Path) -> None:
    """is_publishable returns False for ads not in ledger."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    assert is_publishable("ad_999", ledger_path) is False


# --- Export Tests ---


def test_export_creates_folder_structure(tmp_path: Path) -> None:
    """Export creates correct folder structure."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _seed_ledger(ledger_path)
    assembled = assemble_ad("ad_001", ledger_path)

    export_dir = str(tmp_path / "exports")
    result_path = export_ad(assembled, export_dir)

    assert Path(result_path).exists()
    assert (Path(result_path) / "copy.json").exists()
    assert (Path(result_path) / "metadata.json").exists()


def test_export_copy_json_has_required_fields(tmp_path: Path) -> None:
    """Export writes copy.json with all required fields."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _seed_ledger(ledger_path)
    assembled = assemble_ad("ad_001", ledger_path)

    export_dir = str(tmp_path / "exports")
    result_path = export_ad(assembled, export_dir)

    copy = json.loads((Path(result_path) / "copy.json").read_text())
    assert "primary_text" in copy
    assert "headline" in copy
    assert "description" in copy
    assert "cta" in copy


def test_export_metadata_has_scores(tmp_path: Path) -> None:
    """Export writes metadata.json with text and image scores."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _seed_ledger(ledger_path)
    assembled = assemble_ad("ad_001", ledger_path)

    export_dir = str(tmp_path / "exports")
    result_path = export_ad(assembled, export_dir)

    meta = json.loads((Path(result_path) / "metadata.json").read_text())
    assert "text_scores" in meta
    assert "image_selection" in meta
    assert meta["ad_id"] == "ad_001"


def test_batch_export_skips_blocked(tmp_path: Path) -> None:
    """Batch export skips image-blocked ads with correct summary."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _seed_ledger(ledger_path, ad_id="ad_001")
    _seed_ledger(ledger_path, ad_id="ad_002", image_blocked=True)

    export_dir = str(tmp_path / "exports")
    summary = export_batch(["ad_001", "ad_002"], ledger_path, export_dir)

    assert isinstance(summary, ExportSummary)
    assert summary.exported == 1
    assert summary.skipped == 1
