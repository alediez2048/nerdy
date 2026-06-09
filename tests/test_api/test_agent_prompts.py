# PJ-06: Phase-aware onboarding prompt tests
"""Content-level assertions on the prompts the loop sends to Gemini.

We don't try to grade prompt quality from a test — we only verify that
the right phase block, industry hint, profile snapshot, and tool
whitelist hint appear in the composed string. The behavioral test at
the bottom ("two industries produce different prompts") catches the
worst regression: the industry hint block silently disappearing.
"""
from __future__ import annotations

import pytest

from app.api.agent.prompts import (
    INDUSTRY_FALLBACK,
    INDUSTRY_HINTS,
    build_onboarding_prompt,
    build_post_session_prompt,
    build_pre_session_prep_prompt,
    build_prompt_for,
    build_refine_prompt,
)
from app.models.brand_profile import BrandProfile


def _profile(**overrides) -> BrandProfile:
    """Build a transient BrandProfile (not persisted) for prompt rendering."""
    row = BrandProfile(user_id=overrides.pop("user_id", "alice"))
    row.onboarding_phase = overrides.pop("onboarding_phase", "identify")
    for k, v in overrides.items():
        setattr(row, k, v)
    return row


# ---------------------------------------------------------------------------
# Phase block presence
# ---------------------------------------------------------------------------


def test_identify_phase_prompt_mentions_business_name():
    p = _profile(onboarding_phase="identify")
    out = build_onboarding_prompt(p, "identify")
    assert "Identify" in out
    assert "business name" in out.lower()
    assert "industry" in out.lower()


def test_core_phase_prompt_mentions_value_props_min():
    p = _profile(onboarding_phase="core")
    out = build_onboarding_prompt(p, "core")
    assert "Core" in out
    # The ≥ 2 minimum should be mentioned for both list fields.
    assert "value_props" in out
    assert ">=2" in out or "≥ 2" in out or "at least 2" in out


def test_assets_phase_mentions_skip_and_ingest_asset():
    p = _profile(onboarding_phase="assets")
    out = build_onboarding_prompt(p, "assets")
    assert "logo" in out.lower()
    assert "ingest_asset" in out
    assert "skip" in out.lower() or "no assets yet" in out.lower()


def test_good_enough_phase_mentions_mark_good_enough_call():
    p = _profile(onboarding_phase="good_enough")
    out = build_onboarding_prompt(p, "good_enough")
    assert "mark_good_enough" in out
    assert "finish_touchpoint" in out


# ---------------------------------------------------------------------------
# Industry hints (Phase 3 only)
# ---------------------------------------------------------------------------


def test_extras_phase_includes_tutoring_hints():
    p = _profile(onboarding_phase="extras", industry="tutoring")
    out = build_onboarding_prompt(p, "extras")
    assert "tutoring" in out.lower()
    assert "subjects_taught" in out
    assert "grade_levels" in out


def test_extras_phase_includes_restaurant_hints():
    p = _profile(onboarding_phase="extras", industry="restaurant")
    out = build_onboarding_prompt(p, "extras")
    assert "cuisine_style" in out
    assert "signature_dishes" in out


def test_extras_phase_unknown_industry_uses_fallback():
    p = _profile(onboarding_phase="extras", industry="circus")
    out = build_onboarding_prompt(p, "extras")
    # The fallback's first marker line should appear.
    assert "generic" in out.lower()
    # And a known industry hint should NOT.
    assert "subjects_taught" not in out


def test_extras_phase_null_industry_uses_fallback():
    p = _profile(onboarding_phase="extras", industry=None)
    out = build_onboarding_prompt(p, "extras")
    assert "generic" in out.lower()


@pytest.mark.parametrize("industry", list(INDUSTRY_HINTS.keys()))
def test_every_industry_hint_renders(industry: str):
    """Sanity: every known industry's hint block actually appears when
    that's the profile's industry."""
    p = _profile(onboarding_phase="extras", industry=industry)
    out = build_onboarding_prompt(p, "extras")
    assert INDUSTRY_HINTS[industry][:80] in out  # first line of the block


# ---------------------------------------------------------------------------
# Snapshot + whitelist hint
# ---------------------------------------------------------------------------


def test_profile_snapshot_includes_filled_fields():
    p = _profile(
        onboarding_phase="core",
        business_name="Acme Tutors",
        audience="parents",
    )
    out = build_onboarding_prompt(p, "core")
    assert "Acme Tutors" in out
    assert "parents" in out


def test_profile_snapshot_includes_extras_keys():
    p = _profile(onboarding_phase="extras", industry="tutoring")
    p.extras = {
        "subjects_taught": {"value": ["SAT"], "confidence": 0.8, "rationale": "."},
    }
    out = build_onboarding_prompt(p, "extras")
    assert "subjects_taught" in out


def test_whitelist_hint_omits_unavailable_tools():
    p = _profile(onboarding_phase="identify")
    out = build_onboarding_prompt(p, "identify")
    # mark_good_enough only appears in the good_enough phase.
    # The phase block itself doesn't mention it; nor should the
    # "Tools available right now" section in identify phase.
    # We check the whitelist hint specifically (anchored on the heading).
    tail = out.split("### Tools available right now", 1)[1]
    assert "mark_good_enough" not in tail


def test_whitelist_hint_includes_ingest_asset_in_assets_phase():
    p = _profile(onboarding_phase="assets")
    out = build_onboarding_prompt(p, "assets")
    tail = out.split("### Tools available right now", 1)[1]
    assert "ingest_asset" in tail


# ---------------------------------------------------------------------------
# Behavioral: different industries produce different Phase 3 prompts
# ---------------------------------------------------------------------------


def test_two_industries_produce_different_extras_prompts():
    tutoring = build_onboarding_prompt(
        _profile(onboarding_phase="extras", industry="tutoring"), "extras"
    )
    restaurant = build_onboarding_prompt(
        _profile(onboarding_phase="extras", industry="restaurant"), "extras"
    )
    assert tutoring != restaurant
    # Should diverge in the hints block specifically.
    assert "subjects_taught" in tutoring
    assert "subjects_taught" not in restaurant
    assert "cuisine_style" in restaurant
    assert "cuisine_style" not in tutoring


# ---------------------------------------------------------------------------
# Other touchpoint builders
# ---------------------------------------------------------------------------


def test_post_session_prompt_includes_session_summary_numbers():
    p = _profile(onboarding_phase="complete")
    summary = {
        "session_type": "image",
        "ads_generated": 5,
        "ads_published": 3,
        "avg_score": 8.4,
    }
    out = build_post_session_prompt(p, summary)
    assert "Post-session reflection" in out
    assert "5" in out  # ads_generated
    assert "8.4" in out


def test_post_session_prompt_handles_missing_summary():
    p = _profile(onboarding_phase="complete")
    out = build_post_session_prompt(p, None)
    assert "Post-session reflection" in out
    assert "unknown" in out.lower()


def test_pre_session_prep_prompt_mentions_propose_brief():
    p = _profile(onboarding_phase="complete")
    out = build_pre_session_prep_prompt(p, "video")
    assert "propose_brief" in out
    assert "video" in out


def test_pre_session_prep_prompt_forbids_brand_profile_writes():
    p = _profile(onboarding_phase="complete")
    out = build_pre_session_prep_prompt(p, "image")
    # Should explicitly tell the LLM no save_field / update_extra.
    assert "may NOT modify" in out or "not modify" in out.lower()


def test_refine_prompt_invites_targeted_edits():
    p = _profile(onboarding_phase="complete", business_name="Acme")
    out = build_refine_prompt(p)
    assert "Refine" in out
    assert "save_field" in out
    assert "Acme" in out  # snapshot


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def test_build_prompt_for_dispatches_correctly():
    p = _profile(onboarding_phase="identify")
    onboarding = build_prompt_for("onboarding", p)
    assert "Phase: Identify" in onboarding

    p2 = _profile(onboarding_phase="complete")
    refine = build_prompt_for("refine", p2)
    assert "Refine your brand" in refine

    pre = build_prompt_for("pre_session_prep", p2, session_type="video")
    assert "propose_brief" in pre

    post = build_prompt_for(
        "post_session", p2, session_summary={"ads_published": 7}
    )
    assert "Post-session reflection" in post
    assert "7" in post


def test_build_prompt_for_uses_industry_fallback_when_industry_none():
    p = _profile(onboarding_phase="extras", industry=None)
    out = build_prompt_for("onboarding", p)
    assert INDUSTRY_FALLBACK[:60] in out
