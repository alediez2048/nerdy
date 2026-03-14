"""Tests for reference ad collection schema and labels (P0-05)."""

import json
from pathlib import Path

REFERENCE_ADS_PATH = Path(__file__).resolve().parents[2] / "data" / "reference_ads.json"
PATTERN_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "pattern_database.json"


def _load_reference_ads() -> dict:
    """Load reference ads JSON."""
    with open(REFERENCE_ADS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _load_pattern_db() -> dict:
    """Load pattern database JSON."""
    with open(PATTERN_DB_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_reference_ads_file_exists() -> None:
    """Reference ads file must exist."""
    assert REFERENCE_ADS_PATH.exists()


def test_reference_ads_valid_json() -> None:
    """Reference ads must be valid JSON."""
    data = _load_reference_ads()
    assert "ads" in data
    assert isinstance(data["ads"], list)


def test_reference_ads_count() -> None:
    """Must have 40-60 reference ads."""
    data = _load_reference_ads()
    ads = data["ads"]
    assert 40 <= len(ads) <= 60, f"Expected 40-60 ads, got {len(ads)}"


def test_reference_ads_required_fields() -> None:
    """Each ad must have primary_text, headline, description, cta_button, source, brand, audience_guess."""
    data = _load_reference_ads()
    required = ["ad_id", "primary_text", "headline", "description", "cta_button", "source", "brand", "audience_guess"]
    for ad in data["ads"]:
        for field in required:
            assert field in ad, f"Ad {ad.get('ad_id', '?')} missing field: {field}"


def test_reference_ads_quality_labels() -> None:
    """Must have at least 5 excellent and 5 poor labeled ads."""
    data = _load_reference_ads()
    excellent = [a for a in data["ads"] if a.get("quality_label") == "excellent"]
    poor = [a for a in data["ads"] if a.get("quality_label") == "poor"]
    assert len(excellent) >= 5, f"Expected ≥5 excellent, got {len(excellent)}"
    assert len(poor) >= 5, f"Expected ≥5 poor, got {len(poor)}"


def test_reference_ads_labeled_have_scores() -> None:
    """Labeled ads must have human_scores and ai_rationales."""
    data = _load_reference_ads()
    labeled = [a for a in data["ads"] if a.get("quality_label") in ("excellent", "poor")]
    for ad in labeled:
        assert "human_scores" in ad
        assert "ai_rationales" in ad
        scores = ad["human_scores"]
        dims = ["clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance"]
        for dim in dims:
            assert dim in scores
            assert 1 <= scores[dim] <= 10


def test_reference_ads_brand_mix() -> None:
    """Must have Varsity Tutors and competitor ads."""
    data = _load_reference_ads()
    brands = {a["brand"] for a in data["ads"]}
    assert "Varsity Tutors" in brands
    assert len(brands) >= 2


def test_pattern_database_exists() -> None:
    """Pattern database file must exist."""
    assert PATTERN_DB_PATH.exists()


def test_pattern_database_valid_json() -> None:
    """Pattern database must be valid JSON with patterns array."""
    data = _load_pattern_db()
    assert "patterns" in data
    assert isinstance(data["patterns"], list)


def test_pattern_database_count() -> None:
    """Must have 10-15 pattern records."""
    data = _load_pattern_db()
    patterns = data["patterns"]
    assert 10 <= len(patterns) <= 15, f"Expected 10-15 patterns, got {len(patterns)}"


def test_pattern_database_required_fields() -> None:
    """Each pattern must have hook_type, body_pattern, cta_style, tone_register, audience."""
    data = _load_pattern_db()
    required = ["pattern_id", "ad_id", "hook_type", "body_pattern", "cta_style", "tone_register", "audience"]
    for pat in data["patterns"]:
        for field in required:
            assert field in pat, f"Pattern {pat.get('pattern_id', '?')} missing field: {field}"


def test_pattern_database_hook_types() -> None:
    """Hook types must be from known set (question, stat, story, fear, etc.)."""
    data = _load_pattern_db()
    valid_hooks = {"question", "stat", "story", "fear", "aspiration", "differentiation", "direct-address", "pain_point"}
    for pat in data["patterns"]:
        assert pat["hook_type"] in valid_hooks, f"Invalid hook_type: {pat['hook_type']}"
