# Ad-Ops-Autopilot — Brand assets upload + serve (PJ-02)
"""Two endpoints: upload a brand asset, fetch one back.

POST /api/brand-assets       — multipart upload, returns asset_id + storage_path
GET  /api/brand-assets/{id}  — auth-scoped file serve

Vision-pass extraction is NOT triggered here. PJ-03's Celery task does
that; this ticket only persists bytes + metadata.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as SASession

from app.api.brand_asset_storage import (
    ALLOWED_MIMES,
    ASSET_TYPES,
    MAX_BYTES,
    UnsupportedExtension,
    build_storage_path,
    resolve_for_serve,
)
from app.api.deps import get_current_user
from app.db import get_db, init_db
from app.models.brand_asset import BrandAsset

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("")
async def upload_asset(
    db: Annotated[SASession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    asset_type: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
) -> dict:
    """Accept one file, persist to disk + DB, return its id."""
    init_db()

    if asset_type not in ASSET_TYPES:
        raise HTTPException(status_code=400, detail=f"invalid asset_type: {asset_type}")

    body = await file.read()
    if len(body) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="file exceeds 10 MB")

    if file.content_type and file.content_type not in ALLOWED_MIMES:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported mime type: {file.content_type}",
        )

    try:
        asset_id, abs_path = build_storage_path(
            user["user_id"], file.filename or "f.bin"
        )
    except UnsupportedExtension as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # File-then-row ordering: if the row insert fails we delete the file
    # so we never have an orphaned DB pointer to a missing file. The
    # converse — orphaned file with no row — is acceptable; nothing can
    # reach it because IDs are UUIDs and never enumerated.
    abs_path.write_bytes(body)
    try:
        # storage_path stored as "<user_id>/<uuid>.<ext>" (relative to output/brand_assets/)
        rel_storage = str(abs_path.relative_to(abs_path.parents[1]))
        row = BrandAsset(
            id=asset_id,
            user_id=user["user_id"],
            asset_type=asset_type,
            original_filename=file.filename,
            storage_path=rel_storage,
            mime_type=file.content_type,
            size_bytes=len(body),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    except Exception:
        try:
            abs_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("failed to clean up file after row insert error: %s", abs_path)
        raise

    return {"asset_id": row.id, "storage_path": row.storage_path}


@router.get("/{asset_id}")
def get_asset(
    asset_id: str,
    db: Annotated[SASession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> FileResponse:
    """Serve a previously-uploaded asset, scoped to the current user.

    Returns 404 (not 403) on miss to avoid leaking the existence of
    other users' assets.
    """
    init_db()
    row = (
        db.query(BrandAsset)
        .filter(BrandAsset.id == asset_id, BrandAsset.user_id == user["user_id"])
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="asset not found")

    try:
        abs_path = resolve_for_serve(user["user_id"], row.storage_path)
    except PermissionError as e:
        logger.error(
            "asset %s storage_path %r escapes user prefix",
            asset_id, row.storage_path,
        )
        raise HTTPException(status_code=404, detail="asset not found") from e

    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="asset file missing")

    return FileResponse(abs_path, media_type=row.mime_type or "application/octet-stream")
