"""Tests for unified media quality evaluator (PI-02)."""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch
import pytest

from evaluate.media_quality import (
    IMAGE_DIMENSIONS,
    IMAGE_GATES,
    DimensionScore,
    GateEvaluation,
    MediaEvaluationResult,
    compute_composite,
    evaluate_media,
)


def test_image_dimensions_and_weights() -> None:
    """8 dimensions for image, weights sum to 1.0."""
    assert len(IMAGE_DIMENSIONS) == 8
    total = sum(d["weight"] for d in IMAGE_DIMENSIONS)
    assert abs(total - 1.0) < 1e-9, f"weights sum to {total}, not 1.0"
    names = {d["name"] for d in IMAGE_DIMENSIONS}
    assert names == {
        "thumb_stop_potential", "mobile_legibility", "single_focal_point",
        "brand_consistency", "emotional_impact", "message_alignment",
        "audience_match", "production_quality",
    }


def test_image_gates_have_caps() -> None:
    """3 image gates with cap multipliers <1.0."""
    assert len(IMAGE_GATES) == 3
    names = {g["name"] for g in IMAGE_GATES}
    assert names == {"has_ai_artifacts", "has_uncanny_faces", "brand_safety_violation"}
    for g in IMAGE_GATES:
        assert 0.0 < g["cap"] < 1.0


def test_compute_composite_no_gates_triggered() -> None:
    """raw * 1.0 * 100 when no penalty applies."""
    dims = {
        d["name"]: DimensionScore(score=7, weight=d["weight"], rationale="")
        for d in IMAGE_DIMENSIONS
    }
    gates = {g["name"]: GateEvaluation(triggered=False, rationale="") for g in IMAGE_GATES}
    raw, mult, composite = compute_composite(dims, gates, IMAGE_GATES)
    assert mult == 1.0
    assert raw == pytest.approx(0.7, abs=1e-4)
    assert composite == pytest.approx(70.0, abs=0.01)


def test_compute_composite_single_gate_triggered() -> None:
    """has_uncanny_faces caps at 0.6."""
    dims = {
        d["name"]: DimensionScore(score=8, weight=d["weight"], rationale="")
        for d in IMAGE_DIMENSIONS
    }
    gates = {g["name"]: GateEvaluation(triggered=False, rationale="") for g in IMAGE_GATES}
    gates["has_uncanny_faces"] = GateEvaluation(triggered=True, rationale="bad eyes")
    raw, mult, composite = compute_composite(dims, gates, IMAGE_GATES)
    assert mult == 0.6
    assert composite == pytest.approx(48.0, abs=0.01)


def test_compute_composite_multiple_gates_use_lowest_cap() -> None:
    """has_ai_artifacts (0.5) wins over has_uncanny_faces (0.6) when both fire."""
    dims = {
        d["name"]: DimensionScore(score=8, weight=d["weight"], rationale="")
        for d in IMAGE_DIMENSIONS
    }
    gates = {g["name"]: GateEvaluation(triggered=False, rationale="") for g in IMAGE_GATES}
    gates["has_uncanny_faces"] = GateEvaluation(triggered=True, rationale="")
    gates["has_ai_artifacts"] = GateEvaluation(triggered=True, rationale="")
    raw, mult, composite = compute_composite(dims, gates, IMAGE_GATES)
    assert mult == 0.5
    assert composite == pytest.approx(40.0, abs=0.01)


def _make_payload(score: int = 7) -> dict[str, Any]:
    return {
        "dimensions": {
            d["name"]: {"score": score, "rationale": f"specific reason for {d['name']}"}
            for d in IMAGE_DIMENSIONS
        },
        "penalty_gates": {
            g["name"]: {"triggered": False, "rationale": "clean"}
            for g in IMAGE_GATES
        },
    }


def test_evaluate_media_image_happy_path(tmp_path) -> None:
    """Mocked LLM returns valid JSON → MediaEvaluationResult populated end to end."""
    media_path = tmp_path / "ad.png"
    media_path.write_bytes(b"fake-png")
    payload = json.dumps(_make_payload(score=7))
    with patch("evaluate.media_quality._call_multimodal", return_value=(payload, 1500)):
        result: MediaEvaluationResult = evaluate_media(
            media_path=str(media_path),
            ad_copy={"headline": "Ace the SAT", "body": "1-on-1 tutoring", "cta": "Start"},
            ad_id="ad_001",
            variant_type="anchor",
            media_type="image",
        )
    assert not result.failed
    assert result.media_type == "image"
    assert result.tokens_consumed == 1500
    assert len(result.dimensions) == 8
    assert all(1 <= ds.score <= 10 for ds in result.dimensions.values())
    assert len(result.penalty_gates) == 3
    assert result.composite_score == pytest.approx(70.0, abs=0.01)
    assert "specific reason" in result.dimensions["thumb_stop_potential"].rationale


def test_evaluate_media_file_not_found_returns_failure() -> None:
    result = evaluate_media(
        media_path="/does/not/exist.png",
        ad_copy={}, ad_id="ad_001", variant_type="anchor", media_type="image",
    )
    assert result.failed
    assert result.failure_reason == "file_not_found"


def test_evaluate_media_json_parse_failure_returns_failure(tmp_path) -> None:
    media_path = tmp_path / "ad.png"
    media_path.write_bytes(b"x")
    with patch("evaluate.media_quality._call_multimodal", return_value=("not json", 100)):
        result = evaluate_media(
            media_path=str(media_path),
            ad_copy={}, ad_id="ad_001", variant_type="anchor", media_type="image",
        )
    assert result.failed
    assert result.failure_reason == "json_parse_failed"


def test_evaluate_media_score_clamped_to_1_10(tmp_path) -> None:
    media_path = tmp_path / "ad.png"
    media_path.write_bytes(b"x")
    bad_payload = _make_payload(score=15)
    with patch("evaluate.media_quality._call_multimodal", return_value=(json.dumps(bad_payload), 100)):
        result = evaluate_media(
            media_path=str(media_path),
            ad_copy={}, ad_id="ad_001", variant_type="anchor", media_type="image",
        )
    assert not result.failed
    assert all(ds.score == 10 for ds in result.dimensions.values())
