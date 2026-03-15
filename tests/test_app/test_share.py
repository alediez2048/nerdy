# PA-11: Share session link tests
"""Tests for share token creation, access, expiry, revocation, and per-user isolation."""

import tempfile
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
import app.models.user  # noqa: F401
import app.models.session  # noqa: F401
import app.models.curation  # noqa: F401
import app.models.share_token  # noqa: F401
from app.models.session import Session as SessionModel
from app.models.share_token import ShareToken


@asynccontextmanager
async def _noop_lifespan(app):
    yield


_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
_engine = create_engine(f"sqlite:///{_tmp.name}")
Base.metadata.create_all(_engine)
_TestSession = sessionmaker(bind=_engine)


def _override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


def _override_user_alice():
    return {"user_id": "alice", "email": "alice@nerdy.com", "name": "Alice"}


def _override_user_bob():
    return {"user_id": "bob", "email": "bob@nerdy.com", "name": "Bob"}


@pytest.fixture(autouse=True)
def _clean():
    yield
    db = _TestSession()
    db.query(ShareToken).delete()
    db.query(SessionModel).delete()
    db.commit()
    db.close()


def _seed_session(session_id: str = "sess_share", user_id: str = "alice") -> SessionModel:
    db = _TestSession()
    row = SessionModel(
        session_id=session_id, user_id=user_id,
        config={"audience": "parents"}, status="completed",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    db.close()
    return row


def _make_client(user_fn):
    from app.api.main import app
    from app.api.deps import get_current_user
    from app.db import get_db

    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = user_fn

    patches = [
        patch("app.api.main.lifespan", _noop_lifespan),
        patch("app.api.routes.share.init_db"),
    ]
    for p in patches:
        p.start()

    return TestClient(app), patches


@pytest.fixture()
def client_alice():
    c, patches = _make_client(_override_user_alice)
    yield c
    c.close()
    for p in patches:
        p.stop()
    from app.api.main import app
    app.dependency_overrides.clear()


# --- Create share token ---


def test_create_share_returns_url(client_alice):
    _seed_session()
    resp = client_alice.post("/sessions/sess_share/share")
    assert resp.status_code == 200
    data = resp.json()
    assert "share_url" in data
    assert "token" in data
    assert "expires_at" in data
    assert "/shared/" in data["share_url"]


def test_create_share_idempotent(client_alice):
    _seed_session()
    resp1 = client_alice.post("/sessions/sess_share/share")
    resp2 = client_alice.post("/sessions/sess_share/share")
    assert resp1.json()["token"] == resp2.json()["token"]


def test_other_user_cannot_share(client_alice):
    _seed_session(user_id="bob")
    resp = client_alice.post("/sessions/sess_share/share")
    assert resp.status_code == 404


# --- Access shared session ---


def test_shared_link_returns_session_data(client_alice):
    _seed_session()
    resp = client_alice.post("/sessions/sess_share/share")
    token = resp.json()["token"]

    # Access shared endpoint (no auth needed)
    shared_resp = client_alice.get(f"/shared/{token}")
    assert shared_resp.status_code == 200
    data = shared_resp.json()
    assert data["session_id"] == "sess_share"
    assert data["read_only"] is True


def test_invalid_token_returns_404(client_alice):
    resp = client_alice.get("/shared/totally_fake_token")
    assert resp.status_code == 404


# --- Revoke ---


def test_revoked_token_returns_404(client_alice):
    _seed_session()
    resp = client_alice.post("/sessions/sess_share/share")
    token = resp.json()["token"]

    # Revoke
    client_alice.delete("/sessions/sess_share/share")

    # Now accessing should fail
    shared_resp = client_alice.get(f"/shared/{token}")
    assert shared_resp.status_code == 404


# --- Expired token ---


def test_expired_token_returns_404(client_alice):
    _seed_session()

    # Manually insert an expired token
    db = _TestSession()
    session_row = db.query(SessionModel).filter(SessionModel.session_id == "sess_share").first()
    expired = ShareToken(
        token="expired_token_123",
        session_id=session_row.id,
        created_by="alice",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db.add(expired)
    db.commit()
    db.close()

    resp = client_alice.get("/shared/expired_token_123")
    assert resp.status_code == 404
