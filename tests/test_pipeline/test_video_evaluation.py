"""PC-02 tests for video evaluation compatibility APIs."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from evaluate.coherence_checker import (
    COHERENCE_DIMENSIONS,
    CoherenceResult,
    check_video_coherence,
    is_incoherent,
)
from evaluate.image_evaluator import (
    VIDEO_ATTRIBUTES,
    VideoAttributeResult,
    VideoSelectionResult,
    compute_video_composite_score,
    evaluate_video_attributes,
    select_best_video_variant,
)


COPY = {
    "primary_text": "Your child can raise their SAT score with focused 1-on-1 tutoring.",
    "headline": "SAT Tutoring That Builds Confidence",
    "description": "See what score is realistic in 8-10 weeks.",
    "cta_button": "Start Free Practice Test",
}


def _make_video_attr_result(
    variant_type: str = "anchor",
    attributes: dict[str, bool] | None = None,
) -> VideoAttributeResult:
    if attributes is None:
        attributes = {attr: True for attr in VIDEO_ATTRIBUTES}
    pass_pct = round(sum(attributes.values()) / len(attributes), 2)
    return VideoAttributeResult(
        ad_id="ad_001",
        variant_type=variant_type,
        attributes=attributes,
        attribute_pass_pct=pass_pct,
        meets_threshold=pass_pct >= 0.8,
    )


def _make_coherence_result(
    variant_type: str = "anchor",
    scores: dict[str, float] | None = None,
) -> CoherenceResult:
    if scores is None:
        scores = {dim: 7.0 for dim in COHERENCE_DIMENSIONS}
    avg = round(sum(scores.values()) / len(scores), 2)
    return CoherenceResult(
        ad_id="ad_001",
        variant_type=variant_type,
        dimension_scores=scores,
        coherence_avg=avg,
    )


@patch("evaluate.image_evaluator._call_video_multimodal_eval")
def test_evaluate_video_attributes_returns_result(mock_call: MagicMock) -> None:
    """Video attribute evaluation returns 5 binary attributes."""
    mock_call.return_value = {
        "hook_timing": True,
        "ugc_authenticity": True,
        "pacing": True,
        "text_legibility": True,
        "no_artifacts": False,
    }
    result = evaluate_video_attributes(
        video_path="/tmp/test.mp4",
        video_spec={"pacing": "fast"},
        ad_id="ad_001",
        variant_type="anchor",
    )
    assert isinstance(result, VideoAttributeResult)
    assert len(result.attributes) == 5
    assert result.attribute_pass_pct == 0.8
    assert result.meets_threshold is True


@patch("evaluate.image_evaluator._call_video_multimodal_eval")
def test_evaluate_video_attributes_logs_event(mock_call: MagicMock, tmp_path: Path) -> None:
    """Video attribute evaluation appends a VideoEvaluated event."""
    mock_call.return_value = {attr: True for attr in VIDEO_ATTRIBUTES}
    ledger_path = str(tmp_path / "ledger.jsonl")
    evaluate_video_attributes(
        video_path="/tmp/test.mp4",
        video_spec={"pacing": "fast"},
        ad_id="ad_001",
        variant_type="anchor",
        ledger_path=ledger_path,
    )
    events = [json.loads(line) for line in Path(ledger_path).read_text().strip().split("\n")]
    assert events[0]["event_type"] == "VideoEvaluated"
    assert events[0]["ad_id"] == "ad_001"


def test_video_attribute_threshold_4_of_5_passes() -> None:
    """4/5 passes meets the 80% threshold."""
    attrs = {attr: True for attr in VIDEO_ATTRIBUTES}
    attrs["no_artifacts"] = False
    result = _make_video_attr_result(attributes=attrs)
    assert result.attribute_pass_pct == 0.8
    assert result.meets_threshold is True


def test_video_attribute_threshold_3_of_5_fails() -> None:
    """3/5 passes fails the threshold."""
    attrs = {attr: False for attr in VIDEO_ATTRIBUTES}
    attrs["hook_timing"] = True
    attrs["ugc_authenticity"] = True
    attrs["pacing"] = True
    result = _make_video_attr_result(attributes=attrs)
    assert result.attribute_pass_pct == 0.6
    assert result.meets_threshold is False


@patch("evaluate.coherence_checker._call_video_coherence_eval")
def test_check_video_coherence_returns_result(mock_call: MagicMock) -> None:
    """Video coherence evaluation reuses CoherenceResult with 4 dimensions."""
    mock_call.return_value = {
        "message_alignment": 8.0,
        "audience_match": 7.0,
        "emotional_consistency": 6.0,
        "visual_narrative": 7.0,
    }
    result = check_video_coherence(
        copy=COPY,
        video_path="/tmp/test.mp4",
        ad_id="ad_001",
        variant_type="anchor",
    )
    assert isinstance(result, CoherenceResult)
    assert len(result.dimension_scores) == 4
    assert result.coherence_avg == 7.0


def test_video_coherence_threshold() -> None:
    """Average below 6.0 is incoherent, 6.0 and above is coherent."""
    low = _make_coherence_result(scores={dim: 5.0 for dim in COHERENCE_DIMENSIONS})
    high = _make_coherence_result(scores={dim: 6.0 for dim in COHERENCE_DIMENSIONS})
    assert is_incoherent(low) is True
    assert is_incoherent(high) is False


def test_select_best_video_variant_higher_composite_wins() -> None:
    """Higher composite score wins when both variants pass."""
    anchor_attr = _make_video_attr_result("anchor")
    anchor_coh = _make_coherence_result("anchor", {dim: 6.0 for dim in COHERENCE_DIMENSIONS})
    alt_attr = _make_video_attr_result("alternative")
    alt_coh = _make_coherence_result("alternative", {dim: 8.0 for dim in COHERENCE_DIMENSIONS})

    result = select_best_video_variant(
        [(anchor_attr, anchor_coh), (alt_attr, alt_coh)],
        ad_id="ad_001",
    )

    assert isinstance(result, VideoSelectionResult)
    assert result.winner_variant_type == "alternative"
    assert result.video_blocked is False


def test_select_best_video_variant_both_fail_blocks() -> None:
    """When both variants fail, selection degrades to image-only."""
    bad_attrs = {attr: False for attr in VIDEO_ATTRIBUTES}
    anchor_attr = _make_video_attr_result("anchor", bad_attrs)
    alt_attr = _make_video_attr_result("alternative", bad_attrs)
    low_scores = {dim: 5.0 for dim in COHERENCE_DIMENSIONS}
    anchor_coh = _make_coherence_result("anchor", low_scores)
    alt_coh = _make_coherence_result("alternative", low_scores)

    result = select_best_video_variant(
        [(anchor_attr, anchor_coh), (alt_attr, alt_coh)],
        ad_id="ad_001",
    )

    assert result.winner_variant_type is None
    assert result.video_blocked is True
    assert result.degrade_to_image_only is True


def test_select_best_video_variant_one_fail_one_pass_selects_passing() -> None:
    """Passing variant wins even if the failing variant has stronger coherence."""
    failing_attrs = {attr: False for attr in VIDEO_ATTRIBUTES}
    failing_attrs["hook_timing"] = True
    failing_attrs["ugc_authenticity"] = True
    failing_attrs["pacing"] = True
    anchor_attr = _make_video_attr_result("anchor", failing_attrs)
    anchor_coh = _make_coherence_result("anchor", {dim: 9.0 for dim in COHERENCE_DIMENSIONS})

    alt_attr = _make_video_attr_result("alternative")
    alt_coh = _make_coherence_result("alternative", {dim: 6.0 for dim in COHERENCE_DIMENSIONS})

    result = select_best_video_variant(
        [(anchor_attr, anchor_coh), (alt_attr, alt_coh)],
        ad_id="ad_001",
    )

    assert result.winner_variant_type == "alternative"
    assert result.video_blocked is False


def test_select_best_video_variant_logs_selection(tmp_path: Path) -> None:
    """Selection writes a VideoSelected event with winner metadata."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    anchor_attr = _make_video_attr_result("anchor")
    anchor_coh = _make_coherence_result("anchor", {dim: 7.0 for dim in COHERENCE_DIMENSIONS})
    alt_attr = _make_video_attr_result("alternative")
    alt_coh = _make_coherence_result("alternative", {dim: 8.0 for dim in COHERENCE_DIMENSIONS})

    result = select_best_video_variant(
        [(anchor_attr, anchor_coh), (alt_attr, alt_coh)],
        ad_id="ad_001",
        ledger_path=ledger_path,
    )

    events = [json.loads(line) for line in Path(ledger_path).read_text().strip().split("\n")]
    assert result.winner_variant_type == "alternative"
    assert events[0]["event_type"] == "VideoSelected"
    assert events[0]["outputs"]["winner_variant_type"] == "alternative"


def test_compute_video_composite_score_uses_weighted_formula() -> None:
    """Composite score uses 40/60 weighting."""
    score = compute_video_composite_score(attribute_pass_pct=0.8, coherence_avg=7.0)
    assert abs(score - 4.52) < 0.01
