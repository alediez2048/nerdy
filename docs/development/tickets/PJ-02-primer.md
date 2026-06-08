# PJ-02 Primer

**Source plan:** [`PJ-00-phase-plan.md`](PJ-00-phase-plan.md) — §9 (Asset upload + vision pass) and §13.
**For:** New Cursor Agent session
**Date:** 2026-06-08
**Previous work:** PJ-01 (DB models) merged. See `docs/development/DEVLOG.md`.
**Status:** ⏳ Not started

---

# Ticket PJ-02: Brand assets API + storage

## What Is This Ticket?

Wires the `brand_assets` table from PJ-01 to a working upload/serve API. Users (and downstream the agent) need to drop a logo, style guide PDF, or reference image into the chat and have it persisted on the Railway volume under a per-user prefix, with metadata recorded in Postgres. This ticket ships the two endpoints (`POST /api/brand-assets` for upload, `GET /api/brand-assets/{id}` for serving) and the storage helper that enforces path-traversal safety and per-user scoping.

It does NOT run the vision pass — that's PJ-03. PJ-02 is the file-handling and metadata layer.

### Why It Matters

- PJ-03 (vision pass) needs an asset to probe; without storage there's nothing to read.
- PJ-07 (chat UI) needs an upload endpoint for the file-drop zone.
- Mirrors the `app/api/routes/user_keys.py` route pattern — auth-gated, per-user scoped, no leakage across tenants.

---

## What Was Already Done

- **PJ-01** — `BrandAsset` SQLAlchemy model, `brand_assets` table, `ix_brand_assets_user` index.
- `app/api/routes/user_keys.py` — auth-gated CRUD pattern keyed on `user_id` from Clerk JWT. Re-use the auth dependency.
- Railway volume mounted at `output/` (already used by `output/images/`, `output/videos/`).

---

## What This Ticket Must Accomplish

### Goal

Ship `POST /api/brand-assets` (multipart upload) and `GET /api/brand-assets/{id}` (auth-gated file serve) with per-user storage under `output/brand_assets/<user_id>/<uuid>.<ext>` and path-traversal guard.

### Deliverables Checklist

#### A. Implementation

- [ ] `app/api/routes/brand_assets.py` — FastAPI router with both endpoints.
- [ ] `app/api/brand_asset_storage.py` — helper that builds the canonical storage path, validates extension, enforces per-user prefix, returns `(asset_id, storage_path)`.
- [ ] Register the router in `app/main.py` (or wherever existing routers register).
- [ ] Accepted MIME types: `image/png`, `image/jpeg`, `image/svg+xml`, `application/pdf`. Reject others with 400.
- [ ] Size limit: 10 MB. Reject larger with 413.
- [ ] `asset_type` form field validated against `{logo, style_guide, font, reference, other}`.
- [ ] `GET` endpoint validates the asset belongs to `current_user_id` before serving; 404 (not 403) on miss to avoid leaking existence.

#### B. Tests (`tests/test_api/test_brand_assets.py`)

- [ ] TDD first.
- [ ] `test_upload_logo_persists_file_and_row` — POST a tiny PNG, assert file exists on disk + row in DB.
- [ ] `test_upload_rejects_unknown_mime` — POST a `.exe` payload → 400.
- [ ] `test_upload_rejects_oversized` — POST 11 MB payload → 413.
- [ ] `test_get_returns_own_asset` — upload then GET → file bytes returned.
- [ ] `test_get_other_users_asset_returns_404` — user A uploads, user B GETs → 404.
- [ ] `test_path_traversal_in_filename_rejected` — POST with `original_filename="../../etc/passwd"` → file lands under per-user prefix regardless.

#### C. Integration Expectations

- [ ] Auth dep mirrors `user_keys.py`: extract `user_id` from verified Clerk JWT.
- [ ] Storage path is `output/brand_assets/<user_id>/<uuid>.<ext>` — never reads `original_filename` for path construction.
- [ ] DB writes use the `BrandAsset` model from PJ-01.
- [ ] Returns `{asset_id: uuid, storage_path: relative_path}` on success.

#### D. Documentation

- [ ] DEVLOG entry: `## 2026-XX-YY — PJ-02: Brand assets API + storage (✅)`.

---

## Branch & Merge Workflow

```bash
git switch final-submission && git pull
git switch -c feature/PJ-02-brand-assets-api
# implement, run tests
git add app/api/routes/brand_assets.py app/api/brand_asset_storage.py app/main.py tests/test_api/
git commit -m "feat(PJ-02): brand assets upload + serve endpoints"
git push -u origin feature/PJ-02-brand-assets-api
```

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `app/api/routes/brand_assets.py` | The two endpoints |
| `app/api/brand_asset_storage.py` | Path construction + traversal guard |
| `tests/test_api/test_brand_assets.py` | Upload/serve/scoping tests |

### Files to Modify

| File | Action |
|------|--------|
| `app/main.py` (or `app/api/__init__.py`) | Register the new router |

### Files to NOT Modify

- `app/models/brand_asset.py` — shipped in PJ-01, frozen here.
- `app/api/routes/user_keys.py` — read-only pattern reference.

### Files to READ for Context

| File | Why |
|------|-----|
| `app/api/routes/user_keys.py` | Auth-gated, per-user CRUD route pattern |
| `app/api/key_crypto.py` | (Not a direct reuse — this is a no-encryption model — but read for the auth-dep flow) |
| `docs/development/tickets/PJ-00-phase-plan.md` §9 | Upload flow, storage path, vision pass deferred to PJ-03 |

---

## Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Files on Railway volume | PJ-00 §9.3 | Same volume as `output/images/`, `output/videos/`; metadata in Postgres |
| UUID filenames, never user-supplied | PJ-00 §9.3 | Path traversal guard is "we never use the input filename for the path" |
| Auth gate on serve | PJ-00 §9.3 | Clerk JWT verified, scoped to user; 404 on miss |
| Vision pass is async | PJ-00 §3 decision 14 (GRILL Q4) | Upload is sync; vision extraction kicked off separately in PJ-03 |

---

## Suggested Implementation Pattern

```python
# app/api/brand_asset_storage.py
from pathlib import Path
from uuid import uuid4

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".pdf"}
STORAGE_ROOT = Path("output/brand_assets")

def build_storage_path(user_id: str, original_filename: str) -> tuple[str, Path]:
    """
    Returns (asset_id, absolute_path). Filename is ignored except to derive ext.
    """
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"unsupported extension: {ext}")
    asset_id = str(uuid4())
    rel = STORAGE_ROOT / user_id / f"{asset_id}{ext}"
    rel.parent.mkdir(parents=True, exist_ok=True)
    return asset_id, rel
```

```python
# app/api/routes/brand_assets.py
from fastapi import APIRouter, UploadFile, Form, Depends, HTTPException
from app.auth import get_current_user_id
from app.db import get_session
from app.models.brand_asset import BrandAsset
from app.api.brand_asset_storage import build_storage_path

router = APIRouter(prefix="/api/brand-assets", tags=["brand-assets"])
MAX_BYTES = 10 * 1024 * 1024

@router.post("")
async def upload_asset(
    file: UploadFile,
    asset_type: str = Form(...),
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_session),
):
    body = await file.read()
    if len(body) > MAX_BYTES:
        raise HTTPException(413, "file exceeds 10 MB")
    if asset_type not in {"logo", "style_guide", "font", "reference", "other"}:
        raise HTTPException(400, "invalid asset_type")
    try:
        asset_id, abs_path = build_storage_path(user_id, file.filename or "f.bin")
    except ValueError as e:
        raise HTTPException(400, str(e))
    abs_path.write_bytes(body)
    row = BrandAsset(
        id=asset_id,
        user_id=user_id,
        asset_type=asset_type,
        original_filename=file.filename,
        storage_path=str(abs_path.relative_to("output")),
        mime_type=file.content_type,
        size_bytes=len(body),
    )
    db.add(row); db.commit()
    return {"asset_id": asset_id, "storage_path": row.storage_path}


@router.get("/{asset_id}")
def get_asset(asset_id: str, user_id: str = Depends(get_current_user_id), db = Depends(get_session)):
    row = db.query(BrandAsset).filter_by(id=asset_id, user_id=user_id).one_or_none()
    if not row:
        raise HTTPException(404)
    from fastapi.responses import FileResponse
    return FileResponse(f"output/{row.storage_path}", media_type=row.mime_type)
```

---

## Edge Cases to Handle

1. Missing `file.filename` → fall back to a default `f.bin` and rely on `asset_type` + MIME validation.
2. Disk-full at write time → 500 with a clear log; do not leave half-written rows.
3. Asset row inserted but file write fails (or vice versa) → transactional ordering: write file first, then row; on row-insert failure, delete the file.
4. SVG with embedded scripts — accepted as-is for v1 (logos only). Note in DEVLOG for follow-up.
5. PDF over 10 MB — common for style guides. Reject for v1; document the limit on the chat UI prompt in PJ-07.
6. Concurrent uploads from the same user — UUIDs prevent collision.

---

## Definition of Done

- [ ] Both endpoints respond correctly to all six test cases.
- [ ] Files land under `output/brand_assets/<user_id>/` with UUID names.
- [ ] User A cannot GET user B's asset (404).
- [ ] `ruff check .` clean.
- [ ] `pytest tests/test_api/test_brand_assets.py -v` green.
- [ ] DEVLOG entry prepended.
- [ ] Feature branch pushed.

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Read `user_keys.py` route pattern | 20 min |
| Write storage helper | 30 min |
| Write router + endpoints | 90 min |
| Write tests | 90 min |
| Manual curl smoke against docker-compose | 30 min |
| DEVLOG + commit | 15 min |
| **Total** | **~1 day** |

---

## After This Ticket: What Comes Next

- **PJ-03** — Vision pass module (probes the assets uploaded here)
- **PJ-07** — Chat UI file-drop zone POSTs to this endpoint
