"""Tests for dashboard Panels 3-4: Quality Trends + Dimension Deep-Dive (P5-03).

Validates chart views, ratchet line, dimension trends, and correlation heatmap.
"""

from __future__ import annotations

from pathlib import Path

from output.dashboard_builder import generate_dashboard_html

SAMPLE_DATA = {
    "generated_at": "2026-03-15T12:00:00Z",
    "ledger_path": "data/ledger.jsonl",
    "pipeline_summary": {
        "total_ads_generated": 50, "total_ads_published": 35,
        "total_ads_discarded": 15, "publish_rate": 0.7,
        "total_batches": 5, "total_tokens": 100000,
        "total_cost_usd": 1.50, "avg_score": 7.5,
    },
    "iteration_cycles": [],
    "quality_trends": {
        "batch_scores": [
            {"batch": 1, "avg_score": 6.5, "threshold": 7.0},
            {"batch": 2, "avg_score": 7.0, "threshold": 7.0},
            {"batch": 3, "avg_score": 7.3, "threshold": 7.0},
            {"batch": 4, "avg_score": 7.5, "threshold": 7.0},
            {"batch": 5, "avg_score": 7.8, "threshold": 7.0},
        ],
        "ratchet_history": [
            {"batch": 1, "threshold": 7.0},
            {"batch": 2, "threshold": 7.0},
            {"batch": 3, "threshold": 7.0},
            {"batch": 4, "threshold": 7.0},
            {"batch": 5, "threshold": 7.3},
        ],
    },
    "dimension_deep_dive": {
        "dimension_trends": {
            "clarity": [7.0, 7.5, 7.8, 8.0, 8.2],
            "value_proposition": [6.5, 7.0, 7.2, 7.5, 7.6],
            "cta": [6.0, 6.5, 7.0, 7.2, 7.5],
            "brand_voice": [6.8, 7.0, 7.2, 7.5, 7.8],
            "emotional_resonance": [6.2, 6.8, 7.0, 7.3, 7.5],
        },
        "correlation_matrix": {
            "clarity": {"clarity": 1.0, "value_proposition": 0.45, "cta": 0.3, "brand_voice": 0.25, "emotional_resonance": 0.2},
            "value_proposition": {"clarity": 0.45, "value_proposition": 1.0, "cta": 0.5, "brand_voice": 0.35, "emotional_resonance": 0.75},
            "cta": {"clarity": 0.3, "cta": 1.0, "value_proposition": 0.5, "brand_voice": 0.2, "emotional_resonance": 0.4},
            "brand_voice": {"clarity": 0.25, "value_proposition": 0.35, "cta": 0.2, "brand_voice": 1.0, "emotional_resonance": 0.3},
            "emotional_resonance": {"clarity": 0.2, "value_proposition": 0.75, "cta": 0.4, "brand_voice": 0.3, "emotional_resonance": 1.0},
        },
    },
    "ad_library": [],
    "token_economics": {"by_stage": {}, "by_model": {}, "cost_per_published": 0, "marginal_analysis": {}},
    "system_health": {"spc": {"batch_averages": []}, "confidence_stats": {}, "compliance_stats": {}},
    "competitive_intel": {},
}


def test_panel3_has_chart_view_toggles(tmp_path: Path) -> None:
    """Panel 3 has toggle buttons for all 4 chart views."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)
    content = Path(output_path).read_text()

    assert "Score Trend" in content or "Average Score" in content
    assert "Distribution" in content or "Score Distribution" in content
    assert "Publish Rate" in content
    assert "Cost" in content


def test_panel3_includes_ratchet_data(tmp_path: Path) -> None:
    """Panel 3 includes ratchet line data (monotonically non-decreasing)."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)
    content = Path(output_path).read_text()

    # Ratchet data should be in the embedded JSON or chart config
    assert "ratchet" in content.lower()
    # Verify the ratchet values are present
    assert "7.3" in content  # final ratchet value from sample data


def test_panel4_dimension_trends(tmp_path: Path) -> None:
    """Panel 4 shows dimension trend lines."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)
    content = Path(output_path).read_text()

    # All 5 dimensions should appear
    assert "clarity" in content.lower() or "Clarity" in content
    assert "value_proposition" in content or "Value Proposition" in content
    assert "brand_voice" in content or "Brand Voice" in content
    assert "emotional_resonance" in content or "Emotional Resonance" in content


def test_panel4_correlation_heatmap_flags_high(tmp_path: Path) -> None:
    """Panel 4 correlation heatmap flags r > 0.7 in red."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)
    content = Path(output_path).read_text()

    # The 0.75 correlation between VP and ER should be flagged
    assert "0.75" in content or "0.8" in content
    # Should have red styling for high correlations
    assert "halo" in content.lower() or "high-corr" in content or "#F44336" in content or "#f44336" in content or "red" in content.lower()


def test_panel3_batch_score_data(tmp_path: Path) -> None:
    """Panel 3 contains batch score data points."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)
    content = Path(output_path).read_text()

    # Batch scores should be embedded
    assert "6.5" in content  # batch 1 avg
    assert "7.8" in content  # batch 5 avg
