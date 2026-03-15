"""Statistical Process Control (SPC) drift detection + canary injection (P2-04).

Tracks evaluator score distributions across batches using control charts
with ±2σ limits. When a batch breaches limits, canary ads (known-score
references) diagnose whether the drift is real quality change or evaluator
instability.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from iterate.ledger import read_events_filtered

DIMENSIONS = (
    "clarity",
    "value_proposition",
    "cta",
    "brand_voice",
    "emotional_resonance",
)

MIN_BATCHES_FOR_LIMITS = 5
CANARY_TOLERANCE = 1.0  # ±1.0 from human scores = stable


@dataclass
class ControlLimits:
    """SPC control limits for batch score averages."""

    mean: float
    ucl: float  # Upper control limit
    lcl: float  # Lower control limit
    sigma: float


@dataclass
class DriftReport:
    """Result of drift detection across batches."""

    is_stable: bool
    breaches: list[dict]  # [{batch_index, batch_avg, direction: "high"|"low"}]
    limits: ControlLimits | None
    batch_count: int


@dataclass
class DriftDiagnosis:
    """Diagnosis of whether drift is evaluator-caused or real quality change."""

    is_evaluator_drift: bool
    affected_dimensions: list[str]
    recommendation: str
    canary_deviations: dict[str, float] = field(default_factory=dict)


@dataclass
class ControlChartData:
    """Dashboard-ready control chart data."""

    batch_averages: list[float]
    ucl: float | None
    lcl: float | None
    mean: float | None
    breach_indices: list[int]


def compute_control_limits(
    batch_averages: list[float],
    sigma_multiplier: float = 2.0,
) -> ControlLimits | None:
    """Compute control limits from batch averages.

    Args:
        batch_averages: List of per-batch average scores.
        sigma_multiplier: Number of standard deviations for limits (default 2.0).

    Returns:
        ControlLimits or None if insufficient data (< 5 batches).
    """
    if len(batch_averages) < MIN_BATCHES_FOR_LIMITS:
        return None

    n = len(batch_averages)
    mean = sum(batch_averages) / n
    variance = sum((x - mean) ** 2 for x in batch_averages) / n
    sigma = math.sqrt(variance)

    # Prevent zero sigma (all identical scores)
    if sigma == 0:
        sigma = 0.01

    return ControlLimits(
        mean=round(mean, 4),
        ucl=round(mean + sigma_multiplier * sigma, 4),
        lcl=round(mean - sigma_multiplier * sigma, 4),
        sigma=round(sigma, 4),
    )


def is_in_control(batch_avg: float, limits: ControlLimits) -> bool:
    """Check whether a batch average is within control limits.

    Args:
        batch_avg: The batch's average score.
        limits: The control limits to check against.

    Returns:
        True if LCL <= batch_avg <= UCL.
    """
    return limits.lcl <= batch_avg <= limits.ucl


def detect_drift(ledger_path: str) -> DriftReport:
    """Detect evaluator drift from batch data in the ledger.

    Reads BatchCompleted events, extracts per-batch average scores,
    establishes baseline from first N batches, and checks subsequent
    batches against control limits.

    Args:
        ledger_path: Path to the JSONL ledger.

    Returns:
        DriftReport with stability status and any breaches.
    """
    events = read_events_filtered(ledger_path, event_type="BatchCompleted")

    batch_avgs: list[float] = []
    for event in events:
        outputs = event.get("outputs", {})
        avg = outputs.get("batch_avg_score")
        if avg is not None:
            batch_avgs.append(float(avg))

    if len(batch_avgs) < MIN_BATCHES_FOR_LIMITS:
        return DriftReport(
            is_stable=True,
            breaches=[],
            limits=None,
            batch_count=len(batch_avgs),
        )

    # Use first 5 batches as baseline
    baseline = batch_avgs[:MIN_BATCHES_FOR_LIMITS]
    limits = compute_control_limits(baseline)

    if limits is None:
        return DriftReport(
            is_stable=True,
            breaches=[],
            limits=None,
            batch_count=len(batch_avgs),
        )

    breaches: list[dict] = []
    for i in range(MIN_BATCHES_FOR_LIMITS, len(batch_avgs)):
        avg = batch_avgs[i]
        if not is_in_control(avg, limits):
            direction = "high" if avg > limits.ucl else "low"
            breaches.append({
                "batch_index": i,
                "batch_avg": avg,
                "direction": direction,
            })

    return DriftReport(
        is_stable=len(breaches) == 0,
        breaches=breaches,
        limits=limits,
        batch_count=len(batch_avgs),
    )


def get_control_chart_data(ledger_path: str) -> ControlChartData:
    """Get dashboard-ready control chart data.

    Args:
        ledger_path: Path to the JSONL ledger.

    Returns:
        ControlChartData with batch averages, limits, and breach indices.
    """
    events = read_events_filtered(ledger_path, event_type="BatchCompleted")

    batch_avgs: list[float] = []
    for event in events:
        outputs = event.get("outputs", {})
        avg = outputs.get("batch_avg_score")
        if avg is not None:
            batch_avgs.append(float(avg))

    limits = compute_control_limits(batch_avgs)

    breach_indices: list[int] = []
    if limits:
        for i, avg in enumerate(batch_avgs):
            if not is_in_control(avg, limits):
                breach_indices.append(i)

    return ControlChartData(
        batch_averages=batch_avgs,
        ucl=limits.ucl if limits else None,
        lcl=limits.lcl if limits else None,
        mean=limits.mean if limits else None,
        breach_indices=breach_indices,
    )


def inject_canary(
    golden_ads_path: str,
    count: int = 3,
) -> list[dict]:
    """Select diverse canary ads from the golden set.

    Picks one ad per quality tier (excellent, good, poor) for balanced
    drift diagnosis.

    Args:
        golden_ads_path: Path to golden_ads.json.
        count: Number of canaries to select (default 3).

    Returns:
        List of canary ad dicts with ad_id, ad_text, quality_label, human_scores.
    """
    with open(golden_ads_path, encoding="utf-8") as f:
        data = json.load(f)

    ads = data["ads"]
    by_label: dict[str, list[dict]] = {}
    for ad in ads:
        label = ad.get("quality_label", "unknown")
        by_label.setdefault(label, []).append(ad)

    canaries: list[dict] = []
    # Pick one from each tier
    for label in ("excellent", "good", "poor"):
        tier_ads = by_label.get(label, [])
        if tier_ads:
            ad = tier_ads[0]
            canaries.append({
                "ad_id": ad["ad_id"],
                "ad_text": ad["primary_text"],
                "quality_label": label,
                "human_scores": ad["human_scores"],
            })
        if len(canaries) >= count:
            break

    return canaries[:count]


def diagnose_drift(
    canary_results: list[dict],
    golden_scores: list[dict],
) -> DriftDiagnosis:
    """Diagnose whether drift is evaluator-caused or real quality change.

    Compares canary evaluation scores against known human scores.
    If canary scores diverge from humans, evaluator has drifted.

    Args:
        canary_results: List of dicts with ad_id, scores (per-dimension).
        golden_scores: List of dicts with ad_id, human_scores (per-dimension).

    Returns:
        DriftDiagnosis with cause and affected dimensions.
    """
    golden_map: dict[str, dict[str, float]] = {}
    for g in golden_scores:
        golden_map[g["ad_id"]] = g["human_scores"]

    deviations: dict[str, list[float]] = {d: [] for d in DIMENSIONS}
    total_deviation = 0.0
    total_comparisons = 0

    for result in canary_results:
        ad_id = result["ad_id"]
        human = golden_map.get(ad_id, {})
        eval_scores = result.get("scores", {})

        for dim in DIMENSIONS:
            h = human.get(dim)
            e = eval_scores.get(dim)
            if h is not None and e is not None:
                dev = abs(float(e) - float(h))
                deviations[dim].append(dev)
                total_deviation += dev
                total_comparisons += 1

    avg_deviation = total_deviation / total_comparisons if total_comparisons else 0.0

    affected: list[str] = []
    dim_avg_devs: dict[str, float] = {}
    for dim, devs in deviations.items():
        if devs:
            avg = sum(devs) / len(devs)
            dim_avg_devs[dim] = round(avg, 2)
            if avg > CANARY_TOLERANCE:
                affected.append(dim)

    is_drift = avg_deviation > CANARY_TOLERANCE

    if is_drift:
        recommendation = (
            f"Evaluator drift detected (avg deviation: {avg_deviation:.2f}). "
            f"Affected dimensions: {', '.join(affected) or 'general'}. "
            "Recommend re-calibrating evaluation prompt against golden set."
        )
    else:
        recommendation = (
            f"Evaluator stable (avg deviation: {avg_deviation:.2f}). "
            "Score changes reflect real quality variation, not evaluator drift."
        )

    return DriftDiagnosis(
        is_evaluator_drift=is_drift,
        affected_dimensions=affected,
        recommendation=recommendation,
        canary_deviations=dim_avg_devs,
    )
