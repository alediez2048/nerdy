"""Tests for brand knowledge base schema and compliance (P0-04)."""

import json
from pathlib import Path



BRAND_KNOWLEDGE_PATH = Path(__file__).resolve().parents[2] / "data" / "brand_knowledge.json"

# Words/phrases that must not appear in any claim (compliance blacklist)
COMPLIANCE_BLACKLIST = [
    "guaranteed",
    "100%",
    "always works",
    "never fail",
    "worse",
    "bad",
    "terrible",
    "inferior",
]


def _load_brand_knowledge() -> dict:
    """Load and parse brand knowledge JSON."""
    with open(BRAND_KNOWLEDGE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _collect_all_claim_texts(data: dict, exclude_compliance: bool = True) -> list[str]:
    """Recursively collect all claim-like text from the knowledge base.
    Excludes compliance section (which describes forbidden phrases, not claims).
    """
    texts: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "compliance" and exclude_compliance:
                continue
            if key in ("source", "source_citation", "competitors_source") and isinstance(value, str):
                continue
            if key == "claim" and isinstance(value, str):
                texts.append(value)
            elif key == "point" and isinstance(value, str):
                texts.append(value)
            elif key == "driver" and isinstance(value, str):
                texts.append(value)
            elif key == "positioning" and isinstance(value, str):
                texts.append(value)
            elif key == "description" and isinstance(value, str):
                texts.append(value)
            elif key in ("awareness", "conversion") and isinstance(value, list):
                texts.extend(str(x) for x in value)
            elif key == "competitors" and isinstance(value, list):
                texts.extend(str(x) for x in value)
            else:
                texts.extend(_collect_all_claim_texts(value, exclude_compliance))
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict):
                texts.extend(_collect_all_claim_texts(item, exclude_compliance))
    return texts


def test_brand_knowledge_file_exists() -> None:
    """Brand knowledge file must exist."""
    assert BRAND_KNOWLEDGE_PATH.exists(), f"Missing {BRAND_KNOWLEDGE_PATH}"


def test_brand_knowledge_valid_json() -> None:
    """Brand knowledge must be valid JSON."""
    with open(BRAND_KNOWLEDGE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)


def test_brand_knowledge_required_sections() -> None:
    """Brand knowledge must have all required sections."""
    data = _load_brand_knowledge()
    required = ["brand", "products", "audiences", "proof_points", "competitors", "ctas", "compliance"]
    for section in required:
        assert section in data, f"Missing required section: {section}"


def test_brand_knowledge_brand_identity() -> None:
    """Brand section must have name, voice, positioning."""
    data = _load_brand_knowledge()
    brand = data["brand"]
    assert "name" in brand and brand["name"] == "Varsity Tutors"
    assert "voice" in brand and isinstance(brand["voice"], list)
    assert "positioning" in brand


def test_brand_knowledge_verified_claims_have_source() -> None:
    """Every verified claim in products must have a source field."""
    data = _load_brand_knowledge()
    products = data.get("products", {})
    for product_key, product_data in products.items():
        if isinstance(product_data, dict) and "verified_claims" in product_data:
            for claim in product_data["verified_claims"]:
                assert "source" in claim, f"Claim missing source: {claim}"
                assert claim["source"] in (
                    "assignment_spec",
                    "reference_ad",
                    "public_website",
                    "brand_context",
                    "supplementary",
                ), f"Invalid source: {claim['source']}"


def test_brand_knowledge_audiences_have_required_fields() -> None:
    """Audiences must have pain_points, emotional_drivers, tone_register."""
    data = _load_brand_knowledge()
    audiences = data["audiences"]
    for audience_key, audience_data in audiences.items():
        if isinstance(audience_data, dict):
            assert "pain_points" in audience_data or "tone_register" in audience_data
            assert "tone_register" in audience_data, f"Audience {audience_key} missing tone_register"


def test_brand_knowledge_no_compliance_blacklist_in_claims() -> None:
    """No claim or description may contain compliance blacklist words."""
    data = _load_brand_knowledge()
    texts = _collect_all_claim_texts(data)
    for text in texts:
        text_lower = text.lower()
        for forbidden in COMPLIANCE_BLACKLIST:
            assert forbidden not in text_lower, (
                f"Claim contains forbidden word '{forbidden}': {text[:80]}..."
            )


def test_brand_knowledge_competitors_list() -> None:
    """Competitors must be a non-empty list of known competitors."""
    data = _load_brand_knowledge()
    competitors = data["competitors"]
    assert isinstance(competitors, list)
    assert len(competitors) >= 4
    expected = {"Princeton Review", "Kaplan", "Khan Academy", "Chegg"}
    assert expected.issubset(set(competitors))


def test_brand_knowledge_ctas_by_funnel() -> None:
    """CTAs must have awareness and conversion arrays."""
    data = _load_brand_knowledge()
    ctas = data["ctas"]
    assert "awareness" in ctas and isinstance(ctas["awareness"], list)
    assert "conversion" in ctas and isinstance(ctas["conversion"], list)
    assert len(ctas["awareness"]) > 0
    assert len(ctas["conversion"]) > 0


def test_brand_knowledge_compliance_rules() -> None:
    """Compliance must have never_claim and always_include."""
    data = _load_brand_knowledge()
    compliance = data["compliance"]
    assert "never_claim" in compliance and isinstance(compliance["never_claim"], list)
    assert "always_include" in compliance and isinstance(compliance["always_include"], list)
    assert len(compliance["never_claim"]) > 0
    assert len(compliance["always_include"]) > 0
