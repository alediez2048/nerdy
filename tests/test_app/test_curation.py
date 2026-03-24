# PA-10: Curation API tests
"""Tests for curated set CRUD, reorder, annotation, edit tracking, and ZIP export."""

import io
import json
import tempfile
import zipfile
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
from app.models.session import Session as SessionModel
from app.models.curation import CuratedAd, CuratedSet


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


def _override_user():
    return {"user_id": "alice", "email": "alice@nerdy.com", "name": "Alice"}


@pytest.fixture(autouse=True)
def _clean():
    yield
    db = _TestSession()
    db.query(CuratedAd).delete()
    db.query(CuratedSet).delete()
    db.query(SessionModel).delete()
    db.commit()
    db.close()


def _seed_session(session_id: str = "sess_cur", user_id: str = "alice") -> str:
    db = _TestSession()
    row = SessionModel(
        session_id=session_id, user_id=user_id,
        config={"audience": "parents"}, status="completed",
    )
    db.add(row)
    db.commit()
    db.close()
    return session_id


@pytest.fixture()
def client():
    from app.api.main import app
    from app.api.deps import get_current_user
    from app.db import get_db

    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_user

    with (
        patch("app.api.main.lifespan", _noop_lifespan),
        patch("app.api.routes.curation.init_db"),
    ):
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()


# --- Create curated set ---


def test_create_curated_set(client):
    sid = _seed_session()
    resp = client.post(f"/api/sessions/{sid}/curated", json={"name": "Best Ads"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Best Ads"


def test_create_curated_set_idempotent(client):
    sid = _seed_session()
    client.post(f"/api/sessions/{sid}/curated", json={"name": "Set 1"})
    resp = client.post(f"/api/sessions/{sid}/curated", json={"name": "Set 2"})
    assert resp.json()["name"] == "Set 1"  # Returns existing


# --- Add ad ---


def test_add_ad_to_curated_set(client):
    sid = _seed_session()
    client.post(f"/api/sessions/{sid}/curated", json={})
    resp = client.post(f"/api/sessions/{sid}/curated/ads", json={"ad_id": "ad_001", "position": 1})
    assert resp.status_code == 201
    assert resp.json()["ad_id"] == "ad_001"


def test_add_duplicate_ad_returns_already_exists(client):
    sid = _seed_session()
    client.post(f"/api/sessions/{sid}/curated", json={})
    client.post(f"/api/sessions/{sid}/curated/ads", json={"ad_id": "ad_001"})
    resp = client.post(f"/api/sessions/{sid}/curated/ads", json={"ad_id": "ad_001"})
    assert resp.json()["status"] == "already_exists"


# --- Remove ad ---


def test_remove_ad_from_curated_set(client):
    sid = _seed_session()
    client.post(f"/api/sessions/{sid}/curated", json={})
    client.post(f"/api/sessions/{sid}/curated/ads", json={"ad_id": "ad_001"})
    resp = client.delete(f"/api/sessions/{sid}/curated/ads/ad_001")
    assert resp.status_code == 204

    # Verify removed
    get_resp = client.get(f"/api/sessions/{sid}/curated")
    assert len(get_resp.json()["ads"]) == 0


# --- Annotate ---


def test_annotate_ad(client):
    sid = _seed_session()
    client.post(f"/api/sessions/{sid}/curated", json={})
    client.post(f"/api/sessions/{sid}/curated/ads", json={"ad_id": "ad_002"})
    resp = client.patch(f"/api/sessions/{sid}/curated/ads/ad_002", json={
        "annotation": "Great hook, needs shorter CTA"
    })
    assert resp.json()["annotation"] == "Great hook, needs shorter CTA"


# --- Edit with diff tracking ---


def test_edit_ad_with_diff_tracking(client):
    sid = _seed_session()
    client.post(f"/api/sessions/{sid}/curated", json={})
    client.post(f"/api/sessions/{sid}/curated/ads", json={"ad_id": "ad_003"})
    resp = client.patch(f"/api/sessions/{sid}/curated/ads/ad_003", json={
        "edited_copy": {
            "primary_text": {"original": "Old text", "edited": "New text"},
        }
    })
    edited = resp.json()["edited_copy"]
    assert edited["primary_text"]["original"] == "Old text"
    assert edited["primary_text"]["edited"] == "New text"


# --- Reorder ---


def test_batch_reorder(client):
    sid = _seed_session()
    client.post(f"/api/sessions/{sid}/curated", json={})
    client.post(f"/api/sessions/{sid}/curated/ads", json={"ad_id": "ad_a", "position": 1})
    client.post(f"/api/sessions/{sid}/curated/ads", json={"ad_id": "ad_b", "position": 2})
    client.post(f"/api/sessions/{sid}/curated/ads", json={"ad_id": "ad_c", "position": 3})

    resp = client.post(f"/api/sessions/{sid}/curated/reorder", json={"ad_ids": ["ad_c", "ad_a", "ad_b"]})
    assert resp.json()["status"] == "reordered"

    get_resp = client.get(f"/api/sessions/{sid}/curated")
    ads = get_resp.json()["ads"]
    assert [a["ad_id"] for a in ads] == ["ad_c", "ad_a", "ad_b"]


# --- Per-user isolation ---


def test_other_user_cannot_access_curated_set(client):
    _seed_session("sess_bob", user_id="bob")
    resp = client.get("/api/sessions/sess_bob/curated")
    assert resp.status_code == 404


# --- ZIP export ---


def test_export_zip(client):
    sid = _seed_session()
    client.post(f"/api/sessions/{sid}/curated", json={})
    client.post(f"/api/sessions/{sid}/curated/ads", json={"ad_id": "ad_zip", "position": 1})
    client.patch(f"/api/sessions/{sid}/curated/ads/ad_zip", json={
        "edited_copy": {
            "primary_text": {"original": "Old copy", "edited": "New exported copy"},
        }
    })

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_image:
        tmp_image.write(b"fake-image-bytes")
        tmp_image.flush()
        image_path = tmp_image.name

    try:
        asset_map = {
            "ad_zip": {
                "ad_id": "ad_zip",
                "copy": {
                    "primary_text": "Old copy",
                    "headline": "Original headline",
                    "description": "Description text",
                    "cta_button": "Learn More",
                },
                "image_path": image_path,
                "status": "published",
                "aggregate_score": 7.8,
                "created_at": "2026-03-17T00:00:00+00:00",
            }
        }

        with patch("app.api.routes.curation._load_curated_ad_assets", return_value=asset_map):
            resp = client.get(f"/api/sessions/{sid}/curated/export")
    finally:
        import os
        os.unlink(image_path)

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"

    buf = io.BytesIO(resp.content)
    with zipfile.ZipFile(buf) as zf:
        names = zf.namelist()
        assert "curated_export/summary.json" in names
        assert "curated_export/manifest.csv" in names
        assert any("ad_zip" in n for n in names)
        assert "curated_export/ads/01_ad_zip/copy.json" in names
        assert "curated_export/ads/01_ad_zip/copy.txt" in names
        assert "curated_export/ads/01_ad_zip/original_copy.json" in names
        assert "curated_export/ads/01_ad_zip/edited_copy.json" in names
        assert "curated_export/ads/01_ad_zip/image.png" in names

        copy_json = json.loads(zf.read("curated_export/ads/01_ad_zip/copy.json"))
        assert copy_json["primary_text"] == "New exported copy"
        assert copy_json["headline"] == "Original headline"

        copy_txt = zf.read("curated_export/ads/01_ad_zip/copy.txt").decode()
        assert "New exported copy" in copy_txt
        assert "Original headline" in copy_txt

        summary = json.loads(zf.read("curated_export/summary.json"))
        assert summary["images_included"] == 1
