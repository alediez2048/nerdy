"""Golden set regression tests for evaluator (P0-06).

TDD: Tests written first. Evaluator must return valid EvaluationResult schema,
score all 5 dimensions independently, include contrastive rationales and confidence.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from evaluate.evaluator import EvaluationResult, evaluate_ad

REFERENCE_ADS_PATH = Path(__file__).resolve().parents[2] / "data" / "reference_ads.json"


def _sample_ad() -> dict:
    """Minimal valid ad dict for testing."""
    return {
        "ad_id": "test_001",
        "primary_text": "Is your child's SAT score holding them back? Varsity Tutors pairs your student with expert 1-on-1 tutors. Start with a free practice test.",
        "headline": "Expert 1-on-1 SAT Prep",
        "description": "Personalized tutoring that adapts",
        "cta_button": "Start Free Practice Test",
    }


def _mock_evaluation_response() -> dict:
    """Valid evaluation output matching EvaluationResult schema."""
    return {
        "ad_id": "test_001",
        "scores": {
            "clarity": {
                "score": 8.0,
                "rationale": "Single clear message about SAT score improvement.",
                "contrastive": "A 10.0 version would frontload the benefit.",
                "confidence": 8,
            },
            "value_proposition": {
                "score": 8.0,
                "rationale": "Specific: 1-on-1, expert, free practice test.",
                "contrastive": "A 10.0 would add social proof numbers.",
                "confidence": 8,
            },
            "cta": {
                "score": 9.0,
                "rationale": "Specific, low-friction, free trial.",
                "contrastive": "Already strong.",
                "confidence": 9,
            },
            "brand_voice": {
                "score": 7.5,
                "rationale": "Empowering, outcome-focused.",
                "contrastive": "A 9.5 would add 1-on-1 emphasis.",
                "confidence": 7,
            },
            "emotional_resonance": {
                "score": 7.0,
                "rationale": "Addresses parent worry about SAT.",
                "contrastive": "A 9.0 would paint transformation picture.",
                "confidence": 7,
            },
        },
        "aggregate_score": 7.9,
        "campaign_goal": "conversion",
        "meets_threshold": True,
        "weakest_dimension": "emotional_resonance",
        "flags": [],
    }


@patch("evaluate.evaluator._call_gemini")
def test_evaluator_returns_valid_schema(mock_call: MagicMock) -> None:
    """Evaluator returns valid EvaluationResult with all required fields."""
    mock_call.return_value = _mock_evaluation_response()
    ad = _sample_ad()
    result = evaluate_ad(ad, campaign_goal="conversion")
    assert isinstance(result, EvaluationResult)
    assert result.ad_id == "test_001"
    assert result.aggregate_score == 7.9
    assert result.campaign_goal == "conversion"
    assert result.meets_threshold is True
    assert result.weakest_dimension == "emotional_resonance"
    assert isinstance(result.flags, list)


@patch("evaluate.evaluator._call_gemini")
def test_all_five_dimensions_scored(mock_call: MagicMock) -> None:
    """All 5 dimensions must be scored independently."""
    mock_call.return_value = _mock_evaluation_response()
    result = evaluate_ad(_sample_ad())
    dims = {"clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance"}
    assert set(result.scores.keys()) == dims
    for dim in dims:
        s = result.scores[dim]
        assert "score" in s and isinstance(s["score"], (int, float))
        assert 1 <= s["score"] <= 10


@patch("evaluate.evaluator._call_gemini")
def test_contrastive_rationale_present(mock_call: MagicMock) -> None:
    """Each dimension must have contrastive rationale."""
    mock_call.return_value = _mock_evaluation_response()
    result = evaluate_ad(_sample_ad())
    for dim, data in result.scores.items():
        assert "contrastive" in data
        assert isinstance(data["contrastive"], str)
        assert len(data["contrastive"]) > 10


@patch("evaluate.evaluator._call_gemini")
def test_confidence_flag_present(mock_call: MagicMock) -> None:
    """Each dimension must have confidence (1-10)."""
    mock_call.return_value = _mock_evaluation_response()
    result = evaluate_ad(_sample_ad())
    for dim, data in result.scores.items():
        assert "confidence" in data
        assert isinstance(data["confidence"], (int, float))
        assert 1 <= data["confidence"] <= 10


@patch("evaluate.evaluator._call_gemini")
def test_aggregate_uses_equal_weights(mock_call: MagicMock) -> None:
    """P0-06: Default equal weighting (0.2 per dimension)."""
    mock_call.return_value = _mock_evaluation_response()
    result = evaluate_ad(_sample_ad())
    # With equal weights, aggregate should be mean of 5 dimension scores
    scores = [result.scores[d]["score"] for d in result.scores]
    expected = sum(scores) / 5
    assert abs(result.aggregate_score - expected) < 0.1


@patch("evaluate.evaluator._call_gemini")
def test_floor_constraint_awareness(mock_call: MagicMock) -> None:
    """Basic floor awareness: Clarity >= 6.0, Brand Voice >= 5.0."""
    low_floor_response = _mock_evaluation_response()
    low_floor_response["scores"]["clarity"]["score"] = 5.0
    low_floor_response["scores"]["brand_voice"]["score"] = 4.0
    low_floor_response["aggregate_score"] = 6.0
    mock_call.return_value = low_floor_response
    result = evaluate_ad(_sample_ad())
    # Evaluator returns raw scores; floor enforcement is in meets_threshold logic
    assert result.scores["clarity"]["score"] == 5.0
    assert result.scores["brand_voice"]["score"] == 4.0
    # Floor violations → meets_threshold must be False
    assert result.meets_threshold is False


@patch("evaluate.evaluator._call_gemini")
def test_awareness_vs_conversion_goal(mock_call: MagicMock) -> None:
    """Evaluator accepts campaign_goal parameter."""
    mock_call.return_value = _mock_evaluation_response()
    result_conv = evaluate_ad(_sample_ad(), campaign_goal="conversion")
    result_aware = evaluate_ad(_sample_ad(), campaign_goal="awareness")
    assert result_conv.campaign_goal == "conversion"
    assert result_aware.campaign_goal == "awareness"


def test_evaluation_result_json_serializable() -> None:
    """EvaluationResult can be serialized to JSON for ledger."""
    mock = _mock_evaluation_response()
    result = EvaluationResult(
        ad_id=mock["ad_id"],
        scores=mock["scores"],
        aggregate_score=mock["aggregate_score"],
        campaign_goal=mock["campaign_goal"],
        meets_threshold=mock["meets_threshold"],
        weakest_dimension=mock["weakest_dimension"],
        flags=mock["flags"],
    )
    s = json.dumps(result.to_dict())
    loaded = json.loads(s)
    assert loaded["ad_id"] == result.ad_id
    assert loaded["aggregate_score"] == result.aggregate_score
