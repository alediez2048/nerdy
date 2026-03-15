# PA-02: Database model tests
"""Tests for User, Session, CuratedSet, CuratedAd models using in-memory SQLite."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.curation import CuratedAd, CuratedSet
from app.models.session import Session
from app.models.user import User


@pytest.fixture()
def db():
    """In-memory SQLite database for model tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


# --- User model ---


def test_user_creation(db):
    user = User(
        google_id="google_123",
        email="jad@nerdy.com",
        name="Jad",
        picture_url="https://example.com/photo.jpg",
        last_login_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.id is not None
    assert user.google_id == "google_123"
    assert user.email == "jad@nerdy.com"
    assert user.name == "Jad"
    assert user.picture_url == "https://example.com/photo.jpg"
    assert user.last_login_at is not None
    assert user.created_at is not None


def test_user_email_unique(db):
    u1 = User(google_id="g1", email="jad@nerdy.com", name="Jad")
    u2 = User(google_id="g2", email="jad@nerdy.com", name="Jad2")
    db.add(u1)
    db.commit()
    db.add(u2)
    with pytest.raises(Exception):  # IntegrityError
        db.commit()


# --- Session model ---


def test_session_creation_with_extended_fields(db):
    session_row = Session(
        session_id="sess_abc123",
        name="SAT Parents Conversion — Mar 15",
        user_id="test-user",
        config={"audience": "parents", "campaign_goal": "conversion", "ad_count": 50},
        status="pending",
        ledger_path="data/sessions/sess_abc123/ledger.jsonl",
        output_path="data/sessions/sess_abc123/output/",
    )
    db.add(session_row)
    db.commit()
    db.refresh(session_row)

    assert session_row.id is not None
    assert session_row.name == "SAT Parents Conversion — Mar 15"
    assert session_row.ledger_path == "data/sessions/sess_abc123/ledger.jsonl"
    assert session_row.output_path == "data/sessions/sess_abc123/output/"
    assert session_row.completed_at is None
    assert session_row.config["audience"] == "parents"


def test_session_completed_at_set_on_completion(db):
    session_row = Session(
        session_id="sess_done",
        user_id="test-user",
        config={},
        status="completed",
        completed_at=datetime.now(timezone.utc),
    )
    db.add(session_row)
    db.commit()
    db.refresh(session_row)

    assert session_row.completed_at is not None
    assert session_row.status == "completed"


# --- CuratedSet + CuratedAd ---


def test_curated_set_creation(db):
    session_row = Session(session_id="sess_cur", user_id="test-user", config={})
    db.add(session_row)
    db.commit()

    cs = CuratedSet(session_id=session_row.id, name="Best Ads")
    db.add(cs)
    db.commit()
    db.refresh(cs)

    assert cs.id is not None
    assert cs.name == "Best Ads"
    assert cs.session_id == session_row.id


def test_curated_ad_with_annotation_and_edit(db):
    session_row = Session(session_id="sess_cad", user_id="test-user", config={})
    db.add(session_row)
    db.commit()

    cs = CuratedSet(session_id=session_row.id, name="Set 1")
    db.add(cs)
    db.commit()

    ad = CuratedAd(
        curated_set_id=cs.id,
        ad_id="ad_001",
        position=1,
        annotation="Great hook, needs shorter CTA",
        edited_copy={
            "primary_text": {
                "original": "Struggling with SAT prep?",
                "edited": "SAT scores holding you back?",
            }
        },
    )
    db.add(ad)
    db.commit()
    db.refresh(ad)

    assert ad.position == 1
    assert ad.annotation == "Great hook, needs shorter CTA"
    assert ad.edited_copy["primary_text"]["original"] == "Struggling with SAT prep?"
    assert ad.edited_copy["primary_text"]["edited"] == "SAT scores holding you back?"


def test_curated_set_to_ads_relationship(db):
    session_row = Session(session_id="sess_rel", user_id="test-user", config={})
    db.add(session_row)
    db.commit()

    cs = CuratedSet(session_id=session_row.id, name="Top Picks")
    db.add(cs)
    db.commit()

    ad1 = CuratedAd(curated_set_id=cs.id, ad_id="ad_01", position=1)
    ad2 = CuratedAd(curated_set_id=cs.id, ad_id="ad_02", position=2)
    ad3 = CuratedAd(curated_set_id=cs.id, ad_id="ad_03", position=3)
    db.add_all([ad1, ad2, ad3])
    db.commit()

    db.refresh(cs)
    assert len(cs.ads) == 3
    assert [a.ad_id for a in cs.ads] == ["ad_01", "ad_02", "ad_03"]


def test_session_to_curated_sets_relationship(db):
    session_row = Session(session_id="sess_s2c", user_id="test-user", config={})
    db.add(session_row)
    db.commit()

    cs1 = CuratedSet(session_id=session_row.id, name="Set A")
    cs2 = CuratedSet(session_id=session_row.id, name="Set B")
    db.add_all([cs1, cs2])
    db.commit()

    db.refresh(session_row)
    assert len(session_row.curated_sets) == 2
    assert {cs.name for cs in session_row.curated_sets} == {"Set A", "Set B"}
