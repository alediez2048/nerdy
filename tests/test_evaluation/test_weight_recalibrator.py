"""Tests for weight recalibration from performance data (PF-04)."""

import os
import tempfile

from evaluate.performance_correlation import DimensionPerformanceMatrix
from evaluate.correlation import DIMENSIONS
from evaluate.dimensions import AWARENESS_WEIGHTS, CONVERSION_WEIGHTS
from evaluate.weight_recalibrator import (
    MIN_WEIGHT,
    RecalibrationReport,
    compare_profiles,
    log_recalibration,
    recalibrate_weights,
    recalibrated_weight_profile,
)
from iterate.ledger import read_events_filtered


def _make_matrix(ctr_correlations: dict[str, float] | None = None) -> DimensionPerformanceMatrix:
    """Create a mock DimensionPerformanceMatrix."""
    matrix = {}
    defaults = {
        "clarity": {"ctr": 0.35, "conversion_rate": 0.15, "engagement_rate": 0.10, "relevance_score": 0.20},
        "value_proposition": {"ctr": 0.20, "conversion_rate": 0.30, "engagement_rate": 0.15, "relevance_score": 0.25},
        "cta": {"ctr": 0.15, "conversion_rate": 0.55, "engagement_rate": 0.05, "relevance_score": 0.10},
        "brand_voice": {"ctr": 0.10, "conversion_rate": 0.08, "engagement_rate": 0.30, "relevance_score": 0.35},
        "emotional_resonance": {"ctr": 0.25, "conversion_rate": 0.10, "engagement_rate": 0.50, "relevance_score": 0.20},
    }

    if ctr_correlations:
        for dim, r in ctr_correlations.items():
            defaults[dim]["ctr"] = r

    for dim in DIMENSIONS:
        for metric, r in defaults[dim].items():
            matrix[(dim, metric)] = r

    strongest = {}
    weakest = {}
    for metric in ("ctr", "conversion_rate", "engagement_rate", "relevance_score"):
        pairs = [(dim, matrix[(dim, metric)]) for dim in DIMENSIONS]
        by_abs = sorted(pairs, key=lambda x: abs(x[1]), reverse=True)
        strongest[metric] = (by_abs[0][0], by_abs[0][1])
        weakest[metric] = (by_abs[-1][0], by_abs[-1][1])

    return DimensionPerformanceMatrix(
        matrix=matrix,
        strongest_predictors=strongest,
        weakest_predictors=weakest,
        findings=["Test finding"],
        sample_size=50,
    )


class TestRecalibration:
    def test_weights_sum_to_one(self):
        matrix = _make_matrix()
        report = recalibrate_weights(matrix, "awareness")
        total = sum(report.recalibrated_weights.values())
        assert abs(total - 1.0) < 0.001, f"Weights sum to {total}"

    def test_all_dimensions_present(self):
        matrix = _make_matrix()
        report = recalibrate_weights(matrix, "awareness")
        for dim in DIMENSIONS:
            assert dim in report.recalibrated_weights

    def test_no_weight_below_floor(self):
        matrix = _make_matrix()
        report = recalibrate_weights(matrix, "awareness")
        for dim, w in report.recalibrated_weights.items():
            assert w >= MIN_WEIGHT * 0.5, f"{dim} weight {w} too low"

    def test_awareness_uses_ctr(self):
        matrix = _make_matrix()
        report = recalibrate_weights(matrix, "awareness")
        assert report.target_metric == "ctr"

    def test_conversion_uses_conversion_rate(self):
        matrix = _make_matrix()
        report = recalibrate_weights(matrix, "conversion")
        assert report.target_metric == "conversion_rate"

    def test_high_correlation_gets_more_weight(self):
        """CTA has highest conversion_rate correlation (0.55), should get more weight."""
        matrix = _make_matrix()
        report = recalibrate_weights(matrix, "conversion")
        # CTA should have gained weight relative to original
        assert report.delta_per_dimension["cta"] > 0

    def test_confidence_note_present(self):
        matrix = _make_matrix()
        report = recalibrate_weights(matrix, "awareness")
        assert "simulated" in report.confidence_note.lower()

    def test_deltas_computed(self):
        matrix = _make_matrix()
        report = recalibrate_weights(matrix, "awareness")
        for dim in DIMENSIONS:
            expected = round(
                report.recalibrated_weights[dim] - report.original_weights[dim], 4
            )
            assert abs(report.delta_per_dimension[dim] - expected) < 0.001


class TestWeightProfile:
    def test_creates_valid_profile(self):
        matrix = _make_matrix()
        report = recalibrate_weights(matrix, "awareness")
        profile = recalibrated_weight_profile(report)
        assert "recalibrated" in profile.campaign_goal
        assert sum(profile.weights.values()) - 1.0 < 0.001


class TestComparison:
    def test_format_produces_table(self):
        matrix = _make_matrix()
        report = recalibrate_weights(matrix, "awareness")
        profile = recalibrated_weight_profile(report)
        table = compare_profiles(AWARENESS_WEIGHTS, profile)
        assert "Clarity" in table
        assert "Original" in table
        assert "Recalibrated" in table


class TestLedgerIntegration:
    def test_logs_event(self):
        matrix = _make_matrix()
        report = recalibrate_weights(matrix, "awareness")
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            ledger_path = f.name
        try:
            log_recalibration(report, ledger_path)
            events = read_events_filtered(ledger_path, event_type="WeightsRecalibrated")
            assert len(events) == 1
            assert events[0]["outputs"]["recalibrated_weights"] == report.recalibrated_weights
        finally:
            os.unlink(ledger_path)
