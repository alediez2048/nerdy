"""Confidence-gated autonomy routing (P2-05).

Routes ads based on evaluator's self-rated confidence per dimension.
High confidence → autonomous; medium → flagged; low → human required.
Brand safety hard stop fires when any dimension scores < 4.0.
"""

from __future__ import annotations

from dataclasses import dataclass

from evaluate.evaluator import EvaluationResult
from iterate.ledger import read_events_filtered

DIMENSIONS = (
    "clarity",
    "value_proposition",
    "cta",
    "brand_voice",
    "emotional_resonance",
)

# Routing levels
AUTONOMOUS = "autonomous"
FLAGGED = "flagged"
HUMAN_REQUIRED = "human_required"
BRAND_SAFETY_STOP = "brand_safety_stop"

# Thresholds
BRAND_SAFETY_SCORE_FLOOR = 4.0
CONFIDENCE_AUTONOMOUS = 7.0
CONFIDENCE_FLAGGED_LOWER = 5.0


@dataclass
class ConfidenceRoutingResult:
    """Result of confidence-based routing for an ad."""

    ad_id: str
    confidence_level: str
    min_confidence: float
    low_confidence_dimensions: list[str]
    brand_safety_triggered: bool
    reason: str


@dataclass
class ConfidenceStats:
    """Aggregate confidence routing statistics for dashboard."""

    autonomous_count: int
    flagged_count: int
    human_required_count: int
    brand_safety_count: int
    total: int
    autonomous_pct: float
    flagged_pct: float
    human_required_pct: float
    brand_safety_pct: float


def route_by_confidence(evaluation_result: EvaluationResult) -> ConfidenceRoutingResult:
    """Route an ad based on evaluator confidence and brand safety.

    Routing priority:
    1. Brand safety: any dimension score < 4.0 → BRAND_SAFETY_STOP
    2. Confidence < 5.0 on any dimension → HUMAN_REQUIRED
    3. Confidence 5.0-7.0 on any dimension → FLAGGED
    4. All confidence > 7.0 → AUTONOMOUS

    Args:
        evaluation_result: The evaluation result with scores and confidence.

    Returns:
        ConfidenceRoutingResult with routing level and details.
    """
    ad_id = evaluation_result.ad_id
    scores = evaluation_result.scores

    # 1. Brand safety check: any dimension score < 4.0
    for dim in DIMENSIONS:
        dim_data = scores.get(dim, {})
        score = float(dim_data.get("score", 5.0))
        if score < BRAND_SAFETY_SCORE_FLOOR:
            return ConfidenceRoutingResult(
                ad_id=ad_id,
                confidence_level=BRAND_SAFETY_STOP,
                min_confidence=0.0,
                low_confidence_dimensions=[dim],
                brand_safety_triggered=True,
                reason=f"Brand safety: {dim} scored {score:.1f} (< {BRAND_SAFETY_SCORE_FLOOR})",
            )

    # 2. Extract confidence per dimension
    confidences: dict[str, float] = {}
    low_conf_dims: list[str] = []

    for dim in DIMENSIONS:
        dim_data = scores.get(dim, {})
        conf = float(dim_data.get("confidence", 7.0))
        confidences[dim] = conf
        if conf < CONFIDENCE_AUTONOMOUS:
            low_conf_dims.append(dim)

    min_conf = min(confidences.values()) if confidences else 0.0

    # 3. Route by minimum confidence
    if min_conf < CONFIDENCE_FLAGGED_LOWER:
        level = HUMAN_REQUIRED
        reason = f"Low confidence: min={min_conf:.1f} on {', '.join(low_conf_dims)}"
    elif min_conf < CONFIDENCE_AUTONOMOUS:
        level = FLAGGED
        reason = f"Medium confidence: min={min_conf:.1f} on {', '.join(low_conf_dims)}"
    else:
        level = AUTONOMOUS
        reason = f"All dimensions confidence >= {CONFIDENCE_AUTONOMOUS}"

    return ConfidenceRoutingResult(
        ad_id=ad_id,
        confidence_level=level,
        min_confidence=min_conf,
        low_confidence_dimensions=low_conf_dims,
        brand_safety_triggered=False,
        reason=reason,
    )


def get_confidence_stats(ledger_path: str) -> ConfidenceStats:
    """Aggregate confidence routing statistics from the ledger.

    Args:
        ledger_path: Path to the JSONL ledger.

    Returns:
        ConfidenceStats with counts and percentages per routing level.
    """
    events = read_events_filtered(ledger_path, event_type="ConfidenceRouted")

    counts = {
        AUTONOMOUS: 0,
        FLAGGED: 0,
        HUMAN_REQUIRED: 0,
        BRAND_SAFETY_STOP: 0,
    }

    for event in events:
        level = event.get("outputs", {}).get("confidence_level", "")
        if level in counts:
            counts[level] += 1

    total = sum(counts.values())

    def pct(c: int) -> float:
        return round(c / total * 100, 1) if total > 0 else 0.0

    return ConfidenceStats(
        autonomous_count=counts[AUTONOMOUS],
        flagged_count=counts[FLAGGED],
        human_required_count=counts[HUMAN_REQUIRED],
        brand_safety_count=counts[BRAND_SAFETY_STOP],
        total=total,
        autonomous_pct=pct(counts[AUTONOMOUS]),
        flagged_pct=pct(counts[FLAGGED]),
        human_required_pct=pct(counts[HUMAN_REQUIRED]),
        brand_safety_pct=pct(counts[BRAND_SAFETY_STOP]),
    )
