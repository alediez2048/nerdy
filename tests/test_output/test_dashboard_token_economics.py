"""Tests for dashboard Panel 6: Token Economics (P5-05).

Validates cost attribution, marginal analysis, model routing,
and auto-cap recommendation sub-panels.
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
    "token_economics": {
        "by_stage": {
            "generation": 45000,
            "evaluation": 30000,
            "regeneration": 20000,
            "other": 5000,
        },
        "by_model": {
            "gemini-2.0-flash": 80000,
            "gemini-2.0-pro": 20000,
        },
        "cost_per_published": 2857.14,
        "marginal_analysis": {
            "gain_curve": {1: 1.2, 2: 0.5, 3: 0.15},
            "token_spend": {1: 1000, 2: 1000, 3: 1000},
            "dimension_breakdown": [
                {"dimension": "clarity", "cycle_1": 0.8, "cycle_2": 0.3, "cycle_3": 0.1},
                {"dimension": "cta", "cycle_1": 1.5, "cycle_2": 0.6, "cycle_3": 0.2},
            ],
            "recommendation": {
                "max_cycles": 2,
                "reason": "Cycle 3 avg gain < 0.2 — capping at 2",
                "savings_tokens": 5000,
            },
        },
    },
    "system_health": {"spc": {"batch_averages": []}, "confidence_stats": {}, "compliance_stats": {}},
    "competitive_intel": {},
}


def test_panel6_has_cost_attribution(tmp_path: Path) -> None:
    """Panel 6 renders cost attribution by stage."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)
    content = Path(output_path).read_text()

    assert "generation" in content.lower()
    assert "evaluation" in content.lower()
    assert "Cost Attribution" in content or "cost-attribution" in content.lower() or "by_stage" in content


def test_panel6_has_model_routing(tmp_path: Path) -> None:
    """Panel 6 shows model routing breakdown."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)
    content = Path(output_path).read_text()

    assert "gemini-2.0-flash" in content or "Flash" in content
    assert "gemini-2.0-pro" in content or "Pro" in content


def test_panel6_has_marginal_analysis(tmp_path: Path) -> None:
    """Panel 6 shows marginal analysis gain curve data."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)
    content = Path(output_path).read_text()

    assert "marginal" in content.lower() or "Gain Curve" in content or "gain" in content.lower()


def test_panel6_has_auto_cap_recommendation(tmp_path: Path) -> None:
    """Panel 6 shows auto-cap recommendation with reason."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)
    content = Path(output_path).read_text()

    assert "capping at 2" in content.lower() or "max_cycles" in content or "Recommended" in content


def test_panel6_has_all_subpanels(tmp_path: Path) -> None:
    """Panel 6 renders all sub-panel sections."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)
    content = Path(output_path).read_text()

    # Should have multiple sub-panels for token economics
    assert content.count("econ-sub") >= 3 or content.count("sub-panel") >= 3
