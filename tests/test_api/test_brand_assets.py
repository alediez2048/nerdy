# PJ-02: Brand assets API tests
"""Upload + serve + per-user scoping for /api/brand-assets.

In-memory SQLite + a tmpdir patched in for STORAGE_ROOT keeps the tests
hermetic. ``app.dependency_overrides`` swaps the auth and DB deps the
same way ``test_curation.py`` does.
"""
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Force full model registration before create_all.
import app.db  # noqa: F401
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


# Two distinct users for cross-tenant tests.
_USER_ALICE = {"user_id": "alice", "email": "alice@nerdy.com", "name": "Alice"}
_USER_BOB = {"user_id": "bob", "email": "bob@nerdy.com", "name": "Bob"}

_current_user = {"v": _USER_ALICE}


def _override_user():
    return _current_user["v"]


@pytest.fixture(autouse=True)
def _clean_db():
    yield
    db = _TestSession()
    db.query(BrandAsset).delete()
    db.commit()
    db.close()


@pytest.fixture()
def storage_dir(tmp_path):
    """Patch STORAGE_ROOT so file writes land in a tmpdir, not the
    real Railway volume path."""
    fake_root = tmp_path / "brand_assets"
    fake_root.mkdir()
    with (
        patch("app.api.brand_asset_storage.STORAGE_ROOT", fake_root),
        patch("app.api.routes.brand_assets.resolve_for_serve") as resolve_mock,
    ):
        # The serve resolver needs to use the patched root too.
        def _resolve(user_id: str, storage_path: str) -> Path:
            requested = (fake_root / storage_path).resolve()
            user_root = (fake_root / user_id).resolve()
            requested_str = str(requested)
            user_root_str = str(user_root)
            if not (
                requested_str == user_root_str
                or requested_str.startswith(user_root_str + "/")
            ):
                raise PermissionError("escapes user prefix")
            return requested

        resolve_mock.side_effect = _resolve
        yield fake_root


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
        patch("app.api.routes.brand_assets.init_db"),
    ):
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()
    _current_user["v"] = _USER_ALICE


def _png_bytes(payload: bytes = b"") -> bytes:
    # Minimal 1x1 PNG with the magic header + body.
    header = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    )
    return header + payload


# --- Tests ---------------------------------------------------------


def test_upload_logo_persists_file_and_row(client, storage_dir):
    """A valid PNG upload writes the file + DB row."""
    payload = _png_bytes()
    resp = client.post(
        "/api/brand-assets",
        data={"asset_type": "logo"},
        files={"file": ("acme-logo.png", payload, "image/png")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "asset_id" in body
    assert body["storage_path"].startswith("alice/")
    assert body["storage_path"].endswith(".png")

    # File exists under the per-user prefix.
    written = storage_dir / body["storage_path"]
    assert written.exists()
    assert written.read_bytes() == payload

    # DB row reflects everything.
    db = _TestSession()
    row = db.query(BrandAsset).filter_by(id=body["asset_id"]).one()
    assert row.user_id == "alice"
    assert row.asset_type == "logo"
    assert row.original_filename == "acme-logo.png"
    assert row.mime_type == "image/png"
    assert row.size_bytes == len(payload)
    assert row.extracted_facts is None  # PJ-03 fills this later
    db.close()


def test_upload_rejects_unknown_mime(client, storage_dir):
    """An .exe upload is rejected at the extension or mime gate."""
    resp = client.post(
        "/api/brand-assets",
        data={"asset_type": "logo"},
        files={"file": ("bad.exe", b"MZ\x90\x00", "application/x-msdownload")},
    )
    assert resp.status_code == 400
    assert "unsupported" in resp.json()["detail"].lower()


def test_upload_rejects_oversized(client, storage_dir):
    """An 11 MB payload returns 413."""
    big = b"a" * (11 * 1024 * 1024)
    resp = client.post(
        "/api/brand-assets",
        data={"asset_type": "logo"},
        files={"file": ("huge.png", big, "image/png")},
    )
    assert resp.status_code == 413


def test_upload_rejects_invalid_asset_type(client, storage_dir):
    """asset_type outside the allowlist returns 400."""
    resp = client.post(
        "/api/brand-assets",
        data={"asset_type": "rogue"},
        files={"file": ("logo.png", _png_bytes(), "image/png")},
    )
    assert resp.status_code == 400
    assert "asset_type" in resp.json()["detail"]


def test_get_returns_own_asset(client, storage_dir):
    """Upload as alice, fetch as alice → bytes round-trip."""
    payload = _png_bytes(b"hello-bytes")
    up = client.post(
        "/api/brand-assets",
        data={"asset_type": "logo"},
        files={"file": ("a.png", payload, "image/png")},
    )
    asset_id = up.json()["asset_id"]

    resp = client.get(f"/api/brand-assets/{asset_id}")
    assert resp.status_code == 200
    assert resp.content == payload
    assert resp.headers["content-type"].startswith("image/png")


def test_get_other_users_asset_returns_404(client, storage_dir):
    """User B GETting user A's asset gets 404 — not 403 — to avoid existence leak."""
    payload = _png_bytes(b"alice-only")
    up = client.post(
        "/api/brand-assets",
        data={"asset_type": "logo"},
        files={"file": ("a.png", payload, "image/png")},
    )
    asset_id = up.json()["asset_id"]

    _current_user["v"] = _USER_BOB
    resp = client.get(f"/api/brand-assets/{asset_id}")
    assert resp.status_code == 404


def test_path_traversal_in_filename_rejected(client, storage_dir):
    """``original_filename`` with ../ is ignored — the on-disk path is
    always ``<user_id>/<uuid>.<ext>``."""
    payload = _png_bytes()
    resp = client.post(
        "/api/brand-assets",
        data={"asset_type": "logo"},
        files={"file": ("../../../etc/passwd.png", payload, "image/png")},
    )
    assert resp.status_code == 200
    storage_path = resp.json()["storage_path"]
    # Path must start with the user prefix and have a UUID-shaped name,
    # not anything that escapes the prefix.
    assert storage_path.startswith("alice/")
    assert ".." not in storage_path
    assert "etc/passwd" not in storage_path
    assert (storage_dir / storage_path).exists()
    # The original_filename is preserved verbatim in the row for display,
    # but it's never honored for the on-disk layout.
    db = _TestSession()
    row = db.query(BrandAsset).filter_by(id=resp.json()["asset_id"]).one()
    assert row.original_filename == "../../../etc/passwd.png"
    db.close()


def test_get_nonexistent_asset_returns_404(client, storage_dir):
    """A made-up asset id returns 404."""
    resp = client.get("/api/brand-assets/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
