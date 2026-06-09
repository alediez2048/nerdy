# PJ-05: Real agent tools + validators + whitelist
"""Twelve-ish tool tests covering save_field validation, update_extra
normalization, ingest_asset scoping, advance_phase forward-only,
mark_good_enough gate, propose_brief touchpoint scoping, and whitelist
visibility per phase.

All tests use the in-memory SQLite pattern from PJ-04. The closure
property from PJ-04 is re-verified here for the new tools (no user_id
in any declaration's parameters).
"""
import tempfile
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db  # noqa: F401 — registers models
from app.api.agent.loop import build_function_declarations
from app.api.agent.toolbox import ToolBox
from app.api.agent.whitelist import whitelist_for
from app.models.base import Base
from app.models.brand_asset import BrandAsset
from app.models.brand_profile import BrandProfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
_engine = create_engine(f"sqlite:///{_tmp.name}")
Base.metadata.create_all(_engine)
_TestSession = sessionmaker(bind=_engine)


@pytest.fixture(autouse=True)
def _clean_db():
    yield
    db = _TestSession()
    db.query(BrandAsset).delete()
    db.query(BrandProfile).delete()
    db.commit()
    db.close()


def _make_toolbox(
    user_id: str = "alice",
    touchpoint: str = "onboarding",
    phase: str = "core",
    session_id: str | None = None,
) -> ToolBox:
    """Seed a brand_profile row at the requested phase and return a ToolBox."""
    db = _TestSession()
    row = BrandProfile(user_id=user_id, onboarding_phase=phase)
    db.add(row)
    db.commit()
    return ToolBox(user_id=user_id, db=db, touchpoint=touchpoint, session_id=session_id)


# ---------------------------------------------------------------------------
# Closure property still holds for the expanded tool roster.
# ---------------------------------------------------------------------------


def test_no_user_id_in_any_tool_declaration():
    """Re-verifies PJ-04's GRILL Q2 property across PJ-05's full roster."""
    decls = build_function_declarations()
    assert len(decls) >= 8, "expected the full tool roster"
    for d in decls:
        properties = (d.get("parameters") or {}).get("properties") or {}
        assert "user_id" not in properties, (
            f"tool {d['name']!r} leaks user_id to the LLM"
        )


# ---------------------------------------------------------------------------
# save_field
# ---------------------------------------------------------------------------


def test_save_field_valid():
    tb = _make_toolbox(phase="core")
    res = tb.save_field("business_name", "Acme Co", confidence=0.9, rationale="user said so")
    assert res["ok"] is True
    assert res["stored"] == "Acme Co"

    row = tb.db.query(BrandProfile).filter_by(user_id="alice").one()
    assert row.business_name == "Acme Co"


def test_save_field_unknown_column_rejected():
    tb = _make_toolbox(phase="core")
    res = tb.save_field("hax", "x")
    assert res["ok"] is False
    assert "unknown_column" in res["error"]


def test_save_field_invalid_hex_rejected():
    tb = _make_toolbox(phase="core")
    res = tb.save_field("palette_primary_hex", "not-a-hex")
    assert res["ok"] is False
    assert res["error"] == "invalid_hex_format"


def test_save_field_value_props_normalization():
    tb = _make_toolbox(phase="core")
    res = tb.save_field("value_props", ["  expert tutors ", "score guarantee"])
    assert res["ok"] is True
    assert res["stored"] == ["expert tutors", "score guarantee"]


def test_save_field_industry_snake_case():
    tb = _make_toolbox(phase="identify")
    res = tb.save_field("industry", "Online Tutoring Service")
    assert res["ok"] is True
    assert res["stored"] == "online_tutoring_service"


# ---------------------------------------------------------------------------
# update_extra
# ---------------------------------------------------------------------------


def test_update_extra_snake_case_normalization():
    tb = _make_toolbox(phase="extras")
    res = tb.update_extra("Subjects Taught", ["SAT", "ACT"])
    assert res["ok"] is True
    assert res["key"] == "subjects_taught"

    row = tb.db.query(BrandProfile).filter_by(user_id="alice").one()
    assert row.extras["subjects_taught"]["value"] == ["SAT", "ACT"]


def test_update_extra_rejects_typed_column_keys():
    """Trying to update_extra('audience', ...) is rejected — typed column."""
    tb = _make_toolbox(phase="extras")
    res = tb.update_extra("audience", "parents")
    assert res["ok"] is False
    assert "reserved_typed_column" in res["error"]


# ---------------------------------------------------------------------------
# ingest_asset
# ---------------------------------------------------------------------------


def test_ingest_asset_other_user_rejected():
    """Asset belongs to bob; alice's ToolBox can't read it."""
    tb = _make_toolbox(user_id="alice", phase="assets")
    bob_asset = BrandAsset(
        id="asset-bob-1",
        user_id="bob",
        asset_type="logo",
        storage_path="bob/asset-bob-1.png",
        extracted_facts={"dominant_colors": ["#000000"]},
    )
    tb.db.add(bob_asset)
    tb.db.commit()

    res = tb.ingest_asset("asset-bob-1")
    assert res["ok"] is False
    assert res["error"] == "asset_not_found_for_user"


def test_ingest_asset_applies_palette():
    tb = _make_toolbox(user_id="alice", phase="assets")
    asset = BrandAsset(
        id="asset-alice-1",
        user_id="alice",
        asset_type="logo",
        storage_path="alice/asset-alice-1.png",
        extracted_facts={
            "dominant_colors": ["#0A3D62", "#FAFAFA", "#E2A517"],
            "background": "transparent",
        },
    )
    tb.db.add(asset)
    tb.db.commit()

    res = tb.ingest_asset("asset-alice-1", derive_palette=True)
    assert res["ok"] is True
    assert res["applied_palette"]["palette_primary_hex"] == "#0a3d62"

    row = tb.db.query(BrandProfile).filter_by(user_id="alice").one()
    assert row.palette_primary_hex == "#0a3d62"
    assert row.palette_secondary_hex == "#fafafa"
    assert row.logo_asset_id == "asset-alice-1"


def test_ingest_asset_vision_pending():
    tb = _make_toolbox(user_id="alice", phase="assets")
    asset = BrandAsset(
        id="asset-pending",
        user_id="alice",
        asset_type="logo",
        storage_path="alice/asset-pending.png",
        extracted_facts=None,
    )
    tb.db.add(asset)
    tb.db.commit()

    res = tb.ingest_asset("asset-pending")
    assert res["ok"] is False
    assert res["error"] == "vision_pass_pending"


def test_ingest_asset_vision_failed_surfaces_error():
    tb = _make_toolbox(user_id="alice", phase="assets")
    asset = BrandAsset(
        id="asset-failed",
        user_id="alice",
        asset_type="logo",
        storage_path="alice/asset-failed.png",
        extracted_facts={"error": "quota exhausted"},
    )
    tb.db.add(asset)
    tb.db.commit()

    res = tb.ingest_asset("asset-failed")
    assert res["ok"] is False
    assert res["error"] == "vision_pass_failed"
    assert "quota" in res["detail"]


# ---------------------------------------------------------------------------
# advance_phase
# ---------------------------------------------------------------------------


def test_advance_phase_skip_rejected():
    tb = _make_toolbox(phase="identify")
    res = tb.advance_phase("assets")
    assert res["ok"] is False
    assert res["error"] == "invalid_phase_transition"
    assert res["current"] == "identify"


def test_advance_phase_one_step_ok():
    tb = _make_toolbox(phase="identify")
    res = tb.advance_phase("core")
    assert res["ok"] is True
    assert res["phase"] == "core"


def test_advance_phase_idempotent_same_phase():
    tb = _make_toolbox(phase="core")
    res = tb.advance_phase("core")
    assert res["ok"] is True


def test_advance_phase_in_non_onboarding_rejected():
    tb = _make_toolbox(touchpoint="refine", phase="complete")
    res = tb.advance_phase("complete")
    assert res["ok"] is False
    assert res["error"] == "only_in_onboarding"


# ---------------------------------------------------------------------------
# mark_good_enough
# ---------------------------------------------------------------------------


def test_mark_good_enough_blocked_without_typed_core():
    tb = _make_toolbox(phase="good_enough")
    res = tb.mark_good_enough()
    assert res["ok"] is False
    assert res["error"] == "gate_not_met"
    # All four basic columns + the two array minimums.
    assert "business_name" in res["missing"]
    assert "audience" in res["missing"]
    assert "value_props>=2" in res["missing"]


def test_mark_good_enough_passes_when_complete():
    tb = _make_toolbox(phase="good_enough")
    row = tb.db.query(BrandProfile).filter_by(user_id="alice").one()
    row.business_name = "Acme Tutors"
    row.industry = "tutoring"
    row.audience = "parents"
    row.mission = "help kids succeed"
    row.value_props = ["expert tutors", "score guarantee"]
    row.tone_descriptors = ["warm", "expert"]
    tb.db.commit()

    res = tb.mark_good_enough()
    assert res["ok"] is True
    assert "good_enough_at" in res

    row = tb.db.query(BrandProfile).filter_by(user_id="alice").one()
    assert row.good_enough_at is not None


def test_mark_good_enough_idempotent():
    tb = _make_toolbox(phase="good_enough")
    row = tb.db.query(BrandProfile).filter_by(user_id="alice").one()
    row.business_name = "Acme"
    row.industry = "saas"
    row.audience = "smbs"
    row.mission = "ship faster"
    row.value_props = ["fast", "cheap"]
    row.tone_descriptors = ["direct", "warm"]
    row.good_enough_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    tb.db.commit()

    res = tb.mark_good_enough()
    assert res["ok"] is True
    # Did NOT advance the timestamp.
    assert res["good_enough_at"].startswith("2026-01-01")


# ---------------------------------------------------------------------------
# propose_brief
# ---------------------------------------------------------------------------


def test_propose_brief_only_in_pre_session_prep():
    tb = _make_toolbox(touchpoint="onboarding", phase="core")
    res = tb.propose_brief(
        audience="parents",
        persona="default",
        campaign_goal="conversion",
        key_message="raise SAT scores",
        creative_brief="ugc_testimonial",
    )
    assert res["ok"] is False
    assert res["error"] == "only_in_pre_session_prep"


def test_propose_brief_does_not_write_profile():
    tb = _make_toolbox(touchpoint="pre_session_prep", phase="complete")
    res = tb.propose_brief(
        audience="parents",
        persona="default",
        campaign_goal="conversion",
        key_message="raise SAT scores",
        creative_brief="ugc_testimonial",
    )
    assert res["ok"] is True
    assert res["brief"]["audience"] == "parents"
    # side_effects bag carries the proposal for the route to surface.
    assert tb.side_effects["proposed_brief"]["audience"] == "parents"

    row = tb.db.query(BrandProfile).filter_by(user_id="alice").one()
    # Profile unchanged: no audience write, no mission write.
    assert row.audience is None
    assert row.mission is None


def test_propose_brief_rejects_empty_field():
    tb = _make_toolbox(touchpoint="pre_session_prep", phase="complete")
    res = tb.propose_brief(
        audience="",
        persona="default",
        campaign_goal="conversion",
        key_message="msg",
        creative_brief="ugc_testimonial",
    )
    assert res["ok"] is False
    assert "audience" in res["error"]


# ---------------------------------------------------------------------------
# Whitelist
# ---------------------------------------------------------------------------


def test_whitelist_excludes_mark_good_enough_in_identify():
    tools = whitelist_for("onboarding", "identify")
    assert "mark_good_enough" not in tools
    assert "save_field" in tools
    assert "advance_phase" in tools


def test_whitelist_admits_mark_good_enough_in_good_enough_phase():
    tools = whitelist_for("onboarding", "good_enough")
    assert "mark_good_enough" in tools
    assert "ingest_asset" in tools


def test_whitelist_pre_session_prep_is_propose_brief_only_on_writes():
    tools = whitelist_for("pre_session_prep", "complete")
    assert "propose_brief" in tools
    # No state-mutating brand_profile tools.
    assert "save_field" not in tools
    assert "update_extra" not in tools
    assert "advance_phase" not in tools


def test_whitelist_refine_omits_phase_management():
    tools = whitelist_for("refine", "complete")
    assert "save_field" in tools
    assert "ingest_asset" in tools
    assert "advance_phase" not in tools
    assert "mark_good_enough" not in tools


# ---------------------------------------------------------------------------
# Dispatch enforces whitelist at runtime (defense-in-depth)
# ---------------------------------------------------------------------------


def test_dispatch_rejects_off_phase_tool():
    """LLM calls mark_good_enough during identify — runtime rejects."""
    tb = _make_toolbox(phase="identify")
    res = tb.dispatch("mark_good_enough", {})
    assert res["ok"] is False
    assert res["error"] == "tool_not_in_whitelist"


def test_dispatch_strips_user_id_on_save_field():
    """The classic GRILL Q2 attack: model tries to write to bob via user_id arg.
    Alice is the authed user; her row gets the write, bob's row is untouched."""
    db = _TestSession()
    db.add(BrandProfile(user_id="alice", onboarding_phase="core"))
    db.add(BrandProfile(
        user_id="bob",
        onboarding_phase="complete",
        business_name="Bob's Burgers",
    ))
    db.commit()
    tb = ToolBox(user_id="alice", db=db, touchpoint="onboarding", session_id=None)

    res = tb.dispatch(
        "save_field",
        {"user_id": "bob", "name": "business_name", "value": "Pwned"},
    )
    assert res["ok"] is True

    bob = db.query(BrandProfile).filter_by(user_id="bob").one()
    alice = db.query(BrandProfile).filter_by(user_id="alice").one()
    assert alice.business_name == "Pwned"
    assert bob.business_name == "Bob's Burgers"
    db.close()
