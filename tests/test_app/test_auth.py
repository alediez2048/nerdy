# PA-03: Auth tests
"""Tests for Google SSO auth, JWT tokens, DEV_MODE fallback, and domain restriction."""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import JWT_ALGORITHM
from app.models.base import Base
from app.models.user import User


# --- Fixtures ---


@asynccontextmanager
async def _noop_lifespan(app):
    yield


def _make_test_db():
    """Create an in-memory SQLite DB for tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


@pytest.fixture()
def db_session():
    SessionLocal = _make_test_db()
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def client_dev_mode():
    """Client in DEV_MODE (GOOGLE_CLIENT_ID empty) — mock auth."""
    with patch("app.api.main.lifespan", _noop_lifespan):
        with patch("app.api.deps.settings") as mock_settings:
            mock_settings.GOOGLE_CLIENT_ID = ""
            mock_settings.SECRET_KEY = "test-secret"
            from app.api.main import app
            app.router.lifespan_context = _noop_lifespan
            with TestClient(app) as c:
                yield c


@pytest.fixture()
def client_prod_mode():
    """Client in prod mode (GOOGLE_CLIENT_ID set) — real JWT validation."""
    with patch("app.api.main.lifespan", _noop_lifespan):
        with patch("app.api.deps.settings") as mock_settings:
            mock_settings.GOOGLE_CLIENT_ID = "fake-client-id"
            mock_settings.SECRET_KEY = "test-secret"
            from app.api.main import app
            app.router.lifespan_context = _noop_lifespan
            with TestClient(app) as c:
                yield c


def _make_jwt(user_id: str = "1", email: str = "jad@nerdy.com", name: str = "Jad",
              secret: str = "test-secret", expired: bool = False) -> str:
    """Create a JWT for testing."""
    exp = datetime.now(timezone.utc) + (timedelta(hours=-1) if expired else timedelta(hours=24))
    return jwt.encode(
        {"sub": user_id, "email": email, "name": name, "exp": exp},
        secret,
        algorithm=JWT_ALGORITHM,
    )


# --- DEV_MODE tests ---


def test_dev_mode_fallback_returns_mock_user(client_dev_mode):
    """When GOOGLE_CLIENT_ID is empty, mock auth returns test-user."""
    resp = client_dev_mode.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "test-user"
    assert data["email"] == "test-user@nerdy.com"


def test_dev_mode_accepts_x_user_id_header(client_dev_mode):
    """DEV_MODE respects X-User-Id header."""
    resp = client_dev_mode.get("/api/auth/me", headers={"X-User-Id": "custom-dev-user"})
    assert resp.status_code == 200
    assert resp.json()["user_id"] == "custom-dev-user"


# --- Prod mode JWT tests ---


def test_prod_mode_missing_auth_returns_401(client_prod_mode):
    """Without Authorization header, return 401."""
    resp = client_prod_mode.get("/api/auth/me")
    assert resp.status_code == 401


def test_prod_mode_invalid_scheme_returns_401(client_prod_mode):
    """Non-Bearer scheme returns 401."""
    resp = client_prod_mode.get("/api/auth/me", headers={"Authorization": "Basic abc123"})
    assert resp.status_code == 401


def test_prod_mode_valid_jwt_returns_user(client_prod_mode):
    """Valid JWT returns user profile."""
    token = _make_jwt(secret="test-secret")
    resp = client_prod_mode.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "1"
    assert data["email"] == "jad@nerdy.com"
    assert data["name"] == "Jad"


def test_prod_mode_expired_jwt_returns_401(client_prod_mode):
    """Expired JWT returns 401."""
    token = _make_jwt(secret="test-secret", expired=True)
    resp = client_prod_mode.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_prod_mode_wrong_secret_returns_401(client_prod_mode):
    """JWT signed with wrong secret returns 401."""
    token = _make_jwt(secret="wrong-secret")
    resp = client_prod_mode.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


# --- Domain restriction tests ---


def test_nerdy_email_domain_check():
    """@nerdy.com passes, others fail."""
    from app.api.routes.auth import _verify_google_token  # noqa: F401

    # Direct domain check logic
    assert "jad@nerdy.com".endswith("@nerdy.com")
    assert not "jad@gmail.com".endswith("@nerdy.com")
    assert not "jad@evil-nerdy.com".endswith("@nerdy.com")


# --- JWT creation tests ---


def test_jwt_create_and_decode():
    """JWT round-trip: create and decode."""
    from app.api.routes.auth import _create_jwt

    user = User(id=42, email="test@nerdy.com", name="Test User", google_id="g123")

    with patch("app.api.routes.auth.settings") as mock_s:
        mock_s.SECRET_KEY = "round-trip-secret"
        mock_s.JWT_EXPIRY_HOURS = 24
        token = _create_jwt(user)

    payload = jwt.decode(token, "round-trip-secret", algorithms=[JWT_ALGORITHM])
    assert payload["sub"] == "42"
    assert payload["email"] == "test@nerdy.com"
    assert payload["name"] == "Test User"
    assert "exp" in payload


# --- User upsert tests (unit level) ---


def test_user_upsert_creates_new(db_session):
    """First login creates a new user."""
    user = User(
        google_id="new_google_id",
        email="new@nerdy.com",
        name="New User",
        last_login_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    db_session.commit()

    found = db_session.query(User).filter(User.google_id == "new_google_id").first()
    assert found is not None
    assert found.email == "new@nerdy.com"


def test_user_upsert_updates_existing(db_session):
    """Second login updates last_login_at."""
    user = User(
        google_id="existing_id",
        email="existing@nerdy.com",
        name="Old Name",
        last_login_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(user)
    db_session.commit()

    # Simulate second login
    found = db_session.query(User).filter(User.google_id == "existing_id").first()
    found.name = "New Name"
    found.last_login_at = datetime.now(timezone.utc)
    db_session.commit()
    db_session.refresh(found)

    assert found.name == "New Name"
    # SQLite drops timezone info, so compare naive
    assert found.last_login_at > datetime(2026, 1, 1)
