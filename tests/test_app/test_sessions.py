# PA-04: Session CRUD tests
"""Tests for session creation, listing, filtering, per-user isolation, and deletion."""

import tempfile
from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
import app.models.user  # noqa: F401
import app.models.session  # noqa: F401
import app.models.curation  # noqa: F401


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
    """Delete all session rows between tests."""
    yield
    from app.models.session import Session as SessionModel
    db = _TestSessionLocal()
    db.query(SessionModel).delete()
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

    mock_task = MagicMock()
    mock_result = MagicMock()
    mock_result.id = "celery-task-123"
    mock_task.delay.return_value = mock_result

    p1 = patch("app.api.main.lifespan", _noop_lifespan)
    p2 = patch("app.api.routes.sessions.run_pipeline_session", mock_task)
    p3 = patch("app.api.routes.sessions.init_db")
    p1.start()
    p2.start()
    p3.start()

    client = TestClient(app)
    return client, [p1, p2, p3]


@pytest.fixture()
def alice():
    client, patches = _build_app_with_user("alice")
    yield client
    client.close()
    for p in patches:
        p.stop()
    from app.api.main import app
    app.dependency_overrides.clear()


VALID_CONFIG = {
    "config": {
        "audience": "parents",
        "campaign_goal": "conversion",
        "ad_count": 50,
    }
}


def _create(client, config=None):
    return client.post("/sessions", json=config or VALID_CONFIG)


# --- Create ---


def test_create_session_valid_config(alice):
    resp = _create(alice)
    assert resp.status_code == 201
    data = resp.json()
    assert data["session_id"].startswith("sess_")
    assert data["user_id"] == "alice"
    assert data["config"]["audience"] == "parents"
    assert data["name"] is not None


def test_create_session_with_custom_name(alice):
    resp = alice.post("/sessions", json={
        "name": "My Custom Session",
        "config": {"audience": "students", "campaign_goal": "awareness"},
    })
    assert resp.status_code == 201
    assert resp.json()["name"] == "My Custom Session"


def test_create_session_invalid_audience_returns_422(alice):
    resp = alice.post("/sessions", json={
        "config": {"audience": "dogs", "campaign_goal": "conversion"},
    })
    assert resp.status_code == 422


def test_create_session_missing_required_returns_422(alice):
    resp = alice.post("/sessions", json={"config": {}})
    assert resp.status_code == 422


def test_create_session_ad_count_out_of_range_returns_422(alice):
    resp = alice.post("/sessions", json={
        "config": {"audience": "parents", "campaign_goal": "conversion", "ad_count": 999},
    })
    assert resp.status_code == 422


# --- Per-user isolation ---


def test_list_sessions_only_own():
    """Alice's sessions are not visible to Bob."""
    # Create sessions as alice
    client_a, patches_a = _build_app_with_user("alice")
    _create(client_a)
    _create(client_a)
    client_a.close()
    for p in patches_a:
        p.stop()

    from app.api.main import app
    app.dependency_overrides.clear()

    # Create session as bob
    client_b, patches_b = _build_app_with_user("bob")
    _create(client_b)

    # Bob sees only 1
    resp_bob = client_b.get("/sessions")
    assert resp_bob.json()["total"] == 1
    client_b.close()
    for p in patches_b:
        p.stop()
    app.dependency_overrides.clear()

    # Alice sees only 2
    client_a2, patches_a2 = _build_app_with_user("alice")
    resp_alice = client_a2.get("/sessions")
    assert resp_alice.json()["total"] == 2
    client_a2.close()
    for p in patches_a2:
        p.stop()
    app.dependency_overrides.clear()


# --- Filters ---


def test_list_sessions_filter_by_status(alice):
    _create(alice)

    resp = alice.get("/sessions?status=completed")
    assert resp.json()["total"] == 0

    resp = alice.get("/sessions?status=pending")
    assert resp.json()["total"] == 1


def test_list_sessions_includes_ad_preview(alice):
    create_resp = _create(alice)
    sid = create_resp.json()["session_id"]

    from app.models.session import Session as SessionModel
    db = _TestSessionLocal()
    row = db.query(SessionModel).filter(SessionModel.session_id == sid).first()
    assert row is not None
    row.results_summary = {"ads_generated": 1, "ads_published": 1, "avg_score": 7.4}
    db.commit()
    db.close()

    with patch("app.api.routes.sessions._get_session_ad_preview", return_value={
        "ad_id": "ad_001",
        "image_url": "/images/ad_001.png",
        "primary_text": "Preview copy",
        "headline": "Preview headline",
        "cta_button": "Learn More",
        "status": "published",
        "aggregate_score": 7.4,
    }):
        resp = alice.get("/sessions")

    assert resp.status_code == 200
    session = resp.json()["sessions"][0]
    assert session["results_summary"]["ads_generated"] == 1
    assert session["ad_preview"]["headline"] == "Preview headline"
    assert session["ad_preview"]["image_url"] == "/images/ad_001.png"


# --- Pagination ---


def test_list_sessions_pagination(alice):
    for _ in range(5):
        _create(alice)

    resp = alice.get("/sessions?offset=0&limit=2")
    data = resp.json()
    assert len(data["sessions"]) == 2
    assert data["total"] == 5
    assert data["offset"] == 0
    assert data["limit"] == 2

    resp2 = alice.get("/sessions?offset=2&limit=2")
    assert len(resp2.json()["sessions"]) == 2


# --- Get ---


def test_get_session_own(alice):
    create_resp = _create(alice)
    sid = create_resp.json()["session_id"]

    resp = alice.get(f"/sessions/{sid}")
    assert resp.status_code == 200
    assert resp.json()["session_id"] == sid


def test_get_session_other_user_returns_404():
    """Bob cannot see Alice's session."""
    client_a, patches_a = _build_app_with_user("alice")
    create_resp = _create(client_a)
    sid = create_resp.json()["session_id"]
    client_a.close()
    for p in patches_a:
        p.stop()

    from app.api.main import app
    app.dependency_overrides.clear()

    client_b, patches_b = _build_app_with_user("bob")
    resp = client_b.get(f"/sessions/{sid}")
    assert resp.status_code == 404
    client_b.close()
    for p in patches_b:
        p.stop()
    app.dependency_overrides.clear()


# --- Update ---


def test_update_session_name_own(alice):
    create_resp = _create(alice)
    sid = create_resp.json()["session_id"]

    resp = alice.patch(f"/sessions/{sid}", json={"name": "Renamed Session"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed Session"

    get_resp = alice.get(f"/sessions/{sid}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Renamed Session"


def test_update_session_name_blank_returns_400(alice):
    create_resp = _create(alice)
    sid = create_resp.json()["session_id"]

    resp = alice.patch(f"/sessions/{sid}", json={"name": "   "})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Session name cannot be empty"


# --- Delete ---


def test_delete_session_own(alice):
    create_resp = _create(alice)
    sid = create_resp.json()["session_id"]

    resp = alice.delete(f"/sessions/{sid}")
    assert resp.status_code == 204

    resp2 = alice.get(f"/sessions/{sid}")
    assert resp2.status_code == 404


def test_delete_session_other_user_returns_404():
    """Bob cannot delete Alice's session."""
    client_a, patches_a = _build_app_with_user("alice")
    create_resp = _create(client_a)
    sid = create_resp.json()["session_id"]
    client_a.close()
    for p in patches_a:
        p.stop()

    from app.api.main import app
    app.dependency_overrides.clear()

    client_b, patches_b = _build_app_with_user("bob")
    resp = client_b.delete(f"/sessions/{sid}")
    assert resp.status_code == 404
    client_b.close()
    for p in patches_b:
        p.stop()
    app.dependency_overrides.clear()

    # Still exists for alice
    client_a2, patches_a2 = _build_app_with_user("alice")
    resp2 = client_a2.get(f"/sessions/{sid}")
    assert resp2.status_code == 200
    client_a2.close()
    for p in patches_a2:
        p.stop()
    app.dependency_overrides.clear()


# --- PC-00: SessionType + video fields ---


def test_session_type_defaults_to_image(alice):
    """Sessions without session_type default to 'image' (backward compatible)."""
    resp = _create(alice)
    assert resp.status_code == 201
    assert resp.json()["config"]["session_type"] == "image"


def test_create_video_session(alice):
    resp = alice.post("/sessions", json={
        "config": {
            "session_type": "video",
            "audience": "students",
            "campaign_goal": "awareness",
            "video_count": 5,
            "video_duration": 5,
            "video_audio_mode": "with_audio",
            "video_aspect_ratio": "16:9",
        },
    })
    assert resp.status_code == 201
    cfg = resp.json()["config"]
    assert cfg["session_type"] == "video"
    assert cfg["video_count"] == 5
    assert cfg["video_duration"] == 5
    assert cfg["video_audio_mode"] == "with_audio"
    assert cfg["video_aspect_ratio"] == "16:9"


def test_video_count_out_of_range_returns_422(alice):
    resp = alice.post("/sessions", json={
        "config": {
            "session_type": "video",
            "audience": "parents",
            "campaign_goal": "conversion",
            "video_count": 25,
        },
    })
    assert resp.status_code == 422


def test_video_duration_out_of_range_returns_422(alice):
    resp = alice.post("/sessions", json={
        "config": {
            "session_type": "video",
            "audience": "parents",
            "campaign_goal": "conversion",
            "video_duration": 30,
        },
    })
    assert resp.status_code == 422


def test_invalid_session_type_returns_422(alice):
    resp = alice.post("/sessions", json={
        "config": {
            "session_type": "audio",
            "audience": "parents",
            "campaign_goal": "conversion",
        },
    })
    assert resp.status_code == 422


def test_image_session_ignores_video_fields(alice):
    """Image sessions accept video fields but they're just defaults."""
    resp = alice.post("/sessions", json={
        "config": {
            "session_type": "image",
            "audience": "parents",
            "campaign_goal": "conversion",
            "ad_count": 10,
        },
    })
    assert resp.status_code == 201
    cfg = resp.json()["config"]
    assert cfg["session_type"] == "image"
    assert cfg["video_count"] == 3
    assert cfg["ad_count"] == 10


def test_video_advanced_fields_default_empty(alice):
    """Advanced video fields default to empty strings."""
    resp = alice.post("/sessions", json={
        "config": {
            "session_type": "video",
            "audience": "students",
            "campaign_goal": "conversion",
        },
    })
    assert resp.status_code == 201
    cfg = resp.json()["config"]
    assert cfg["video_scene"] == ""
    assert cfg["video_visual_style"] == ""
    assert cfg["video_camera_movement"] == ""
    assert cfg["video_negative_prompt"] == ""


def test_video_session_with_advanced_fields(alice):
    resp = alice.post("/sessions", json={
        "config": {
            "session_type": "video",
            "audience": "parents",
            "campaign_goal": "awareness",
            "video_scene": "Parent and student celebrating",
            "video_visual_style": "UGC realistic",
            "video_camera_movement": "handheld",
            "video_negative_prompt": "no text, no logos",
        },
    })
    assert resp.status_code == 201
    cfg = resp.json()["config"]
    assert cfg["video_scene"] == "Parent and student celebrating"
    assert cfg["video_camera_movement"] == "handheld"
