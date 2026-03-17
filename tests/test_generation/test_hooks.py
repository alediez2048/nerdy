# PB-02: Hook library tests
"""Tests for hook loading, persona filtering, seed diversity, and data integrity."""

import json
from pathlib import Path

from generate.hooks import (
    get_all_categories,
    get_all_personas,
    get_hooks_for_category,
    get_hooks_for_persona,
    load_hooks,
)

HOOKS_PATH = Path("data/hooks_library.json")
BRAND_KB_PATH = Path("data/brand_knowledge.json")

REQUIRED_FIELDS = ["hook_id", "persona", "category", "hook_text", "psychology", "cta_text", "cta_style", "funnel_position"]


def test_hooks_count_at_least_80():
    hooks = load_hooks()
    assert len(hooks) >= 80, f"Expected 80+ hooks, got {len(hooks)}"


def test_hook_required_fields():
    hooks = load_hooks()
    for h in hooks:
        for field in REQUIRED_FIELDS:
            assert field in h, f"Hook {h.get('hook_id', '?')} missing field: {field}"
            assert h[field], f"Hook {h.get('hook_id', '?')} has empty field: {field}"


def test_no_duplicate_hook_ids():
    hooks = load_hooks()
    ids = [h["hook_id"] for h in hooks]
    assert len(ids) == len(set(ids)), f"Duplicate hook_ids found: {len(ids) - len(set(ids))} duplicates"


def test_persona_filtering_returns_correct_persona():
    hooks = get_hooks_for_persona("athlete_recruit", n=10)
    assert len(hooks) >= 3, "Athlete persona should have at least 3 hooks"
    for h in hooks:
        assert h["persona"] == "athlete_recruit" or h["category"] == "athlete"


def test_seed_determinism():
    """Same seed should produce same result."""
    r1 = get_hooks_for_persona("suburban_optimizer", n=3, seed=42)
    r2 = get_hooks_for_persona("suburban_optimizer", n=3, seed=42)
    assert [h["hook_id"] for h in r1] == [h["hook_id"] for h in r2]


def test_seed_diversity():
    """Different seeds should produce different orderings."""
    r1 = get_hooks_for_persona("suburban_optimizer", n=5, seed=1)
    r2 = get_hooks_for_persona("suburban_optimizer", n=5, seed=999)
    ids1 = [h["hook_id"] for h in r1]
    ids2 = [h["hook_id"] for h in r2]
    # Same hooks but different order (or different subset)
    assert ids1 != ids2, "Different seeds should produce different orderings"


def test_all_brand_kb_personas_have_hooks():
    """Every persona in brand_knowledge.json should have at least 3 hooks."""
    with open(BRAND_KB_PATH) as f:
        kb = json.load(f)
    persona_keys = list(kb.get("personas", {}).keys())
    assert len(persona_keys) == 7

    for persona in persona_keys:
        hooks = get_hooks_for_persona(persona, n=10)
        assert len(hooks) >= 3, f"Persona {persona} has only {len(hooks)} hooks, need at least 3"


def test_category_filtering():
    hooks = get_hooks_for_category("scholarship", n=10)
    assert len(hooks) >= 3
    for h in hooks:
        assert h["category"] == "scholarship"


def test_get_all_personas_returns_known_personas():
    personas = get_all_personas()
    expected = {"athlete_recruit", "suburban_optimizer", "immigrant_navigator",
                "cultural_investor", "system_optimizer", "neurodivergent_advocate", "burned_returner"}
    assert expected.issubset(set(personas))


def test_get_all_categories():
    categories = get_all_categories()
    assert len(categories) >= 10, f"Expected 10+ categories, got {len(categories)}"
    assert "athlete" in categories
    assert "scholarship" in categories
    assert "test_anxiety" in categories
    assert "burned_returner" in categories
