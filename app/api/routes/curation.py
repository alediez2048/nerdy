# Ad-Ops-Autopilot — Curation CRUD + export (PA-10)
import csv
import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas.curation import (
    BatchReorder,
    CuratedAdAdd,
    CuratedAdUpdate,
    CuratedSetCreate,
    CuratedSetResponse,
)
from app.db import get_db, init_db
from app.models.curation import CuratedAd, CuratedSet
from app.models.session import Session as SessionModel

router = APIRouter()


def _get_user_session(db: Session, session_id: str, user_id: str) -> SessionModel:
    row = db.query(SessionModel).filter(
        SessionModel.session_id == session_id,
        SessionModel.user_id == user_id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return row


def _get_or_create_set(db: Session, session_row: SessionModel) -> CuratedSet:
    cs = db.query(CuratedSet).filter(CuratedSet.session_id == session_row.id).first()
    if not cs:
        cs = CuratedSet(session_id=session_row.id, name="Default Set")
        db.add(cs)
        db.commit()
        db.refresh(cs)
    return cs


@router.post("/{session_id}/curated", response_model=CuratedSetResponse)
def create_curated_set(
    session_id: str,
    body: CuratedSetCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> CuratedSet:
    init_db()
    session_row = _get_user_session(db, session_id, user["user_id"])
    existing = db.query(CuratedSet).filter(CuratedSet.session_id == session_row.id).first()
    if existing:
        return existing
    cs = CuratedSet(session_id=session_row.id, name=body.name)
    db.add(cs)
    db.commit()
    db.refresh(cs)
    return cs


@router.get("/{session_id}/curated", response_model=CuratedSetResponse)
def get_curated_set(
    session_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> CuratedSet:
    init_db()
    session_row = _get_user_session(db, session_id, user["user_id"])
    cs = db.query(CuratedSet).filter(CuratedSet.session_id == session_row.id).first()
    if not cs:
        raise HTTPException(status_code=404, detail="No curated set found")
    return cs


@router.post("/{session_id}/curated/ads", status_code=201)
def add_curated_ad(
    session_id: str,
    body: CuratedAdAdd,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    init_db()
    session_row = _get_user_session(db, session_id, user["user_id"])
    cs = _get_or_create_set(db, session_row)

    # Check duplicate
    existing = db.query(CuratedAd).filter(
        CuratedAd.curated_set_id == cs.id, CuratedAd.ad_id == body.ad_id
    ).first()
    if existing:
        return {"ad_id": body.ad_id, "status": "already_exists"}

    ad = CuratedAd(
        curated_set_id=cs.id,
        ad_id=body.ad_id,
        position=body.position or (len(cs.ads) + 1),
    )
    db.add(ad)
    db.commit()
    return {"ad_id": body.ad_id, "status": "added", "position": ad.position}


@router.delete("/{session_id}/curated/ads/{ad_id}", status_code=204)
def remove_curated_ad(
    session_id: str,
    ad_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    init_db()
    session_row = _get_user_session(db, session_id, user["user_id"])
    cs = db.query(CuratedSet).filter(CuratedSet.session_id == session_row.id).first()
    if not cs:
        raise HTTPException(status_code=404, detail="No curated set")
    ad = db.query(CuratedAd).filter(
        CuratedAd.curated_set_id == cs.id, CuratedAd.ad_id == ad_id
    ).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not in curated set")
    db.delete(ad)
    db.commit()


@router.patch("/{session_id}/curated/ads/{ad_id}")
def update_curated_ad(
    session_id: str,
    ad_id: str,
    body: CuratedAdUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    init_db()
    session_row = _get_user_session(db, session_id, user["user_id"])
    cs = db.query(CuratedSet).filter(CuratedSet.session_id == session_row.id).first()
    if not cs:
        raise HTTPException(status_code=404, detail="No curated set")
    ad = db.query(CuratedAd).filter(
        CuratedAd.curated_set_id == cs.id, CuratedAd.ad_id == ad_id
    ).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not in curated set")

    if body.position is not None:
        ad.position = body.position
    if body.annotation is not None:
        ad.annotation = body.annotation
    if body.edited_copy is not None:
        ad.edited_copy = body.edited_copy

    db.commit()
    db.refresh(ad)
    return {
        "ad_id": ad.ad_id,
        "position": ad.position,
        "annotation": ad.annotation,
        "edited_copy": ad.edited_copy,
    }


@router.post("/{session_id}/curated/reorder")
def batch_reorder(
    session_id: str,
    body: BatchReorder,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, str]:
    init_db()
    session_row = _get_user_session(db, session_id, user["user_id"])
    cs = db.query(CuratedSet).filter(CuratedSet.session_id == session_row.id).first()
    if not cs:
        raise HTTPException(status_code=404, detail="No curated set")

    for i, aid in enumerate(body.ad_ids, 1):
        ad = db.query(CuratedAd).filter(
            CuratedAd.curated_set_id == cs.id, CuratedAd.ad_id == aid
        ).first()
        if ad:
            ad.position = i

    db.commit()
    return {"status": "reordered"}


@router.get("/{session_id}/curated/export")
def export_curated_zip(
    session_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    """Export curated set as Meta-ready ZIP."""
    init_db()
    session_row = _get_user_session(db, session_id, user["user_id"])
    cs = db.query(CuratedSet).filter(CuratedSet.session_id == session_row.id).first()
    if not cs or not cs.ads:
        raise HTTPException(status_code=404, detail="No curated ads to export")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Summary
        summary = {
            "total_ads": len(cs.ads),
            "curated_set_name": cs.name,
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        zf.writestr("curated_export/summary.json", json.dumps(summary, indent=2))

        # Manifest CSV
        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(["position", "ad_id", "annotation", "has_edits"])
        for ad in cs.ads:
            writer.writerow([ad.position, ad.ad_id, ad.annotation or "", bool(ad.edited_copy)])
        zf.writestr("curated_export/manifest.csv", csv_buf.getvalue())

        # Per-ad folders
        for ad in cs.ads:
            prefix = f"curated_export/ads/{ad.position:02d}_{ad.ad_id}/"
            copy_data = ad.edited_copy or {}
            zf.writestr(prefix + "copy.json", json.dumps(copy_data, indent=2))
            metadata = {
                "ad_id": ad.ad_id,
                "position": ad.position,
                "annotation": ad.annotation,
                "has_edits": bool(ad.edited_copy),
            }
            zf.writestr(prefix + "metadata.json", json.dumps(metadata, indent=2))

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=curated_{session_id}.zip"},
    )
