# PJ-03: Vision pass module + Celery task + extract endpoints
"""Hermetic tests — Gemini calls are stubbed via patch.

The probe functions wrap a single private call ``_call_multimodal``;
patching that one entry point gives us full control over the "Gemini
response" without touching the network. The Celery task is invoked as
a plain Python function (its body has been factored into
``_run_vision``) so we don't need a broker for tests.
"""
import json
import tempfile
from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db  # noqa: F401 (registers models)
from app.api import vision
from app.models.base import Base
from app.models.brand_asset import BrandAsset


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


_USER = {"user_id": "alice", "email": "alice@nerdy.com", "name": "Alice"}


def _override_user():
    return _USER


@pytest.fixture(autouse=True)
def _clean_db():
    yield
    db = _TestSession()
    db.query(BrandAsset).delete()
    db.commit()
    db.close()


@pytest.fixture()
def asset(tmp_path):
    """Seed a brand_asset row with a real file on disk under a patched
    STORAGE_ROOT so the task can read bytes back."""
    fake_root = tmp_path / "brand_assets"
    user_dir = fake_root / "alice"
    user_dir.mkdir(parents=True)
    asset_id = "test-asset-0001"
    rel = f"alice/{asset_id}.png"
    abs_path = user_dir / f"{asset_id}.png"
    abs_path.write_bytes(b"fake-png-bytes-here")

    db = _TestSession()
    row = BrandAsset(
        id=asset_id,
        user_id="alice",
        asset_type="logo",
        original_filename="logo.png",
        storage_path=rel,
        mime_type="image/png",
        size_bytes=19,
    )
    db.add(row)
    db.commit()
    db.close()

    with (
        patch("app.api.brand_asset_storage.STORAGE_ROOT", fake_root),
        patch("app.workers.tasks.brand_asset_vision_task.STORAGE_ROOT", fake_root),
        # The task body opens its own SessionLocal — point it at the
        # test SQLite engine so it sees the seeded row.
        patch("app.workers.tasks.brand_asset_vision_task.SessionLocal", _TestSession),
        patch("app.workers.tasks.brand_asset_vision_task.init_db"),
    ):
        yield {"asset_id": asset_id, "storage_root": fake_root}


@pytest.fixture()
def client(asset):
    from app.api.deps import get_current_user
    from app.api.main import app
    from app.db import get_db

    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_user
    with (
        patch("app.api.main.lifespan", _noop_lifespan),
        patch("app.api.routes.brand_assets.init_db"),
    ):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


# --- Probe-function tests -------------------------------------------------


def test_probe_logo_returns_structured_facts():
    """Stubbed Gemini returns logo JSON → probe parses it."""
    fake = json.dumps({
        "dominant_colors": ["#0a3d62", "#fafafa", "#e2a517"],
        "background": "transparent",
        "detected_fonts": [{"family": "Inter", "confidence": 0.85}],
        "notes": "Wordmark with stylized graduation cap.",
    })
    with patch.object(vision, "_call_multimodal", return_value=fake):
        out = vision.probe_logo(b"png-bytes", "image/png")
    assert out["dominant_colors"][0] == "#0a3d62"
    assert out["background"] == "transparent"
    assert out["detected_fonts"][0]["family"] == "Inter"


def test_probe_logo_handles_fenced_json():
    """A ```json … ``` wrapper is stripped."""
    fenced = '```json\n{"dominant_colors": ["#000000"], "background": "solid", "detected_fonts": [], "notes": "x"}\n```'
    with patch.object(vision, "_call_multimodal", return_value=fenced):
        out = vision.probe_logo(b"png", "image/png")
    assert out["dominant_colors"] == ["#000000"]


def test_probe_style_guide_extracts_facts():
    """Stubbed style-guide JSON → palette, fonts, do/dont."""
    fake = json.dumps({
        "palette_hex": ["#0a3d62", "#fafafa"],
        "font_names": ["Inter", "Source Sans Pro"],
        "do_dont_rules": {
            "do": ["use teal as primary"],
            "dont": ["use stock-photo handshakes"],
        },
        "ocr_text_excerpt": "Acme Brand Guidelines v2.1...",
    })
    with patch.object(vision, "_call_multimodal", return_value=fake):
        out = vision.probe_style_guide(b"pdf-bytes")
    assert out["palette_hex"] == ["#0a3d62", "#fafafa"]
    assert "Inter" in out["font_names"]
    assert "use teal as primary" in out["do_dont_rules"]["do"]


def test_probe_returns_raw_on_unparseable_json():
    """Non-JSON model output is preserved under ``raw`` so we don't lose it."""
    with patch.object(vision, "_call_multimodal", return_value="this is not JSON"):
        out = vision.probe_logo(b"x", "image/png")
    assert "raw" in out
    assert out["raw"] == "this is not JSON"


def test_probe_font_falls_back_to_filename_on_error():
    """When Gemini fails, font_family is inferred from the filename."""
    with patch.object(vision, "_call_multimodal", side_effect=RuntimeError("network")):
        out = vision.probe_font(b"font-bytes", "/path/to/Inter-Regular.ttf")
    assert out["font_family"] == "Inter-Regular"


# --- Task tests -----------------------------------------------------------


def test_task_persists_extracted_facts(asset):
    """Successful probe populates ``brand_assets.extracted_facts``."""
    from app.workers.tasks.brand_asset_vision_task import _run_vision

    fake = json.dumps({
        "dominant_colors": ["#0a3d62"],
        "background": "transparent",
        "detected_fonts": [],
        "notes": "minimal",
    })
    with patch.object(vision, "_call_multimodal", return_value=fake):
        facts = _run_vision(asset["asset_id"])

    assert facts["dominant_colors"] == ["#0a3d62"]
    db = _TestSession()
    row = db.query(BrandAsset).filter_by(id=asset["asset_id"]).one()
    assert row.extracted_facts["background"] == "transparent"
    db.close()


def test_task_handles_gemini_failure(asset):
    """Probe exception is captured as ``extracted_facts.error``."""
    from app.workers.tasks.brand_asset_vision_task import _run_vision

    with patch.object(vision, "_call_multimodal", side_effect=RuntimeError("quota")):
        facts = _run_vision(asset["asset_id"])

    assert "error" in facts
    assert "quota" in facts["error"]
    db = _TestSession()
    row = db.query(BrandAsset).filter_by(id=asset["asset_id"]).one()
    assert "error" in row.extracted_facts
    db.close()


def test_task_returns_error_for_unknown_asset():
    """Missing row → structured error, no exception."""
    from app.workers.tasks.brand_asset_vision_task import _run_vision

    out = _run_vision("does-not-exist")
    assert "error" in out
    assert "not found" in out["error"]


# --- Endpoint tests -------------------------------------------------------


def test_extract_endpoint_enqueues(client, asset):
    """POST returns 202 + task_id without running anything inline."""
    fake_task = MagicMock()
    fake_task.id = "celery-task-123"
    with patch(
        "app.workers.tasks.brand_asset_vision_task.run_vision_pass.delay",
        return_value=fake_task,
    ):
        resp = client.post(f"/api/brand-assets/{asset['asset_id']}/extract")
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "queued"
    assert body["task_id"] == "celery-task-123"


def test_extract_endpoint_404_for_unknown(client):
    """Unknown asset → 404."""
    resp = client.post("/api/brand-assets/no-such-id/extract")
    assert resp.status_code == 404


def test_status_returns_running_before_facts_set(client, asset):
    """No ``extracted_facts`` yet → ``running``."""
    resp = client.get(f"/api/brand-assets/{asset['asset_id']}/extract/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"


def test_status_returns_ready_when_done(client, asset):
    """Populated ``extracted_facts`` → ``ready`` + payload."""
    db = _TestSession()
    row = db.query(BrandAsset).filter_by(id=asset["asset_id"]).one()
    row.extracted_facts = {"dominant_colors": ["#abcdef"], "background": "solid"}
    db.commit()
    db.close()

    resp = client.get(f"/api/brand-assets/{asset['asset_id']}/extract/status")
    body = resp.json()
    assert body["status"] == "ready"
    assert body["extracted_facts"]["dominant_colors"] == ["#abcdef"]


def test_status_returns_failed_on_error_payload(client, asset):
    """``extracted_facts = {error: ...}`` → ``failed`` + error message."""
    db = _TestSession()
    row = db.query(BrandAsset).filter_by(id=asset["asset_id"]).one()
    row.extracted_facts = {"error": "quota exhausted"}
    db.commit()
    db.close()

    resp = client.get(f"/api/brand-assets/{asset['asset_id']}/extract/status")
    body = resp.json()
    assert body["status"] == "failed"
    assert body["error"] == "quota exhausted"


def test_status_cross_tenant_returns_404(client, asset):
    """User B can't poll user A's extract status."""
    from app.api.deps import get_current_user
    from app.api.main import app

    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": "mallory", "email": "m@nerdy.com", "name": "Mallory",
    }
    try:
        resp = client.get(f"/api/brand-assets/{asset['asset_id']}/extract/status")
    finally:
        app.dependency_overrides[get_current_user] = _override_user
    assert resp.status_code == 404
