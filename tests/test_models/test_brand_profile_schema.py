# PJ-01: Brand profile + conversation + asset schema tests
"""Smoke + roundtrip tests for the three PJ-01 models.

In-memory SQLite + Base.metadata.create_all matches the existing
``test_app/test_models.py`` pattern. Real Postgres-specific behaviour
(JSONB indexing, ARRAY operators) is not exercised here — the column
types use generic SQLAlchemy ``JSON`` for portability.
"""
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.brand_asset import BrandAsset
from app.models.brand_profile import BrandProfile
from app.models.conversation_message import ConversationMessage

# Force full model registration. app.db imports every model so the FK
# chain (conversation_messages → sessions → campaigns) resolves.
import app.db  # noqa: F401


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


# --- BrandProfile ---------------------------------------------------


def test_brand_profile_create_minimal(db):
    """Write a row with only user_id; defaults fill in."""
    row = BrandProfile(user_id="user_abc")
    db.add(row)
    db.commit()
    db.refresh(row)

    assert row.user_id == "user_abc"
    assert row.onboarding_phase == "identify"
    assert row.extras == {}
    assert row.good_enough_at is None
    assert row.created_at is not None
    assert row.business_name is None
    assert row.value_props is None


def test_brand_profile_extras_jsonb_roundtrip(db):
    """A nested dict round-trips through the extras column unchanged."""
    nested = {
        "subjects_taught": ["SAT", "ACT", "AP Calculus"],
        "scoring_proof": {"avg_lift_pts": 180, "median": 150},
        "is_franchise": False,
    }
    row = BrandProfile(user_id="user_extras", extras=nested)
    db.add(row)
    db.commit()
    db.refresh(row)

    assert row.extras == nested
    assert row.extras["scoring_proof"]["avg_lift_pts"] == 180


def test_brand_profile_typed_arrays_roundtrip(db):
    """value_props / tone_descriptors store lists of strings."""
    row = BrandProfile(
        user_id="user_arrays",
        value_props=["expert tutors", "1-on-1 match guarantee", "results-backed"],
        tone_descriptors=["reassuring", "data-driven", "warm"],
        avoid_phrases=["guarantee a score", "miracle"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    assert row.value_props == [
        "expert tutors",
        "1-on-1 match guarantee",
        "results-backed",
    ]
    assert row.tone_descriptors[1] == "data-driven"
    assert row.avoid_phrases == ["guarantee a score", "miracle"]


def test_brand_profile_good_enough_gate(db):
    """Setting good_enough_at simulates the session-gate unlock."""
    row = BrandProfile(user_id="user_gate")
    db.add(row)
    db.commit()
    assert row.good_enough_at is None

    row.good_enough_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    assert row.good_enough_at is not None


# --- ConversationMessage --------------------------------------------


def test_conversation_message_append(db):
    """Three appended rows for the same (user, touchpoint) return in order."""
    db.add(BrandProfile(user_id="user_conv"))
    db.commit()

    db.add_all([
        ConversationMessage(
            user_id="user_conv", touchpoint="onboarding",
            role="assistant", content="Welcome! What's your business?",
            phase="identify",
        ),
        ConversationMessage(
            user_id="user_conv", touchpoint="onboarding",
            role="user", content="I run a tutoring service.",
            phase="identify",
        ),
        ConversationMessage(
            user_id="user_conv", touchpoint="onboarding",
            role="tool", tool_results={"saved": "business_name"},
            phase="identify",
        ),
    ])
    db.commit()

    rows = db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.user_id == "user_conv")
        .order_by(ConversationMessage.created_at, ConversationMessage.id)
    ).scalars().all()

    assert len(rows) == 3
    assert [r.role for r in rows] == ["assistant", "user", "tool"]
    assert rows[2].tool_results == {"saved": "business_name"}


def test_conversation_message_per_touchpoint_isolation(db):
    """Messages for different touchpoints are queryable independently."""
    db.add(BrandProfile(user_id="user_multi"))
    db.commit()
    db.add_all([
        ConversationMessage(
            user_id="user_multi", touchpoint="onboarding",
            role="user", content="onboarding msg",
        ),
        ConversationMessage(
            user_id="user_multi", touchpoint="refine",
            role="user", content="refine msg",
        ),
    ])
    db.commit()

    onb = db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.user_id == "user_multi")
        .where(ConversationMessage.touchpoint == "onboarding")
    ).scalars().all()
    assert len(onb) == 1
    assert onb[0].content == "onboarding msg"


# --- BrandAsset -----------------------------------------------------


def test_brand_asset_create(db):
    """Create a row, get an auto-generated UUID id, read storage_path back."""
    asset = BrandAsset(
        user_id="user_asset",
        asset_type="logo",
        original_filename="acme-logo.png",
        storage_path="user_asset/abcd-1234.png",
        mime_type="image/png",
        size_bytes=42_000,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    assert asset.id is not None
    assert len(asset.id) == 36  # UUID4 string length
    assert asset.storage_path == "user_asset/abcd-1234.png"
    assert asset.asset_type == "logo"
    assert asset.extracted_facts is None


def test_brand_asset_extracted_facts_roundtrip(db):
    """The PJ-03 vision pass populates extracted_facts after upload."""
    asset = BrandAsset(
        user_id="user_facts",
        asset_type="logo",
        storage_path="user_facts/zzz.png",
    )
    db.add(asset)
    db.commit()

    asset.extracted_facts = {
        "palette": ["#0a3d62", "#fafafa", "#e2a517"],
        "fonts_detected": ["Inter"],
        "background_type": "transparent",
    }
    db.commit()
    db.refresh(asset)

    assert asset.extracted_facts["palette"][0] == "#0a3d62"
    assert asset.extracted_facts["background_type"] == "transparent"


# --- Metadata --------------------------------------------------------


def test_metadata_create_all_idempotent():
    """Calling create_all twice on the same engine does not raise."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    # Second call should be a no-op, not an error.
    Base.metadata.create_all(engine)
