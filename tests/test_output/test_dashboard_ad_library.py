"""Tests for dashboard Panel 5: Ad Library (P5-04).

Validates filterable ad browser with expandable rationales and before/after pairs.
"""

from __future__ import annotations

from pathlib import Path

from output.dashboard_builder import generate_dashboard_html

SAMPLE_DATA = {
    "generated_at": "2026-03-15T12:00:00Z",
    "ledger_path": "data/ledger.jsonl",
    "pipeline_summary": {
        "total_ads_generated": 3, "total_ads_published": 2,
        "total_ads_discarded": 1, "publish_rate": 0.67,
        "total_batches": 1, "total_tokens": 5000,
        "total_cost_usd": 0.10, "avg_score": 7.5,
    },
    "iteration_cycles": [],
    "quality_trends": {"batch_scores": [], "ratchet_history": []},
    "dimension_deep_dive": {"dimension_trends": {}, "correlation_matrix": {}},
    "ad_library": [
        {
            "ad_id": "ad_001",
            "brief_id": "b001",
            "copy": {"headline": "Boost Your SAT Score", "primary_text": "Expert 1-on-1 tutoring that adapts to your learning style."},
            "scores": {"clarity": 8, "value_proposition": 7, "cta": 7, "brand_voice": 8, "emotional_resonance": 8},
            "aggregate_score": 7.6,
            "rationale": {"clarity": "Clear and direct messaging", "cta": "Strong call to action"},
            "status": "published",
            "cycle_count": 2,
            "image_path": None,
        },
        {
            "ad_id": "ad_002",
            "brief_id": "b001",
            "copy": {"headline": "SAT Prep Made Easy", "primary_text": "Join thousands of students who improved their scores."},
            "scores": {"clarity": 7, "value_proposition": 8, "cta": 8, "brand_voice": 7, "emotional_resonance": 7},
            "aggregate_score": 7.4,
            "rationale": {"clarity": "Good clarity", "value_proposition": "Strong VP"},
            "status": "published",
            "cycle_count": 1,
            "image_path": None,
        },
        {
            "ad_id": "ad_003",
            "brief_id": "b002",
            "copy": {"headline": "Test Prep", "primary_text": "We help with tests."},
            "scores": {"clarity": 5, "value_proposition": 4, "cta": 3, "brand_voice": 4, "emotional_resonance": 3},
            "aggregate_score": 3.8,
            "rationale": {"clarity": "Too vague", "cta": "No clear CTA"},
            "status": "discarded",
            "cycle_count": 1,
            "image_path": None,
        },
    ],
    "token_economics": {"by_stage": {}, "by_model": {}, "cost_per_published": 0, "marginal_analysis": {}},
    "system_health": {"spc": {"batch_averages": []}, "confidence_stats": {}, "compliance_stats": {}},
    "competitive_intel": {},
}


def test_all_ads_rendered(tmp_path: Path) -> None:
    """All ads from ad_library are rendered in Panel 5."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)
    content = Path(output_path).read_text()

    assert "ad_001" in content
    assert "ad_002" in content
    assert "ad_003" in content


def test_ad_cards_show_scores(tmp_path: Path) -> None:
    """Ad cards display aggregate scores."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)
    content = Path(output_path).read_text()

    assert "7.6" in content  # ad_001 score
    assert "7.4" in content  # ad_002 score
    assert "3.8" in content  # ad_003 score


def test_ad_cards_show_status_badges(tmp_path: Path) -> None:
    """Ad cards show published/discarded status badges."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)
    content = Path(output_path).read_text()

    assert "published" in content.lower()
    assert "discarded" in content.lower()


def test_ad_cards_show_copy_preview(tmp_path: Path) -> None:
    """Ad cards include copy preview text."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)
    content = Path(output_path).read_text()

    assert "Boost Your SAT Score" in content
    assert "Expert 1-on-1 tutoring" in content


def test_ad_cards_have_rationale(tmp_path: Path) -> None:
    """Ad cards include rationale text in expandable section."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)
    content = Path(output_path).read_text()

    assert "Clear and direct messaging" in content
    assert "Strong call to action" in content


def test_filter_controls_present(tmp_path: Path) -> None:
    """Filter bar has status and score controls."""
    output_path = str(tmp_path / "dashboard.html")
    generate_dashboard_html(SAMPLE_DATA, output_path)
    content = Path(output_path).read_text()

    # Filter controls should exist in the ad library panel
    assert "filter" in content.lower() or "Filter" in content
    assert "sort" in content.lower() or "Sort" in content
