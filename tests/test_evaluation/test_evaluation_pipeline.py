"""PH-04 evaluation pipeline composite tests.

Cover the public surface added in PH-04:
- :class:`CopyEvaluation` carries the underlying :class:`EvaluationResult`
  and :class:`RoutingDecision` and exposes the four convenience properties
  (``aggregate_score``, ``decision``, ``improvable``, ``escalation_reason``).
- :func:`evaluate_copy` composes ``evaluator.evaluate_ad`` and
  ``model_router.route_ad`` into a single call.
- :func:`evaluate_visual` returns whichever pieces match the asset paths
  (image only, video only, neither).
- ``improvable`` is derived from the aggregate score range [5.5, 7.0).
- ``escalation_reason`` is populated only when the routing decision is
  ``"escalate"``.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from evaluate.brief_adherence import BriefAdherenceResult
from evaluate.evaluation_pipeline import (
    CopyEvaluation,
    VisualEvaluation,
    evaluate_copy,
    evaluate_visual,
)
from evaluate.evaluator import EvaluationResult
from generate.model_router import RoutingDecision


def _eval_result(score: float, ad_id: str = "ad_001") -> EvaluationResult:
    """Minimal EvaluationResult fixture."""
    return EvaluationResult(
        ad_id=ad_id,
        scores={},
        aggregate_score=score,
        campaign_goal="conversion",
        meets_threshold=score >= 7.0,
        weakest_dimension="clarity",
        flags=[],
        rationales={},
        structural_elements={},
        confidence_flags={},
        metadata={},
    )


def _routing(decision: str, score: float = 7.5, reason: str = "ok") -> RoutingDecision:
    return RoutingDecision(
        ad_id="ad_001", score=score, decision=decision,
        model_used="gemini-2.0-flash", reason=reason,
    )


# --- CopyEvaluation convenience properties ---------------------------------


def test_aggregate_score_passes_through() -> None:
    ce = CopyEvaluation(evaluation=_eval_result(7.5), routing=_routing("publish"))
    assert ce.aggregate_score == 7.5


def test_decision_passes_through() -> None:
    ce = CopyEvaluation(evaluation=_eval_result(6.2), routing=_routing("escalate"))
    assert ce.decision == "escalate"


def test_improvable_true_inside_range() -> None:
    """Improvable range is [5.5, 7.0)."""
    for score in (5.5, 6.0, 6.5, 6.99):
        ce = CopyEvaluation(evaluation=_eval_result(score), routing=_routing("escalate"))
        assert ce.improvable, f"score {score} should be improvable"


def test_improvable_false_outside_range() -> None:
    for score in (0.0, 4.0, 5.49, 7.0, 7.5, 9.0):
        ce = CopyEvaluation(evaluation=_eval_result(score), routing=_routing("publish"))
        assert not ce.improvable, f"score {score} should NOT be improvable"


def test_escalation_reason_only_when_escalating() -> None:
    publish = CopyEvaluation(evaluation=_eval_result(8.0), routing=_routing("publish"))
    escalate = CopyEvaluation(
        evaluation=_eval_result(6.0),
        routing=_routing("escalate", reason="Score in improvable range"),
    )
    discard = CopyEvaluation(evaluation=_eval_result(3.0), routing=_routing("discard"))

    assert publish.escalation_reason is None
    assert escalate.escalation_reason == "Score in improvable range"
    assert discard.escalation_reason is None


# --- evaluate_copy composes the two leaf calls -----------------------------


def test_evaluate_copy_calls_evaluator_then_router() -> None:
    fake_eval = _eval_result(6.2, ad_id="ad_xyz")
    fake_routing = _routing("escalate", score=6.2, reason="improvable")

    fake_ad = MagicMock()
    fake_ad.ad_id = "ad_xyz"
    fake_ad.to_evaluator_input.return_value = {"ad_id": "ad_xyz", "primary_text": "..."}

    brief = {"campaign_goal": "awareness", "audience": "parents"}
    session_config = {"text_threshold": 7.0, "improvable_range": [5.5, 7.0]}

    with (
        patch("evaluate.evaluation_pipeline.evaluate_ad", return_value=fake_eval) as me,
        patch("evaluate.evaluation_pipeline.route_ad", return_value=fake_routing) as mr,
    ):
        result = evaluate_copy(
            fake_ad, brief, session_config,
            persona="suburban_optimizer", ledger_path="/tmp/l",
        )

    me.assert_called_once()
    eval_kwargs = me.call_args.kwargs
    assert eval_kwargs["campaign_goal"] == "awareness"
    assert eval_kwargs["audience"] == "parents"
    assert eval_kwargs["persona"] == "suburban_optimizer"
    assert eval_kwargs["ledger_path"] == "/tmp/l"

    mr.assert_called_once()
    router_kwargs = mr.call_args.kwargs
    assert router_kwargs["ad_id"] == "ad_xyz"
    assert router_kwargs["aggregate_score"] == 6.2
    assert router_kwargs["campaign_goal"] == "awareness"

    assert isinstance(result, CopyEvaluation)
    assert result.evaluation is fake_eval
    assert result.routing is fake_routing
    assert result.improvable is True
    assert result.escalation_reason == "improvable"


def test_evaluate_copy_accepts_raw_dict_ad() -> None:
    """When given a raw evaluator-input dict (no .to_evaluator_input), works."""
    fake_eval = _eval_result(8.0, ad_id="ad_dict")
    fake_routing = _routing("publish", score=8.0)
    ad_dict = {"ad_id": "ad_dict", "primary_text": "..."}

    with (
        patch("evaluate.evaluation_pipeline.evaluate_ad", return_value=fake_eval),
        patch("evaluate.evaluation_pipeline.route_ad", return_value=fake_routing) as mr,
    ):
        result = evaluate_copy(ad_dict, {"campaign_goal": "conversion"}, {})

    # router should receive ad_id from the dict
    assert mr.call_args.kwargs["ad_id"] == "ad_dict"
    assert result.decision == "publish"


# --- evaluate_visual ---------------------------------------------------------


def test_evaluate_visual_no_paths_returns_empty() -> None:
    fake_ad = MagicMock()
    fake_ad.to_evaluator_input.return_value = {"ad_id": "ad_001"}
    result = evaluate_visual(fake_ad, {}, {})
    assert isinstance(result, VisualEvaluation)
    assert result.image_scores is None
    assert result.video_scores is None
    assert result.adherence is None


def test_evaluate_visual_image_path_runs_image_scorer_and_adherence() -> None:
    fake_ad = MagicMock()
    fake_ad.ad_id = "ad_001"
    fake_ad.to_evaluator_input.return_value = {"ad_id": "ad_001"}

    fake_image_result = MagicMock(scores={"clarity": 8.0}, avg_score=8.0, tokens_consumed=100)
    fake_adherence = BriefAdherenceResult(
        ad_id="ad_001", scores={}, avg_score=7.0,
        rationales={}, tokens_consumed=50,
    )

    with (
        patch("evaluate.image_scorer.score_image", return_value=fake_image_result) as ms,
        patch(
            "evaluate.evaluation_pipeline.score_brief_adherence",
            return_value=fake_adherence,
        ) as ma,
    ):
        result = evaluate_visual(
            fake_ad, {}, {"text_threshold": 7.0},
            image_path="/tmp/img.png",
        )

    ms.assert_called_once()
    assert ms.call_args.kwargs["image_path"] == "/tmp/img.png"
    ma.assert_called_once()
    assert ma.call_args.kwargs["image_path"] == "/tmp/img.png"
    assert ma.call_args.kwargs["video_path"] is None

    assert result.image_scores is fake_image_result
    assert result.video_scores is None
    assert result.adherence is fake_adherence


def test_evaluate_visual_video_path_runs_video_scorer_and_adherence() -> None:
    fake_ad = {"ad_id": "ad_vid"}
    fake_video_result = MagicMock(scores={}, avg_score=6.5, tokens_consumed=100)
    fake_adherence = BriefAdherenceResult(
        ad_id="ad_vid", scores={}, avg_score=6.5,
        rationales={}, tokens_consumed=80,
    )

    with (
        patch("evaluate.video_scorer.score_video", return_value=fake_video_result) as mv,
        patch(
            "evaluate.evaluation_pipeline.score_brief_adherence",
            return_value=fake_adherence,
        ) as ma,
    ):
        result = evaluate_visual(
            fake_ad, {}, {},
            video_path="/tmp/v.mp4",
            ad_id="ad_vid",
        )

    mv.assert_called_once()
    assert mv.call_args.kwargs["video_path"] == "/tmp/v.mp4"
    ma.assert_called_once()
    assert ma.call_args.kwargs["video_path"] == "/tmp/v.mp4"

    assert result.video_scores is fake_video_result
    assert result.image_scores is None
    assert result.adherence is fake_adherence
