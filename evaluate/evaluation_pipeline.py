"""Evaluation pipeline composite — PH-04.

Today, "evaluate an ad" requires calling at least four leaf evaluators in
the right order:

1. ``evaluator.evaluate_ad`` — 5-dimension chain-of-thought text scoring
2. ``model_router.route_ad`` — turn the aggregate score into a routing
   decision (publish / discard / escalate)
3. ``image_scorer.score_image`` (or ``video_scorer.score_video``) — visual
   attribute scoring, only after the asset exists
4. ``brief_adherence.score_brief_adherence`` — did the ad do what the
   brief asked, with the visual evidence

Each leaf is small and individually testable, but the *composition* — the
sequencing, the "skip if not publishing" gating, the merging of results —
lived inline in ``iterate.batch_processor.process_batch`` and again in
``app.workers.tasks.pipeline_task._run_video_pipeline``. That's where the
real bugs hide.

This module defines the two composite operations that match the pipeline's
two phases:

* :func:`evaluate_copy` runs **before** any image/video has been generated.
* :func:`evaluate_visual` runs **after** the asset is produced.

The underlying leaf modules stay public — they remain individually
testable, and the 14+ tests that call ``evaluator.evaluate_ad`` directly
keep working.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from evaluate.evaluator import EvaluationResult, evaluate_ad
from generate.model_router import RoutingDecision, route_ad


# --- Result dataclasses --------------------------------------------------------


@dataclass(frozen=True)
class CopyEvaluation:
    """5-dim copy scoring + routing decision (PH-04 composite).

    Carries the underlying leaf results unchanged so callers that need
    one specific dimension can still reach in (`evaluation.scores`,
    `routing.reason`). The convenience properties cover the common
    cases — aggregate score, decision string, improvable flag,
    escalation reason.
    """

    evaluation: EvaluationResult
    routing: RoutingDecision

    @property
    def aggregate_score(self) -> float:
        return self.evaluation.aggregate_score

    @property
    def decision(self) -> str:
        return self.routing.decision

    @property
    def improvable(self) -> bool:
        """Score sits in the improvable range — worth a regen / Pro escalation."""
        return 5.5 <= self.aggregate_score < 7.0

    @property
    def escalation_reason(self) -> str | None:
        if self.decision == "escalate":
            return self.routing.reason
        return None


# --- Composite operations ------------------------------------------------------


def evaluate_copy(
    ad: Any,
    brief: dict[str, Any],
    session_config: dict[str, Any],
    *,
    persona: str | None = None,
    ledger_path: str | None = None,
) -> CopyEvaluation:
    """Run text scoring + routing as one operation.

    ``ad`` may be a :class:`generate.ad_generator.GeneratedAd` or a raw
    evaluator-input dict. ``session_config`` is the same dict
    ``batch_processor.process_batch`` builds (text_threshold, improvable_range,
    global_seed, etc.).
    """
    ad_input = ad.to_evaluator_input() if hasattr(ad, "to_evaluator_input") else ad
    ad_id = ad.ad_id if hasattr(ad, "ad_id") else ad_input.get("ad_id", "unknown")

    evaluation = evaluate_ad(
        ad_input,
        campaign_goal=brief.get("campaign_goal", "conversion"),
        audience=brief.get("audience", "parents"),
        ledger_path=ledger_path,
        persona=persona,
    )
    routing = route_ad(
        ad_id=ad_id,
        aggregate_score=evaluation.aggregate_score,
        campaign_goal=brief.get("campaign_goal", "conversion"),
        config=session_config,
        ledger_path=ledger_path,
    )
    return CopyEvaluation(evaluation=evaluation, routing=routing)


# PI-10: evaluate_visual() retired with the score_image / score_video
# legacy modules. The unified evaluate_media (evaluate/media_quality.py)
# now produces the per-variant rubric used by selection AND the rationale
# shown to the operator — no post-hoc winner re-scoring step is needed.
