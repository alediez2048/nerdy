"""Tests for evaluator-performance correlation analysis (PF-03)."""

from evaluate.performance_correlation import (
    PERFORMANCE_METRICS,
    DimensionPerformanceMatrix,
    compute_dimension_performance_matrix,
    format_performance_matrix,
)
from evaluate.correlation import DIMENSIONS
from evaluate.performance_schema import MetaPerformanceRecord


def _make_test_data(n: int = 30):
    """Create correlated eval scores + performance records for testing."""
    import random
    rng = random.Random(42)

    eval_scores = []
    perf_records = []

    for i in range(n):
        ad_id = f"ad_{i:03d}"
        # Base quality drives both scores and performance
        base = rng.uniform(3, 9)
        scores = {
            "clarity": max(1, min(10, base + rng.gauss(0, 0.5))),
            "value_proposition": max(1, min(10, base + rng.gauss(0, 0.5))),
            "cta": max(1, min(10, base + rng.gauss(0, 0.8))),
            "brand_voice": max(1, min(10, base + rng.gauss(0, 0.5))),
            "emotional_resonance": max(1, min(10, base + rng.gauss(0, 0.7))),
        }
        eval_scores.append({"ad_id": ad_id, "scores": scores})

        # Performance loosely correlated with scores + noise
        ctr = max(0.001, 0.01 + (base - 5) * 0.003 + rng.gauss(0, 0.005))
        clicks = max(1, int(10000 * ctr))
        conversions = max(0, int(clicks * (0.05 + (scores["cta"] - 5) * 0.01 + rng.gauss(0, 0.02))))
        engagement = max(0.005, 0.03 + (scores["emotional_resonance"] - 5) * 0.005 + rng.gauss(0, 0.008))

        perf_records.append(MetaPerformanceRecord(
            ad_id=ad_id,
            campaign_id="camp_test",
            impressions=10000,
            clicks=clicks,
            ctr=round(ctr, 6),
            conversions=conversions,
            cpa=round(50.0 / conversions, 2) if conversions > 0 else None,
            spend=50.0,
            engagement_rate=round(engagement, 4),
            relevance_score=round(max(1, min(10, base + rng.gauss(0, 1))), 1),
            date_range_start="2026-03-01",
            date_range_end="2026-03-07",
            placement="feed",
            audience_segment="parents",
        ))

    return eval_scores, perf_records


class TestCorrelationMatrix:
    def test_produces_20_values(self):
        scores, records = _make_test_data(30)
        result = compute_dimension_performance_matrix(scores, records)
        assert len(result.matrix) == 20  # 5 dimensions x 4 metrics

    def test_all_dimensions_present(self):
        scores, records = _make_test_data(30)
        result = compute_dimension_performance_matrix(scores, records)
        for dim in DIMENSIONS:
            for metric in PERFORMANCE_METRICS:
                assert (dim, metric) in result.matrix

    def test_r_values_in_valid_range(self):
        scores, records = _make_test_data(50)
        result = compute_dimension_performance_matrix(scores, records)
        for key, r in result.matrix.items():
            assert -1.0 <= r <= 1.0, f"{key}: r={r} out of range"

    def test_strongest_predictor_per_metric(self):
        scores, records = _make_test_data(50)
        result = compute_dimension_performance_matrix(scores, records)
        for metric in PERFORMANCE_METRICS:
            assert metric in result.strongest_predictors
            dim, r = result.strongest_predictors[metric]
            assert dim in DIMENSIONS

    def test_weakest_predictor_per_metric(self):
        scores, records = _make_test_data(50)
        result = compute_dimension_performance_matrix(scores, records)
        for metric in PERFORMANCE_METRICS:
            assert metric in result.weakest_predictors

    def test_findings_generated(self):
        scores, records = _make_test_data(50)
        result = compute_dimension_performance_matrix(scores, records)
        assert len(result.findings) >= 4  # At least one per metric

    def test_sample_size_correct(self):
        scores, records = _make_test_data(25)
        result = compute_dimension_performance_matrix(scores, records)
        assert result.sample_size == 25

    def test_insufficient_data(self):
        result = compute_dimension_performance_matrix([], [])
        assert result.matrix == {}
        assert "Insufficient data" in result.findings[0]

    def test_partial_overlap(self):
        """Only ads present in both datasets should be used."""
        scores = [{"ad_id": "ad_001", "scores": {"clarity": 8, "value_proposition": 7, "cta": 6, "brand_voice": 7, "emotional_resonance": 8}},
                  {"ad_id": "ad_002", "scores": {"clarity": 5, "value_proposition": 5, "cta": 5, "brand_voice": 5, "emotional_resonance": 5}},
                  {"ad_id": "ad_003", "scores": {"clarity": 3, "value_proposition": 3, "cta": 3, "brand_voice": 3, "emotional_resonance": 3}}]
        records = [MetaPerformanceRecord(
            ad_id="ad_001", campaign_id="c", impressions=10000, clicks=200, ctr=0.02,
            conversions=5, cpa=10.0, spend=50.0, engagement_rate=0.04, relevance_score=7.0,
            date_range_start="2026-03-01", date_range_end="2026-03-07", placement="feed", audience_segment="parents"),
            MetaPerformanceRecord(
            ad_id="ad_002", campaign_id="c", impressions=10000, clicks=100, ctr=0.01,
            conversions=2, cpa=25.0, spend=50.0, engagement_rate=0.02, relevance_score=5.0,
            date_range_start="2026-03-01", date_range_end="2026-03-07", placement="feed", audience_segment="parents")]
        # ad_003 has scores but no performance, ad_001 and ad_002 overlap
        result = compute_dimension_performance_matrix(scores, records)
        assert result.sample_size == 2


class TestFormatting:
    def test_format_produces_table(self):
        scores, records = _make_test_data(30)
        result = compute_dimension_performance_matrix(scores, records)
        formatted = format_performance_matrix(result)
        assert "CTR" in formatted
        assert "CONV" in formatted
        assert "Findings:" in formatted

    def test_format_empty_matrix(self):
        result = DimensionPerformanceMatrix(
            matrix={}, strongest_predictors={}, weakest_predictors={},
            findings=["No data"], sample_size=0)
        formatted = format_performance_matrix(result)
        assert "No correlation data" in formatted
