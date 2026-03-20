# PC-04: Campaign CRUD tests
"""Tests for campaign creation, listing, filtering, per-user isolation, and soft delete."""

import tempfile
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
import app.models.user  # noqa: F401
import app.models.session  # noqa: F401
import app.models.curation  # noqa: F401
import app.models.campaign  # noqa: F401


@asynccontextmanager
async def _noop_lifespan(app):
    yield


# Use a temp file DB per test run
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
_DB_PATH = _tmp.name
_engine = create_engine(f"sqlite:///{_DB_PATH}")
Base.metadata.create_all(_engine)
_TestSessionLocal = sessionmaker(bind=_engine)


def _override_get_db():
    db = _TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _clean_rows():
    """Delete all campaign rows before and after each test."""
    from app.models.campaign import Campaign as CampaignModel
    db = _TestSessionLocal()
    db.query(CampaignModel).delete()
    db.commit()
    db.close()
    yield
    db = _TestSessionLocal()
    db.query(CampaignModel).delete()
    db.commit()
    db.close()


def _build_app_with_user(user_id: str):
    """Build a fresh TestClient with a specific user override."""
    from app.api.main import app
    from app.api.deps import get_current_user
    from app.db import get_db

    def override_user():
        return {"user_id": user_id, "email": f"{user_id}@nerdy.com", "name": user_id}

    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = override_user

    p1 = patch("app.api.main.lifespan", _noop_lifespan)
    p2 = patch("app.api.routes.campaigns.init_db")
    p1.start()
    p2.start()

    client = TestClient(app)
    return client, [p1, p2]


@pytest.fixture()
def alice():
    client, patches = _build_app_with_user("alice")
    yield client
    client.close()
    for p in patches:
        p.stop()
    from app.api.main import app
    app.dependency_overrides.clear()


@pytest.fixture()
def bob():
    client, patches = _build_app_with_user("bob")
    yield client
    client.close()
    for p in patches:
        p.stop()
    from app.api.main import app
    app.dependency_overrides.clear()


def test_create_campaign_returns_201_with_campaign_id(alice):
    """Create campaign returns 201 with auto-generated campaign_id."""
    resp = alice.post("/api/campaigns", json={"name": "Spring SAT Push"})
    assert resp.status_code == 201
    data = resp.json()
    assert "campaign_id" in data
    assert data["campaign_id"].startswith("camp_")
    assert len(data["campaign_id"]) == 21  # "camp_" + 16 hex chars
    assert data["name"] == "Spring SAT Push"
    assert data["status"] == "active"
    assert data["session_count"] == 0


def test_create_campaign_with_all_optional_fields(alice):
    """Create campaign with description, audience, goal, and default_config."""
    resp = alice.post(
        "/api/campaigns",
        json={
            "name": "Back-to-School",
            "description": "Q3 awareness campaign",
            "audience": "parents",
            "campaign_goal": "awareness",
            "default_config": {"ad_count": 30, "persona": "suburban_optimizer"},
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Back-to-School"
    assert data["description"] == "Q3 awareness campaign"
    assert data["audience"] == "parents"
    assert data["campaign_goal"] == "awareness"
    assert data["default_config"] == {"ad_count": 30, "persona": "suburban_optimizer"}


def test_create_campaign_rejects_empty_name(alice):
    """Create campaign with empty name returns 400."""
    resp = alice.post("/api/campaigns", json={"name": ""})
    assert resp.status_code == 422  # Validation error


def test_create_campaign_rejects_whitespace_only_name(alice):
    """Create campaign with whitespace-only name returns 400."""
    resp = alice.post("/api/campaigns", json={"name": "   "})
    assert resp.status_code == 422  # Validation error


def test_list_campaigns_returns_only_users_campaigns():
    """List campaigns returns only the requesting user's campaigns."""
    # Alice creates a campaign
    client_a, patches_a = _build_app_with_user("alice")
    client_a.post("/api/campaigns", json={"name": "Alice Campaign"})
    client_a.close()
    for p in patches_a:
        p.stop()
    from app.api.main import app
    app.dependency_overrides.clear()

    # Bob creates a campaign
    client_b, patches_b = _build_app_with_user("bob")
    client_b.post("/api/campaigns", json={"name": "Bob Campaign"})
    client_b.close()
    for p in patches_b:
        p.stop()
    app.dependency_overrides.clear()

    # Alice should only see her campaign
    client_a2, patches_a2 = _build_app_with_user("alice")
    resp = client_a2.get("/api/campaigns")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["campaigns"][0]["name"] == "Alice Campaign"
    client_a2.close()
    for p in patches_a2:
        p.stop()
    app.dependency_overrides.clear()

    # Bob should only see his campaign
    client_b2, patches_b2 = _build_app_with_user("bob")
    resp = client_b2.get("/api/campaigns")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["campaigns"][0]["name"] == "Bob Campaign"
    client_b2.close()
    for p in patches_b2:
        p.stop()
    app.dependency_overrides.clear()


def test_list_campaigns_pagination(alice):
    """List campaigns supports offset and limit pagination."""
    # Create 5 campaigns
    for i in range(5):
        alice.post("/api/campaigns", json={"name": f"Campaign {i}"})

    # First page: limit=2
    resp = alice.get("/api/campaigns?limit=2&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["campaigns"]) == 2
    assert data["offset"] == 0
    assert data["limit"] == 2

    # Second page: limit=2, offset=2
    resp = alice.get("/api/campaigns?limit=2&offset=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["campaigns"]) == 2
    assert data["offset"] == 2


def test_list_campaigns_filter_by_status(alice):
    """List campaigns can filter by status (active/archived)."""
    # Create active campaign
    resp1 = alice.post("/api/campaigns", json={"name": "Active Campaign"})
    active_id = resp1.json()["campaign_id"]

    # Create and archive a campaign
    resp2 = alice.post("/api/campaigns", json={"name": "To Archive"})
    archive_id = resp2.json()["campaign_id"]
    alice.delete(f"/api/campaigns/{archive_id}")

    # List active only (default)
    resp = alice.get("/api/campaigns")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["campaigns"][0]["campaign_id"] == active_id

    # List archived only
    resp = alice.get("/api/campaigns?status=archived")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["campaigns"][0]["campaign_id"] == archive_id


def test_get_campaign_detail_includes_session_count(alice):
    """Get campaign detail includes session_count (0 for new campaign)."""
    resp = alice.post("/api/campaigns", json={"name": "Test Campaign"})
    campaign_id = resp.json()["campaign_id"]

    resp = alice.get(f"/api/campaigns/{campaign_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["campaign_id"] == campaign_id
    assert data["name"] == "Test Campaign"
    assert data["session_count"] == 0
    assert "default_config" in data
    assert "updated_at" in data


def test_update_campaign_name(alice):
    """Update campaign name works."""
    resp = alice.post("/api/campaigns", json={"name": "Old Name"})
    campaign_id = resp.json()["campaign_id"]

    resp = alice.patch(f"/api/campaigns/{campaign_id}", json={"name": "New Name"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"

    # Verify persisted
    resp = alice.get(f"/api/campaigns/{campaign_id}")
    assert resp.json()["name"] == "New Name"


def test_update_campaign_status_to_archived(alice):
    """Update campaign status to archived works."""
    resp = alice.post("/api/campaigns", json={"name": "To Archive"})
    campaign_id = resp.json()["campaign_id"]

    resp = alice.patch(f"/api/campaigns/{campaign_id}", json={"status": "archived"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "archived"

    # Verify archived campaigns don't appear in default list
    resp = alice.get("/api/campaigns")
    assert resp.json()["total"] == 0


def test_delete_campaign_sets_status_to_archived(alice):
    """Delete campaign performs soft delete (sets status to archived)."""
    resp = alice.post("/api/campaigns", json={"name": "To Delete"})
    campaign_id = resp.json()["campaign_id"]

    resp = alice.delete(f"/api/campaigns/{campaign_id}")
    assert resp.status_code == 200

    # Campaign should still exist but be archived
    resp = alice.get(f"/api/campaigns/{campaign_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"

    # Should not appear in active list
    resp = alice.get("/api/campaigns")
    assert resp.json()["total"] == 0


def test_get_nonexistent_campaign_returns_404(alice):
    """Get non-existent campaign returns 404."""
    resp = alice.get("/api/campaigns/camp_nonexistent")
    assert resp.status_code == 404


def test_campaign_isolation_user_a_cannot_see_user_b_campaigns():
    """User A cannot see or access User B's campaigns."""
    # Bob creates a campaign
    client_b, patches_b = _build_app_with_user("bob")
    resp = client_b.post("/api/campaigns", json={"name": "Bob's Secret Campaign"})
    bob_campaign_id = resp.json()["campaign_id"]
    client_b.close()
    for p in patches_b:
        p.stop()
    from app.api.main import app
    app.dependency_overrides.clear()

    # Alice cannot see it in list
    client_a, patches_a = _build_app_with_user("alice")
    resp = client_a.get("/api/campaigns")
    assert resp.json()["total"] == 0

    # Alice cannot access it directly
    resp = client_a.get(f"/api/campaigns/{bob_campaign_id}")
    assert resp.status_code == 404

    # Alice cannot update it
    resp = client_a.patch(f"/api/campaigns/{bob_campaign_id}", json={"name": "Hacked"})
    assert resp.status_code == 404

    # Alice cannot delete it
    resp = client_a.delete(f"/api/campaigns/{bob_campaign_id}")
    assert resp.status_code == 404
    client_a.close()
    for p in patches_a:
        p.stop()
    app.dependency_overrides.clear()
