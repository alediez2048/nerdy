"""Brief mutation + escalation — self-aware failure handling (P1-08, R1-Q2).

When Pareto selection (P1-07) fails to find a non-regressing variant, the
problem is the brief, not the generator. This module:

1. Diagnoses the weakest dimension from evaluation scores.
2. Mutates the brief with targeted adjustments for that dimension.
3. Escalates with full diagnostics if mutation also fails.

Cycle budget from config: max_regeneration_cycles (default 3).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from iterate.ledger import log_event

logger = logging.getLogger(__name__)

DIMENSIONS = (
    "clarity",
    "value_proposition",
    "cta",
    "brand_voice",
    "emotional_resonance",
)

# Dimension-specific mutation strategies (R1-Q2)
_MUTATION_STRATEGIES: dict[str, str] = {
    "clarity": (
        "Simplify the core message. Reduce competing claims to a single, "
        "clear value statement. Remove jargon and ensure the hook "
        "communicates one idea in one sentence."
    ),
    "value_proposition": (
        "Add specific proof points and differentiation. Include concrete "
        "outcomes (score improvements, success rates) and explain what "
        "makes this offer different from competitors."
    ),
    "cta": (
        "Make the call-to-action more specific and lower-friction. Add "
        "urgency without false scarcity. Replace generic CTAs with "
        "action-oriented next steps (e.g., 'Start Free Practice Test')."
    ),
    "brand_voice": (
        "Strengthen audience-specific tone. For parents: authoritative and "
        "reassuring. For students: relatable and motivating. Add language "
        "that reflects expertise without being condescending."
    ),
    "emotional_resonance": (
        "Target a specific emotion relevant to the audience. For parents: "
        "college anxiety, desire to help their child succeed. For students: "
        "test anxiety, competitive drive, future ambition. Use concrete "
        "scenarios, not abstract statements."
    ),
}


@dataclass
class MutationDiagnosis:
    """Diagnosis of the weakest dimension with a mutation strategy."""

    ad_id: str
    weakest_dimension: str
    score: float
    rationale: str
    suggested_mutation: str


@dataclass
class EscalationReport:
    """Full diagnostic report for human review."""

    ad_id: str
    attempts: list[dict[str, Any]]
    diagnosis: MutationDiagnosis
    mutation_applied: bool
    reason_for_escalation: str


def diagnose_weakness(
    ad_id: str, scores: dict[str, dict[str, Any]]
) -> MutationDiagnosis:
    """Identify the lowest-scoring dimension and map to mutation strategy.

    Args:
        ad_id: The ad identifier.
        scores: Dict mapping dimension name to score dict (with 'score', 'rationale' keys).

    Returns:
        MutationDiagnosis with weakest dimension and suggested mutation.
    """
    weakest_dim = min(
        DIMENSIONS,
        key=lambda d: scores.get(d, {}).get("score", 5.0),
    )
    dim_data = scores.get(weakest_dim, {})
    score = dim_data.get("score", 5.0)
    rationale = dim_data.get("rationale", "No rationale available")
    mutation = _MUTATION_STRATEGIES.get(weakest_dim, "Review and improve this dimension.")

    logger.info(
        "Diagnosed %s: weakest=%s (%.1f)", ad_id, weakest_dim, score
    )

    return MutationDiagnosis(
        ad_id=ad_id,
        weakest_dimension=weakest_dim,
        score=score,
        rationale=rationale,
        suggested_mutation=mutation,
    )


def mutate_brief(
    original_brief: dict[str, Any],
    diagnosis: MutationDiagnosis,
    ledger_path: str | None = None,
) -> dict[str, Any]:
    """Apply targeted mutation to the brief based on diagnosis.

    Preserves all original fields; adds mutation metadata and guidance
    for the generator to focus on the weak dimension.

    Args:
        original_brief: The original brief dict.
        diagnosis: Diagnosis from diagnose_weakness().
        ledger_path: Optional ledger path for logging.

    Returns:
        New brief dict with mutation context added.
    """
    mutated = dict(original_brief)
    mutated["mutation"] = {
        "target_dimension": diagnosis.weakest_dimension,
        "prior_score": diagnosis.score,
        "guidance": diagnosis.suggested_mutation,
        "rationale": diagnosis.rationale,
    }

    logger.info(
        "Mutated brief for %s: targeting %s (was %.1f)",
        diagnosis.ad_id,
        diagnosis.weakest_dimension,
        diagnosis.score,
    )

    if ledger_path:
        log_event(
            ledger_path,
            {
                "event_type": "BriefMutated",
                "ad_id": diagnosis.ad_id,
                "brief_id": original_brief.get("brief_id", "unknown"),
                "cycle_number": 0,
                "action": "brief-mutation",
                "tokens_consumed": 0,
                "model_used": "none",
                "seed": "0",
                "inputs": {
                    "weakest_dimension": diagnosis.weakest_dimension,
                    "score": diagnosis.score,
                },
                "outputs": {
                    "mutation_guidance": diagnosis.suggested_mutation,
                },
            },
        )

    return mutated


def should_escalate(cycle: int, config: dict[str, Any]) -> bool:
    """Check if the current cycle has reached the escalation threshold.

    Args:
        cycle: Current regeneration cycle number (1-indexed).
        config: Config dict with max_regeneration_cycles.

    Returns:
        True if cycle >= max_regeneration_cycles.
    """
    max_cycles = config.get("max_regeneration_cycles", 3)
    return cycle >= max_cycles


def escalate(
    ad_id: str,
    attempts: list[dict[str, Any]],
    diagnosis: MutationDiagnosis,
    ledger_path: str | None = None,
) -> EscalationReport:
    """Archive ad with full diagnostics for human review.

    Args:
        ad_id: The ad identifier.
        attempts: List of attempt dicts (cycle, scores per attempt).
        diagnosis: Final diagnosis from the last failed cycle.
        ledger_path: Optional ledger path for logging.

    Returns:
        EscalationReport with full diagnostic context.
    """
    reason = (
        f"Ad {ad_id} failed to meet quality threshold after "
        f"{len(attempts)} regeneration cycles. Weakest dimension: "
        f"{diagnosis.weakest_dimension} (score: {diagnosis.score:.1f}). "
        f"Brief mutation was applied but did not resolve the issue. "
        f"Escalating for human review."
    )

    report = EscalationReport(
        ad_id=ad_id,
        attempts=attempts,
        diagnosis=diagnosis,
        mutation_applied=True,
        reason_for_escalation=reason,
    )

    logger.warning("Escalated %s after %d attempts: %s", ad_id, len(attempts), reason)

    if ledger_path:
        log_event(
            ledger_path,
            {
                "event_type": "AdEscalated",
                "ad_id": ad_id,
                "brief_id": "unknown",
                "cycle_number": len(attempts),
                "action": "escalation",
                "tokens_consumed": 0,
                "model_used": "none",
                "seed": "0",
                "inputs": {
                    "attempts_count": len(attempts),
                    "weakest_dimension": diagnosis.weakest_dimension,
                    "weakest_score": diagnosis.score,
                },
                "outputs": {
                    "reason": reason,
                    "attempts": attempts,
                },
            },
        )

    return report
