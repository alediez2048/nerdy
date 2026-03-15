"""Tests for performance feedback dashboard panel (PF-07)."""

import os
import tempfile

from output.performance_dashboard import (
    PerformancePanelData,
    format_panel_html,
    get_performance_panel_data,
)
from iterate.ledger import log_event


def _seed_ledger_with_events(ledger_path: str):
    """Populate a test ledger with PF events."""
    # PerformanceIngested events
    for i in range(5):
        log_event(ledger_path, {
            "event_type": "PerformanceIngested",
            "ad_id": f"ad_{i:03d}",
            "brief_id": "camp_001",
            "cycle_number": 0,
            "action": "ingest_performance",
            "tokens_consumed": 0,
            "model_used": "none",
            "seed": 0,
            "outputs": {"ctr": 0.02 + i * 0.005},
        })

    # WeightsRecalibrated event
    log_event(ledger_path, {
        "event_type": "WeightsRecalibrated",
        "ad_id": "system",
        "brief_id": "system",
        "cycle_number": 0,
        "action": "recalibrate_weights",
        "tokens_consumed": 0,
        "model_used": "none",
        "seed": 0,
        "inputs": {
            "campaign_goal": "awareness",
            "target_metric": "ctr",
            "original_weights": {
                "clarity": 0.25, "value_proposition": 0.20,
                "cta": 0.10, "brand_voice": 0.20, "emotional_resonance": 0.25,
            },
            "correlation_basis": {
                "clarity": 0.35, "value_proposition": 0.20,
                "cta": 0.15, "brand_voice": 0.10, "emotional_resonance": 0.25,
            },
        },
        "outputs": {
            "recalibrated_weights": {
                "clarity": 0.28, "value_proposition": 0.18,
                "cta": 0.12, "brand_voice": 0.14, "emotional_resonance": 0.28,
            },
            "delta_per_dimension": {
                "clarity": 0.03, "value_proposition": -0.02,
                "cta": 0.02, "brand_voice": -0.06, "emotional_resonance": 0.03,
            },
        },
    })


class TestPanelDataAssembly:
    def test_reads_from_ledger(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            ledger_path = f.name
        try:
            _seed_ledger_with_events(ledger_path)
            data = get_performance_panel_data(ledger_path)
            assert data.sample_size == 5
            assert data.loop_status == "simulated"
        finally:
            os.unlink(ledger_path)

    def test_weight_comparison_populated(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            ledger_path = f.name
        try:
            _seed_ledger_with_events(ledger_path)
            data = get_performance_panel_data(ledger_path)
            assert "original" in data.weight_comparison
            assert "recalibrated" in data.weight_comparison
            assert "delta" in data.weight_comparison
        finally:
            os.unlink(ledger_path)

    def test_top_predictors_populated(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            ledger_path = f.name
        try:
            _seed_ledger_with_events(ledger_path)
            data = get_performance_panel_data(ledger_path)
            assert len(data.top_predictors) > 0
        finally:
            os.unlink(ledger_path)

    def test_findings_generated(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            ledger_path = f.name
        try:
            _seed_ledger_with_events(ledger_path)
            data = get_performance_panel_data(ledger_path)
            assert len(data.key_findings) >= 2
        finally:
            os.unlink(ledger_path)

    def test_empty_ledger(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            ledger_path = f.name
        try:
            data = get_performance_panel_data(ledger_path)
            assert data.sample_size == 0
            assert data.loop_status == "simulated"
            assert len(data.key_findings) >= 1
        finally:
            os.unlink(ledger_path)


class TestHTMLGeneration:
    def test_html_contains_required_sections(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            ledger_path = f.name
        try:
            _seed_ledger_with_events(ledger_path)
            data = get_performance_panel_data(ledger_path)
            html = format_panel_html(data)
            assert "Evaluator vs. Reality" in html
            assert "Weight Recalibration" in html
            assert "Correlation" in html
            assert "Key Findings" in html
            assert "Simulated Data" in html
        finally:
            os.unlink(ledger_path)

    def test_html_includes_disclaimer(self):
        data = PerformancePanelData(
            correlation_heatmap={}, weight_comparison={},
            accuracy_summary={}, top_predictors=[],
            key_findings=["Test finding"], loop_status="simulated", sample_size=0,
        )
        html = format_panel_html(data)
        assert "Simulated" in html
        assert "30%" in html
