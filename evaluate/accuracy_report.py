"""Evaluator accuracy report — compares LLM scores vs real-world performance (PF-05).

Measures how well our evaluator's top-scored ads align with top-performing ads
by real metrics. Computes precision@k, recall@k, confusion matrix, and identifies
false positives (high score, low performance) and missed performers (low score, high performance).
"""

from __future__ import annotations

from dataclasses import dataclass

from evaluate.performance_schema import MetaPerformanceRecord


@dataclass
class ConfusionMatrix:
    """Binary confusion matrix using score threshold and performance median."""

    true_positive: int = 0   # High score AND high performance
    false_positive: int = 0  # High score BUT low performance
    true_negative: int = 0   # Low score AND low performance
    false_negative: int = 0  # Low score BUT high performance

    @property
    def total(self) -> int:
        return self.true_positive + self.false_positive + self.true_negative + self.false_negative

    @property
    def precision(self) -> float:
        denom = self.true_positive + self.false_positive
        return self.true_positive / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        denom = self.true_positive + self.false_negative
        return self.true_positive / denom if denom > 0 else 0.0


@dataclass
class AccuracyReport:
    """Complete evaluator accuracy assessment."""

    precision_at_k: float        # Fraction of top-k-by-score in top-2k-by-CTR
    recall_at_k: float           # Fraction of top-k-by-CTR scored >= threshold
    k: int
    false_positives: list[dict]  # Ads scored >= threshold but below-median CTR
    missed_performers: list[dict]  # Ads scored < threshold but top-quartile CTR
    confusion: ConfusionMatrix
    findings: list[str]
    sample_size: int


def compute_accuracy(
    eval_scores: list[dict],
    perf_records: list[MetaPerformanceRecord],
    k: int = 10,
    score_threshold: float = 7.0,
    performance_metric: str = "ctr",
) -> AccuracyReport:
    """Compare evaluator rankings vs real-world performance.

    Args:
        eval_scores: List of dicts with 'ad_id' and 'aggregate_score'.
        perf_records: List of MetaPerformanceRecord objects.
        k: Top-k for precision/recall calculation.
        score_threshold: Score threshold for pass/fail (default 7.0).
        performance_metric: Which metric to use as ground truth.

    Returns:
        AccuracyReport with precision@k, recall@k, confusion matrix, findings.
    """
    # Build lookups
    score_lookup = {e["ad_id"]: e.get("aggregate_score", 0) for e in eval_scores}
    perf_lookup = {r.ad_id: _get_perf_value(r, performance_metric) for r in perf_records}

    # Common ads
    common = sorted(set(score_lookup.keys()) & set(perf_lookup.keys()))
    if not common:
        return AccuracyReport(
            precision_at_k=0.0, recall_at_k=0.0, k=k,
            false_positives=[], missed_performers=[],
            confusion=ConfusionMatrix(),
            findings=["No overlapping ads between scores and performance data."],
            sample_size=0,
        )

    n = len(common)
    actual_k = min(k, n)

    # Rank by score and by performance
    by_score = sorted(common, key=lambda aid: score_lookup[aid], reverse=True)
    by_perf = sorted(common, key=lambda aid: perf_lookup[aid], reverse=True)

    top_k_by_score = set(by_score[:actual_k])
    top_2k_by_perf = set(by_perf[:min(actual_k * 2, n)])
    top_k_by_perf = set(by_perf[:actual_k])

    # Precision@k: fraction of our top-k in the real top-2k
    overlap_precision = top_k_by_score & top_2k_by_perf
    precision_at_k = len(overlap_precision) / actual_k if actual_k > 0 else 0.0

    # Recall@k: fraction of real top-k that we scored >= threshold
    high_scorers = {aid for aid in common if score_lookup[aid] >= score_threshold}
    overlap_recall = top_k_by_perf & high_scorers
    recall_at_k = len(overlap_recall) / actual_k if actual_k > 0 else 0.0

    # Median performance for confusion matrix
    perf_values = sorted(perf_lookup[aid] for aid in common)
    median_perf = perf_values[n // 2]

    # Top quartile threshold
    q75_idx = int(n * 0.75)
    top_quartile_threshold = perf_values[q75_idx] if q75_idx < n else median_perf

    # Confusion matrix
    cm = ConfusionMatrix()
    false_positives: list[dict] = []
    missed_performers: list[dict] = []

    for aid in common:
        score = score_lookup[aid]
        perf = perf_lookup[aid]
        high_score = score >= score_threshold
        high_perf = perf >= median_perf

        if high_score and high_perf:
            cm.true_positive += 1
        elif high_score and not high_perf:
            cm.false_positive += 1
            false_positives.append({
                "ad_id": aid,
                "score": round(score, 2),
                performance_metric: round(perf, 6),
            })
        elif not high_score and not high_perf:
            cm.true_negative += 1
        else:  # not high_score and high_perf
            cm.false_negative += 1
            if perf >= top_quartile_threshold:
                missed_performers.append({
                    "ad_id": aid,
                    "score": round(score, 2),
                    performance_metric: round(perf, 6),
                })

    # Sort by most surprising first
    false_positives.sort(key=lambda x: x[performance_metric])
    missed_performers.sort(key=lambda x: x[performance_metric], reverse=True)

    # Generate findings
    findings = _generate_findings(
        precision_at_k, recall_at_k, actual_k, cm,
        false_positives, missed_performers, performance_metric, n,
    )

    return AccuracyReport(
        precision_at_k=round(precision_at_k, 4),
        recall_at_k=round(recall_at_k, 4),
        k=actual_k,
        false_positives=false_positives,
        missed_performers=missed_performers,
        confusion=cm,
        findings=findings,
        sample_size=n,
    )


def _get_perf_value(record: MetaPerformanceRecord, metric: str) -> float:
    if metric == "ctr":
        return record.ctr
    elif metric == "engagement_rate":
        return record.engagement_rate
    elif metric == "relevance_score":
        return record.relevance_score
    elif metric == "conversion_rate":
        return record.conversions / record.clicks if record.clicks > 0 else 0.0
    return 0.0


def _generate_findings(
    precision: float, recall: float, k: int,
    cm: ConfusionMatrix,
    false_pos: list[dict], missed: list[dict],
    metric: str, n: int,
) -> list[str]:
    findings: list[str] = []

    # Overall assessment
    if precision >= 0.7:
        findings.append(
            f"Strong alignment: {precision:.0%} of our top-{k} ads by score are in the "
            f"real top-{k*2} by {metric} (n={n})."
        )
    elif precision >= 0.4:
        findings.append(
            f"Moderate alignment: {precision:.0%} of our top-{k} ads by score are in the "
            f"real top-{k*2} by {metric}. Copy quality partially predicts performance (n={n})."
        )
    else:
        findings.append(
            f"Weak alignment: only {precision:.0%} of our top-{k} ads by score are in the "
            f"real top-{k*2} by {metric}. Factors beyond copy quality dominate performance (n={n})."
        )

    # Recall
    findings.append(
        f"Recall@{k}: {recall:.0%} of the top-{k} real performers were scored above threshold."
    )

    # Confusion matrix summary
    findings.append(
        f"Confusion matrix: {cm.true_positive} true positives, {cm.false_positive} false positives, "
        f"{cm.false_negative} false negatives, {cm.true_negative} true negatives "
        f"(precision={cm.precision:.0%}, recall={cm.recall:.0%})."
    )

    # Biggest surprise
    if missed:
        top_miss = missed[0]
        findings.append(
            f"Biggest miss: {top_miss['ad_id']} scored {top_miss['score']:.1f} but had "
            f"{metric}={top_miss[metric]:.4f} (top quartile). Likely benefited from "
            f"strong targeting or audience match rather than copy quality."
        )

    if false_pos:
        worst_fp = false_pos[0]
        findings.append(
            f"Biggest false positive: {worst_fp['ad_id']} scored {worst_fp['score']:.1f} but had "
            f"{metric}={worst_fp[metric]:.4f} (below median). Good copy doesn't guarantee good performance."
        )

    # Actionable recommendation
    if cm.false_negative > cm.false_positive:
        findings.append(
            "Recommendation: The evaluator is too conservative — it misses more good performers "
            "than it promotes bad ones. Consider lowering the threshold or adjusting weights "
            "based on PF-04 recalibration."
        )
    elif cm.false_positive > cm.false_negative:
        findings.append(
            "Recommendation: The evaluator is too lenient — it promotes more underperformers "
            "than it misses. Consider raising the threshold or adding performance-aware signals."
        )

    return findings


def format_accuracy_report(report: AccuracyReport) -> str:
    """Format the accuracy report as a readable summary."""
    lines = [
        "=== Evaluator Accuracy Report ===",
        "",
        f"Sample size: {report.sample_size}",
        f"Precision@{report.k}: {report.precision_at_k:.1%}",
        f"Recall@{report.k}: {report.recall_at_k:.1%}",
        "",
        "Confusion Matrix:",
        f"  True Positive:  {report.confusion.true_positive}",
        f"  False Positive: {report.confusion.false_positive}",
        f"  True Negative:  {report.confusion.true_negative}",
        f"  False Negative: {report.confusion.false_negative}",
        "",
        f"False Positives (scored high, performed low): {len(report.false_positives)}",
        f"Missed Performers (scored low, performed high): {len(report.missed_performers)}",
        "",
        "Findings:",
    ]
    for i, f in enumerate(report.findings, 1):
        lines.append(f"  {i}. {f}")

    return "\n".join(lines)
