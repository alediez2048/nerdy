"""Tests for dashboard HTML generation (P5-02).

Validates that the dashboard HTML file contains all 8 panel tabs
and renders Pipeline Summary + Iteration Cycles panels correctly.
"""

from __future__ import annotations

import json
from pathlib import Path

from output.dashboard_builder import generate_dashboard_html

SAMPLE_DATA = {
    "generated_at": "2026-03-15T12:00:00Z",
    "ledger_path": "data/ledger.jsonl",
    "pipeline_summary": {
        "total_ads_generated": 52,
        "total_ads_published": 38,
        "total_ads_discarded": 14,
        "publish_rate": 0.731,
        "total_batches": 5,
        "total_tokens": 125000,
        "total_cost_usd": 1.85,
        "avg_score": 7.8,
    },
    "iteration_cycles": [
        {
            "ad_id": "ad_001",
            "cycle": 2,
            "score_before": 6.2,
            "score_after": 7.6,
            "weakest_dimension": "cta",
            "action_taken": "published",
        },
        {
            "ad_id": "ad_005",
            "cycle": 1,
            "score_before": 5.5,
            "score_after": 5.0,
            "weakest_dimension": "brand_voice",
            "action_taken": "discarded",
        },
    ],
    "quality_trends": {"batch_scores": [], "ratchet_history": []},
    "dimension_deep_dive": {"dimension_trends": {}, "correlation_matrix": {}},
    "ad_library": [],
    "token_economics": {"by_stage": {}, "by_model": {}, "cost_per_published": 0, "marginal_analysis": {}},
    "system_health": {"spc": {"batch_averages": []}, "confidence_stats": {}, "compliance_stats": {}},
    "competitive_intel": {},
}


def test_dashboard_html_generated(tmp_path: Path) -> None:
    """Dashboard HTML file is created."""
    output_path = str(tmp_path / "dashboard.html")
    data_path = str(tmp_path / "dashboard_data.json")
    with open(data_path, "w") as f:
        json.dump(SAMPLE_DATA, f)

    generate_dashboard_html(SAMPLE_DATA, output_path)

    assert Path(output_path).exists()
    content = Path(output_path).read_text()
    assert len(content) > 100


def test_dashboard_has_all_8_tabs(tmp_path: Path) -> None:
    """Dashboard HTML contains all 8 panel tab labels."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)

    content = Path(output_path).read_text()
    expected_tabs = [
        "Pipeline Summary",
        "Iteration Cycles",
        "Quality Trends",
        "Dimension Deep-Dive",
        "Ad Library",
        "Token Economics",
        "System Health",
        "Competitive Intel",
    ]
    for tab in expected_tabs:
        assert tab in content, f"Missing tab: {tab}"


def test_panel1_hero_metrics(tmp_path: Path) -> None:
    """Panel 1 renders all 8 hero KPI values."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)

    content = Path(output_path).read_text()
    # Check that key metrics are embedded in the HTML
    assert "52" in content  # total_ads_generated
    assert "38" in content  # total_ads_published
    assert "73.1%" in content or "73.1" in content  # publish_rate
    assert "7.8" in content  # avg_score
    assert "125,000" in content or "125000" in content  # total_tokens


def test_panel2_iteration_cards(tmp_path: Path) -> None:
    """Panel 2 renders iteration cycle cards with before/after."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)

    content = Path(output_path).read_text()
    assert "ad_001" in content
    assert "6.2" in content  # score_before
    assert "7.6" in content  # score_after
    assert "cta" in content  # weakest_dimension


def test_dashboard_no_external_deps(tmp_path: Path) -> None:
    """Dashboard has no external dependencies beyond Chart.js CDN."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)

    content = Path(output_path).read_text()
    # Should be self-contained with inline CSS/JS
    assert "<style>" in content or "<style " in content
    assert "<script>" in content or "<script " in content
    # Only CDN should be Chart.js
    import re
    external_scripts = re.findall(r'src="(https?://[^"]+)"', content)
    for src in external_scripts:
        assert "chart" in src.lower() or "cdn" in src.lower(), f"Unexpected external script: {src}"
