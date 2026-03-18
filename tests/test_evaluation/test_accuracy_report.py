"""Tests for evaluator accuracy report (PF-05)."""

from evaluate.accuracy_report import (
    ConfusionMatrix,
    compute_accuracy,
    format_accuracy_report,
)
from evaluate.performance_schema import MetaPerformanceRecord


def _make_record(ad_id: str, ctr: float, conversions: int = 5) -> MetaPerformanceRecord:
    clicks = max(1, int(10000 * ctr))
    return MetaPerformanceRecord(
        ad_id=ad_id, campaign_id="c", impressions=10000, clicks=clicks,
        ctr=ctr, conversions=conversions,
        cpa=round(50.0 / conversions, 2) if conversions > 0 else None,
        spend=50.0, engagement_rate=0.03, relevance_score=7.0,
        date_range_start="2026-03-01", date_range_end="2026-03-07",
        placement="feed", audience_segment="parents",
    )


def _make_test_data():
    """Create 20 ads with known score-performance relationship."""
    eval_scores = []
    perf_records = []

    for i in range(20):
        ad_id = f"ad_{i:03d}"
        # Mostly correlated but with some mismatches
        if i < 10:  # High score, mostly high CTR
            score = 7.0 + i * 0.2
            ctr = 0.02 + i * 0.002 if i != 5 else 0.005  # ad_005 is false positive
        else:  # Low score, mostly low CTR
            score = 4.0 + (i - 10) * 0.2
            ctr = 0.005 + (i - 10) * 0.001 if i != 15 else 0.04  # ad_015 is missed performer

        eval_scores.append({"ad_id": ad_id, "aggregate_score": score})
        perf_records.append(_make_record(ad_id, ctr))

    return eval_scores, perf_records


class TestConfusionMatrix:
    def test_total_sums(self):
        cm = ConfusionMatrix(true_positive=5, false_positive=3, true_negative=8, false_negative=4)
        assert cm.total == 20

    def test_precision(self):
        cm = ConfusionMatrix(true_positive=8, false_positive=2, true_negative=5, false_negative=5)
        assert abs(cm.precision - 0.8) < 0.01

    def test_recall(self):
        cm = ConfusionMatrix(true_positive=8, false_positive=2, true_negative=5, false_negative=2)
        assert abs(cm.recall - 0.8) < 0.01

    def test_zero_division(self):
        cm = ConfusionMatrix()
        assert cm.precision == 0.0
        assert cm.recall == 0.0


class TestAccuracy:
    def test_computes_precision_at_k(self):
        scores, records = _make_test_data()
        report = compute_accuracy(scores, records, k=5)
        assert 0.0 <= report.precision_at_k <= 1.0

    def test_computes_recall_at_k(self):
        scores, records = _make_test_data()
        report = compute_accuracy(scores, records, k=5)
        assert 0.0 <= report.recall_at_k <= 1.0

    def test_confusion_matrix_sums(self):
        scores, records = _make_test_data()
        report = compute_accuracy(scores, records, k=5)
        assert report.confusion.total == 20

    def test_false_positives_identified(self):
        scores, records = _make_test_data()
        report = compute_accuracy(scores, records, k=5)
        # ad_005 has high score but low CTR
        fp_ids = [fp["ad_id"] for fp in report.false_positives]
        assert "ad_005" in fp_ids

    def test_missed_performers_identified(self):
        scores, records = _make_test_data()
        report = compute_accuracy(scores, records, k=5)
        # ad_015 has low score but high CTR
        mp_ids = [mp["ad_id"] for mp in report.missed_performers]
        assert "ad_015" in mp_ids

    def test_findings_generated(self):
        scores, records = _make_test_data()
        report = compute_accuracy(scores, records, k=5)
        assert len(report.findings) >= 3

    def test_empty_data(self):
        report = compute_accuracy([], [], k=5)
        assert report.sample_size == 0

    def test_sample_size_correct(self):
        scores, records = _make_test_data()
        report = compute_accuracy(scores, records, k=5)
        assert report.sample_size == 20


class TestFormatting:
    def test_format_produces_report(self):
        scores, records = _make_test_data()
        report = compute_accuracy(scores, records, k=5)
        formatted = format_accuracy_report(report)
        assert "Precision@5" in formatted
        assert "Recall@5" in formatted
        assert "Confusion Matrix" in formatted
        assert "Findings:" in formatted
