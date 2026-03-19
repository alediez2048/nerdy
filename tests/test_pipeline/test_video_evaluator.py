# PC-02: Video evaluator tests (TDD)
"""Tests for video attribute evaluation, coherence checking, and composite scoring."""

from unittest.mock import patch

import pytest


@pytest.fixture()
def real_video(tmp_path):
    """Create a fake video file on disk for tests that need a file to exist."""
    p = tmp_path / "test_video.mp4"
    p.write_bytes(b"\x00" * 1024)
    return str(p)


@pytest.fixture()
def missing_video():
    return "/nonexistent/path/video.mp4"


# --- Attribute evaluation ---


@patch("evaluate.video_evaluator._call_multimodal_video_eval")
def test_evaluate_attributes_all_pass(mock_eval, real_video):
    mock_eval.return_value = {
        "hook_timing": True,
        "ugc_authenticity": True,
        "pacing": True,
        "text_legibility": True,
        "no_artifacts": True,
    }

    from evaluate.video_evaluator import evaluate_video_attributes
    result = evaluate_video_attributes(real_video, {}, "ad_001", "anchor")

    assert result.attribute_pass_pct == 1.0
    assert result.meets_threshold is True
    assert all(result.attributes.values())


@patch("evaluate.video_evaluator._call_multimodal_video_eval")
def test_evaluate_attributes_below_threshold(mock_eval, real_video):
    mock_eval.return_value = {
        "hook_timing": True,
        "ugc_authenticity": False,
        "pacing": False,
        "text_legibility": True,
        "no_artifacts": True,
    }

    from evaluate.video_evaluator import evaluate_video_attributes
    result = evaluate_video_attributes(real_video, {}, "ad_002", "alternative")

    assert result.attribute_pass_pct == pytest.approx(0.6)
    assert result.meets_threshold is False


def test_evaluate_attributes_missing_file_returns_fail(missing_video):
    from evaluate.video_evaluator import evaluate_video_attributes
    result = evaluate_video_attributes(missing_video, {}, "ad_003", "anchor")

    assert result.meets_threshold is False
    assert result.attribute_pass_pct == 0.0
    assert all(v is False for v in result.attributes.values())


# --- Coherence checking ---


@patch("evaluate.video_evaluator._call_coherence_eval")
def test_coherence_above_threshold(mock_eval, real_video):
    mock_eval.return_value = {
        "message_alignment": 5.0,
        "audience_match": 6.0,
        "emotional_consistency": 4.5,
        "narrative_flow": 5.5,
    }

    from evaluate.video_evaluator import check_video_coherence
    result = check_video_coherence(
        {"primary_text": "Test ad"}, real_video, "ad_001", "anchor"
    )

    assert result.avg_score == pytest.approx(5.25)
    assert result.is_coherent is True  # 5.25 >= 4.0


@patch("evaluate.video_evaluator._call_coherence_eval")
def test_coherence_below_threshold(mock_eval, real_video):
    mock_eval.return_value = {
        "message_alignment": 2.0,
        "audience_match": 3.0,
        "emotional_consistency": 3.5,
        "narrative_flow": 3.0,
    }

    from evaluate.video_evaluator import check_video_coherence
    result = check_video_coherence(
        {"primary_text": "Test ad"}, real_video, "ad_001", "anchor"
    )

    assert result.avg_score == pytest.approx(2.875)
    assert result.is_coherent is False  # 2.875 < 4.0


def test_coherence_missing_file_returns_incoherent(missing_video):
    from evaluate.video_evaluator import check_video_coherence
    result = check_video_coherence(
        {"primary_text": "Test"}, missing_video, "ad_004", "anchor"
    )

    assert result.is_coherent is False
    assert result.avg_score == 0.0


# --- Composite score ---


def test_composite_score_calculation():
    from evaluate.video_evaluator import (
        VideoEvalResult,
        VideoCoherenceResult,
        compute_composite_score,
    )

    eval_r = VideoEvalResult(
        ad_id="ad_001", variant_type="anchor",
        attributes={"a": True, "b": True, "c": True, "d": True, "e": False},
        attribute_pass_pct=0.8, meets_threshold=True,
    )
    coh_r = VideoCoherenceResult(
        ad_id="ad_001", variant_type="anchor",
        dimensions={"m": 6.0, "a": 5.0, "e": 7.0, "n": 6.0},
        avg_score=6.0, is_coherent=True,
    )

    score = compute_composite_score(eval_r, coh_r)

    # 40% * 0.8 + 60% * (6.0 / 10.0) = 0.32 + 0.36 = 0.68
    assert score == pytest.approx(0.68, abs=0.01)
