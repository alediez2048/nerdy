# PB-01: Brand knowledge base — Nerdy supplementary integration tests
"""Validates brand_knowledge.json has all personas, messaging rules, competitor data, and offer positioning."""

import json
from pathlib import Path

import pytest

KB_PATH = Path("data/brand_knowledge.json")


@pytest.fixture()
def kb():
    with open(KB_PATH) as f:
        return json.load(f)


PERSONA_KEYS = [
    "athlete_recruit",
    "suburban_optimizer",
    "immigrant_navigator",
    "cultural_investor",
    "system_optimizer",
    "neurodivergent_advocate",
    "burned_returner",
]

PERSONA_REQUIRED_FIELDS = [
    "description",
    "psychology",
    "trigger",
    "funnel_position",
    "conversion_likelihood",
    "key_needs",
    "preferred_cta",
]


def test_all_seven_personas_present(kb):
    personas = kb.get("personas", {})
    for key in PERSONA_KEYS:
        assert key in personas, f"Missing persona: {key}"
    assert len(personas) == 7


def test_persona_required_fields(kb):
    personas = kb["personas"]
    for key in PERSONA_KEYS:
        persona = personas[key]
        for field in PERSONA_REQUIRED_FIELDS:
            assert field in persona, f"Persona {key} missing field: {field}"
            assert persona[field], f"Persona {key} has empty field: {field}"


def test_messaging_dos_contains_key_rules(kb):
    dos = kb.get("messaging_rules", {}).get("dos", [])
    dos_text = " ".join(d["rule"] for d in dos)
    assert "your child" in dos_text.lower()
    assert "sat tutoring" in dos_text.lower()
    assert "100" in dos_text  # 100pts/month
    assert "10x" in dos_text.lower() or "10X" in dos_text


def test_messaging_donts_contains_key_rules(kb):
    donts = kb.get("messaging_rules", {}).get("donts", [])
    donts_text = " ".join(d["rule"] for d in donts)
    assert "your student" in donts_text.lower()
    assert "sat prep" in donts_text.lower()
    assert "spots filling fast" in donts_text.lower() or "fake urgency" in donts_text.lower()
    assert "online tutoring" in donts_text.lower()


def test_competitor_pricing_present(kb):
    comp = kb.get("competitors_detailed", {})
    assert "group_courses" in comp
    assert "$199" in comp["group_courses"]["pricing"] or "$252" in comp["group_courses"]["pricing"]
    assert "self_study" in comp
    assert "local_tutors" in comp
    assert "varsity_tutors" in comp
    assert "$349" in comp["varsity_tutors"]["pricing"]


def test_offer_positioning_present(kb):
    offer = kb.get("offer", {})
    assert "model" in offer
    assert "membership" in offer["model"].lower()
    assert "recommended_plan" in offer
    assert offer["recommended_plan"]["price_per_month"] == 639
    assert "score_improvement" in offer
    assert "100" in offer["score_improvement"]
    assert "whats_included" in offer
    assert len(offer["whats_included"]) >= 8


def test_persona_specific_ctas_present(kb):
    persona_ctas = kb.get("ctas", {}).get("persona_specific", {})
    for key in PERSONA_KEYS:
        assert key in persona_ctas, f"Missing persona CTA for: {key}"
        assert len(persona_ctas[key]) > 10, f"CTA too short for: {key}"


def test_backward_compatibility(kb):
    """Existing keys that other modules depend on must still be present."""
    assert "brand" in kb
    assert "name" in kb["brand"]
    assert kb["brand"]["name"] == "Varsity Tutors"
    assert "audiences" in kb
    assert "parent" in kb["audiences"]
    assert "student" in kb["audiences"]
    assert "competitors" in kb
    assert "compliance" in kb
    assert "never_claim" in kb["compliance"]
    assert "always_include" in kb["compliance"]
    assert "ctas" in kb
    assert "awareness" in kb["ctas"]
    assert "conversion" in kb["ctas"]


def test_compliance_updated_with_nerdy_rules(kb):
    never = kb["compliance"]["never_claim"]
    never_text = " ".join(never).lower()
    assert "your student" in never_text
    assert "sat prep" in never_text
    assert "fake urgency" in never_text or "spots filling fast" in never_text
    assert "online tutoring" in never_text


def test_creative_brief_template_present(kb):
    briefs = kb.get("creative_briefs", {})
    assert "gap_report" in briefs
    gap = briefs["gap_report"]
    assert gap["persona"] == "system_optimizer"
    assert "input_output_table" in gap


def test_meta_ad_structure_present(kb):
    meta = kb.get("meta_ad_structure", {})
    assert "format" in meta
    assert "Hook" in meta["format"]
    assert "example" in meta
    assert "hook" in meta["example"]
    assert "body" in meta["example"]
    assert "cta" in meta["example"]
