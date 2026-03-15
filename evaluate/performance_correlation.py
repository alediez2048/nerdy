"""Evaluator-Performance correlation analysis (PF-03).

Measures Pearson correlation between each of the 5 evaluation dimensions
and 4 real-world performance metrics (CTR, conversion_rate, engagement_rate,
relevance_score). Identifies which dimensions actually predict outcomes.

Reuses _pearson_r from evaluate.correlation (no scipy dependency).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from evaluate.correlation import DIMENSIONS, _pearson_r
from evaluate.performance_schema import MetaPerformanceRecord


PERFORMANCE_METRICS = ("ctr", "conversion_rate", "engagement_rate", "relevance_score")


@dataclass
class DimensionPerformanceMatrix:
    """5×4 correlation matrix: dimensions vs. performance metrics."""

    matrix: dict[tuple[str, str], float]  # (dimension, metric) -> r
    strongest_predictors: dict[str, tuple[str, float]]  # metric -> (dimension, r)
    weakest_predictors: dict[str, tuple[str, float]]  # metric -> (dimension, r)
    findings: list[str]
    sample_size: int


def _compute_conversion_rates(records: list[MetaPerformanceRecord]) -> dict[str, float]:
    """Compute conversion_rate per ad_id (conversions / clicks)."""
    rates: dict[str, float] = {}
    for r in records:
        if r.clicks > 0:
            rates[r.ad_id] = r.conversions / r.clicks
        else:
            rates[r.ad_id] = 0.0
    return rates


def _get_metric_value(record: MetaPerformanceRecord, metric: str, conv_rates: dict[str, float]) -> float:
    """Extract metric value from a performance record."""
    if metric == "ctr":
        return record.ctr
    elif metric == "conversion_rate":
        return conv_rates.get(record.ad_id, 0.0)
    elif metric == "engagement_rate":
        return record.engagement_rate
    elif metric == "relevance_score":
        return record.relevance_score
    else:
        raise ValueError(f"Unknown metric: {metric}")


def compute_dimension_performance_matrix(
    eval_scores: list[dict],
    perf_records: list[MetaPerformanceRecord],
) -> DimensionPerformanceMatrix:
    """Compute correlation matrix between evaluation dimensions and performance metrics.

    Args:
        eval_scores: List of dicts with 'ad_id' and 'scores' (dict of dimension->float).
        perf_records: List of MetaPerformanceRecord objects.

    Returns:
        DimensionPerformanceMatrix with 20 correlation coefficients and findings.
    """
    # Build lookup: ad_id -> scores
    score_lookup: dict[str, dict[str, float]] = {}
    for entry in eval_scores:
        ad_id = entry.get("ad_id", "")
        scores = entry.get("scores", {})
        if ad_id and scores:
            score_lookup[ad_id] = scores

    # Build lookup: ad_id -> performance record
    perf_lookup: dict[str, MetaPerformanceRecord] = {}
    for r in perf_records:
        perf_lookup[r.ad_id] = r

    # Find ads present in both datasets
    common_ids = sorted(set(score_lookup.keys()) & set(perf_lookup.keys()))

    if len(common_ids) < 2:
        return DimensionPerformanceMatrix(
            matrix={},
            strongest_predictors={},
            weakest_predictors={},
            findings=["Insufficient data: need at least 2 ads with both scores and performance data."],
            sample_size=len(common_ids),
        )

    # Precompute conversion rates
    conv_rates = _compute_conversion_rates(perf_records)

    # Compute 5x4 matrix
    matrix: dict[tuple[str, str], float] = {}

    for dim in DIMENSIONS:
        dim_values = [score_lookup[aid].get(dim, 5.0) for aid in common_ids]

        for metric in PERFORMANCE_METRICS:
            metric_values = [
                _get_metric_value(perf_lookup[aid], metric, conv_rates)
                for aid in common_ids
            ]
            r = round(_pearson_r(dim_values, metric_values), 4)
            matrix[(dim, metric)] = r

    # Find strongest/weakest predictors per metric
    strongest: dict[str, tuple[str, float]] = {}
    weakest: dict[str, tuple[str, float]] = {}

    for metric in PERFORMANCE_METRICS:
        correlations = [(dim, matrix[(dim, metric)]) for dim in DIMENSIONS]
        by_abs = sorted(correlations, key=lambda x: abs(x[1]), reverse=True)
        strongest[metric] = (by_abs[0][0], by_abs[0][1])
        weakest[metric] = (by_abs[-1][0], by_abs[-1][1])

    # Generate findings
    findings = _generate_findings(matrix, strongest, weakest, len(common_ids))

    return DimensionPerformanceMatrix(
        matrix=matrix,
        strongest_predictors=strongest,
        weakest_predictors=weakest,
        findings=findings,
        sample_size=len(common_ids),
    )


def _generate_findings(
    matrix: dict[tuple[str, str], float],
    strongest: dict[str, tuple[str, float]],
    weakest: dict[str, tuple[str, float]],
    sample_size: int,
) -> list[str]:
    """Generate plain-English findings from the correlation matrix."""
    findings: list[str] = []

    # 1. Strongest predictor per metric
    for metric in PERFORMANCE_METRICS:
        dim, r = strongest[metric]
        direction = "positively" if r > 0 else "negatively"
        label = _dim_label(dim)
        metric_label = _metric_label(metric)
        findings.append(
            f"{label} is the strongest predictor of {metric_label} "
            f"(r={r:+.3f}, {direction} correlated, n={sample_size})."
        )

    # 2. Notable weak correlations (|r| < 0.1)
    for (dim, metric), r in matrix.items():
        if abs(r) < 0.1:
            findings.append(
                f"{_dim_label(dim)} has no significant correlation with "
                f"{_metric_label(metric)} (r={r:+.3f})."
            )

    # 3. Surprising findings (dimensions that predict unexpected metrics)
    # e.g., if brand_voice predicts CTR strongly
    for (dim, metric), r in matrix.items():
        if abs(r) > 0.4:
            findings.append(
                f"Notable: {_dim_label(dim)} has a strong correlation with "
                f"{_metric_label(metric)} (r={r:+.3f}). "
                f"This {'validates' if _is_expected(dim, metric) else 'challenges'} "
                f"prior assumptions."
            )

    return findings


def _is_expected(dim: str, metric: str) -> bool:
    """Check if a dimension-metric correlation is expected based on prior assumptions."""
    expected = {
        ("cta", "conversion_rate"),
        ("value_proposition", "conversion_rate"),
        ("emotional_resonance", "engagement_rate"),
        ("brand_voice", "engagement_rate"),
        ("clarity", "ctr"),
    }
    return (dim, metric) in expected


def _dim_label(dim: str) -> str:
    labels = {
        "clarity": "Clarity",
        "value_proposition": "Value Proposition",
        "cta": "Call to Action",
        "brand_voice": "Brand Voice",
        "emotional_resonance": "Emotional Resonance",
    }
    return labels.get(dim, dim)


def _metric_label(metric: str) -> str:
    labels = {
        "ctr": "CTR",
        "conversion_rate": "Conversion Rate",
        "engagement_rate": "Engagement Rate",
        "relevance_score": "Relevance Score",
    }
    return labels.get(metric, metric)


def format_performance_matrix(matrix_result: DimensionPerformanceMatrix) -> str:
    """Format the dimension-performance correlation matrix as a readable table."""
    if not matrix_result.matrix:
        return "No correlation data available."

    # Short labels
    dim_labels = {"clarity": "CLAR", "value_proposition": "VP", "cta": "CTA",
                  "brand_voice": "BV", "emotional_resonance": "ER"}
    metric_labels = {"ctr": "CTR", "conversion_rate": "CONV",
                     "engagement_rate": "ENG", "relevance_score": "REL"}

    header = f"{'':>6}" + "".join(f"{metric_labels[m]:>8}" for m in PERFORMANCE_METRICS)
    lines = [header, "-" * len(header)]

    for dim in DIMENSIONS:
        row = f"{dim_labels[dim]:>6}"
        for metric in PERFORMANCE_METRICS:
            r = matrix_result.matrix.get((dim, metric), 0.0)
            row += f"{r:>8.3f}"
        lines.append(row)

    lines.append("")
    lines.append(f"Sample size: {matrix_result.sample_size}")
    lines.append("")
    lines.append("Findings:")
    for i, finding in enumerate(matrix_result.findings, 1):
        lines.append(f"  {i}. {finding}")

    return "\n".join(lines)
