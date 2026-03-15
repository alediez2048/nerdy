"""Tests for dashboard Panels 7-8: System Health + Competitive Intel (P5-06).

Validates SPC control charts, confidence routing, compliance stats,
and competitive intelligence panels.
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
    "quality_trends": {"batch_scores": [], "ratchet_history": []},
    "dimension_deep_dive": {"dimension_trends": {}, "correlation_matrix": {}},
    "ad_library": [],
    "token_economics": {"by_stage": {}, "by_model": {}, "cost_per_published": 0, "marginal_analysis": {}},
    "system_health": {
        "spc": {
            "batch_averages": [7.0, 7.2, 7.1, 7.4, 7.3],
            "ucl": 7.8,
            "lcl": 6.6,
            "mean": 7.2,
            "breach_indices": [],
        },
        "confidence_stats": {
            "autonomous_count": 40,
            "flagged_count": 8,
            "human_required_count": 2,
            "brand_safety_count": 0,
            "total": 50,
            "autonomous_pct": 80.0,
            "flagged_pct": 16.0,
            "human_required_pct": 4.0,
        },
        "compliance_stats": {
            "total_checked": 50,
            "passed": 35,
            "failed": 15,
            "pass_rate": 0.7,
        },
    },
    "competitive_intel": {
        "hook_distribution": {"question": 30, "statistic": 25, "narrative": 20, "social_proof": 15, "curiosity": 10},
        "strategy_radar": {"CompetitorA": {"question": 40, "statistic": 30}},
        "gap_analysis": [{"hook_type": "challenge", "coverage_pct": 5, "opportunity": "Low usage"}],
        "temporal_trends": [{"hook_type": "question", "direction": "increasing", "change_pct": 12}],
    },
}


def test_panel7_spc_chart_data(tmp_path: Path) -> None:
    """Panel 7 SPC chart includes UCL/LCL data."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)
    content = Path(output_path).read_text()

    assert "UCL" in content or "ucl" in content
    assert "LCL" in content or "lcl" in content
    assert "7.8" in content  # UCL value
    assert "6.6" in content  # LCL value


def test_panel7_confidence_stats(tmp_path: Path) -> None:
    """Panel 7 renders confidence routing percentages."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)
    content = Path(output_path).read_text()

    assert "80" in content  # autonomous_pct
    assert "autonomous" in content.lower()


def test_panel7_compliance_stats(tmp_path: Path) -> None:
    """Panel 7 shows compliance pass/fail stats."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)
    content = Path(output_path).read_text()

    assert "compliance" in content.lower() or "Compliance" in content
    assert "35" in content  # passed count


def test_panel8_competitor_patterns(tmp_path: Path) -> None:
    """Panel 8 renders competitor pattern data."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)
    content = Path(output_path).read_text()

    assert "CompetitorA" in content or "competitor" in content.lower()
    assert "question" in content.lower()


def test_panel8_strategy_shifts(tmp_path: Path) -> None:
    """Panel 8 shows strategy shift alerts or no-shifts message."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)
    content = Path(output_path).read_text()

    # Should show gap analysis or trending hooks
    assert "challenge" in content.lower() or "gap" in content.lower() or "trend" in content.lower()
