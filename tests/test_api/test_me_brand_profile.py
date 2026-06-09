# PJ-08: /api/me/brand-profile tests
"""Scoping + 404 + serialization shape for the Settings card's data source."""
import tempfile
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db  # noqa: F401 — registers models
from app.models.base import Base
from app.models.brand_profile import BrandProfile


@asynccontextmanager
async def _noop_lifespan(app):
    yield


_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
_engine = create_engine(f"sqlite:///{_tmp_db.name}")
Base.metadata.create_all(_engine)
_TestSession = sessionmaker(bind=_engine)


def _override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


_USER_ALICE = {"user_id": "alice", "email": "a@nerdy.com", "name": "Alice"}
_USER_BOB = {"user_id": "bob", "email": "b@nerdy.com", "name": "Bob"}
_current = {"v": _USER_ALICE}


def _override_user():
    return _current["v"]


@pytest.fixture(autouse=True)
def _clean_db():
    yield
    db = _TestSession()
    db.query(BrandProfile).delete()
    db.commit()
    db.close()
    _current["v"] = _USER_ALICE


@pytest.fixture()
def client():
    from app.api.deps import get_current_user
    from app.api.main import app
    from app.db import get_db

    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_user
    with (
        patch("app.api.main.lifespan", _noop_lifespan),
        patch("app.api.routes.me.init_db"),
    ):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


def test_returns_404_when_no_profile(client):
    """A user with no brand_profile row gets 404 — frontend reads this
    as 'onboarding not started yet'."""
    resp = client.get("/api/me/brand-profile")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "no_brand_profile"


def test_returns_profile_for_current_user(client):
    """Full serialization round-trip when the user has a row."""
    db = _TestSession()
    db.add(BrandProfile(
        user_id="alice",
        business_name="Acme Tutors",
        industry="tutoring",
        audience="parents",
        mission="help kids ace the SAT",
        value_props=["expert tutors", "score guarantee"],
        tone_descriptors=["warm", "data-driven"],
        avoid_phrases=["guarantee a score"],
        do_dont_rules={"do": ["use teal"], "dont": ["stock handshakes"]},
        palette_primary_hex="#0a3d62",
        palette_secondary_hex="#fafafa",
        extras={"subjects_taught": ["SAT", "ACT"]},
        onboarding_phase="complete",
    ))
    db.commit()
    db.close()

    resp = client.get("/api/me/brand-profile")
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == "alice"
    assert body["business_name"] == "Acme Tutors"
    assert body["industry"] == "tutoring"
    assert body["value_props"] == ["expert tutors", "score guarantee"]
    assert body["do_dont_rules"]["do"] == ["use teal"]
    assert body["palette_primary_hex"] == "#0a3d62"
    assert body["extras"]["subjects_taught"] == ["SAT", "ACT"]
    assert body["onboarding_phase"] == "complete"
    assert body["logo_asset_url"] is None  # no logo


def test_does_not_return_other_users_profile(client):
    """The endpoint takes no path param — there's no way to reach
    another user's row through it. Authing as Bob returns Bob's data,
    not Alice's."""
    db = _TestSession()
    db.add(BrandProfile(user_id="alice", business_name="Alice's Business"))
    db.add(BrandProfile(user_id="bob", business_name="Bob's Burgers"))
    db.commit()
    db.close()

    # Authed as Alice.
    resp = client.get("/api/me/brand-profile")
    assert resp.status_code == 200
    assert resp.json()["business_name"] == "Alice's Business"

    # Switch to Bob — same endpoint, different row.
    _current["v"] = _USER_BOB
    resp2 = client.get("/api/me/brand-profile")
    assert resp2.status_code == 200
    assert resp2.json()["business_name"] == "Bob's Burgers"


def test_logo_asset_url_set_when_logo_asset_id_present(client):
    """``logo_asset_url`` is derived from ``logo_asset_id`` for the
    frontend's logo thumbnail rendering."""
    db = _TestSession()
    db.add(BrandProfile(
        user_id="alice",
        business_name="Acme",
        logo_asset_id="abc-uuid-1234",
    ))
    db.commit()
    db.close()

    resp = client.get("/api/me/brand-profile")
    body = resp.json()
    assert body["logo_asset_url"] == "/api/brand-assets/abc-uuid-1234"


def test_null_arrays_serialize_as_empty(client):
    """``value_props`` etc. start NULL on a fresh profile; serialize as
    [] so the frontend doesn't have to null-check every field."""
    db = _TestSession()
    db.add(BrandProfile(user_id="alice"))
    db.commit()
    db.close()

    resp = client.get("/api/me/brand-profile")
    body = resp.json()
    assert body["value_props"] == []
    assert body["tone_descriptors"] == []
    assert body["avoid_phrases"] == []
    assert body["extras"] == {}
