# Ad-Ops-Autopilot — Curation CRUD + export (PA-10)
import csv
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
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


def _curated_asset_sort_key(asset: dict[str, Any]) -> tuple[bool, bool, float, str]:
    """Prefer published, image-backed, higher-score, newer ad assets."""
    return (
        asset.get("status") == "published",
        bool(asset.get("image_path")),
        float(asset.get("aggregate_score", 0.0) or 0.0),
        str(asset.get("created_at", "")),
    )


def _load_curated_ad_assets(session_row: SessionModel) -> dict[str, dict[str, Any]]:
    """Load export-ready ad data for a session from the dashboard ad library."""
    ledger_path = session_row.ledger_path
    if not ledger_path or not Path(ledger_path).exists():
        return {}

    try:
        from iterate.ledger import read_events
        from output.export_dashboard import _build_ad_library

        library = _build_ad_library(read_events(ledger_path))
    except (ImportError, FileNotFoundError, OSError, ValueError, TypeError):
        return {}

    assets: dict[str, dict[str, Any]] = {}
    for item in library:
        ad_id = item.get("ad_id")
        if not isinstance(ad_id, str) or not ad_id:
            continue
        existing = assets.get(ad_id)
        if existing is None or _curated_asset_sort_key(item) > _curated_asset_sort_key(existing):
            assets[ad_id] = item
    return assets


def _resolve_export_copy(
    source_copy: dict[str, Any],
    edited_copy: dict[str, Any] | None,
) -> dict[str, str]:
    """Merge original ad copy with any curated edits into export-ready copy."""
    resolved: dict[str, str] = {
        key: value
        for key, value in source_copy.items()
        if isinstance(value, str) and value
    }
    if not edited_copy:
        return resolved

    for key, value in edited_copy.items():
        if isinstance(value, dict):
            edited_value = value.get("edited")
            original_value = value.get("original")
            if isinstance(edited_value, str) and edited_value:
                resolved[key] = edited_value
            elif key not in resolved and isinstance(original_value, str) and original_value:
                resolved[key] = original_value
        elif isinstance(value, str) and value:
            resolved[key] = value
    return resolved


def _render_copy_text(copy_data: dict[str, str]) -> str:
    """Create a human-readable copy export."""
    lines: list[str] = []
    for label, key in (
        ("Primary Text", "primary_text"),
        ("Headline", "headline"),
        ("Description", "description"),
        ("CTA Button", "cta_button"),
    ):
        value = copy_data.get(key, "")
        if value:
            lines.append(f"{label}:\n{value}")
    return "\n\n".join(lines)


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

    ad_assets = _load_curated_ad_assets(session_row)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Summary
        summary = {
            "total_ads": len(cs.ads),
            "curated_set_name": cs.name,
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "images_included": 0,
        }

        # Manifest CSV
        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow([
            "position",
            "ad_id",
            "annotation",
            "has_edits",
            "headline",
            "primary_text",
            "cta_button",
            "image_file",
        ])
        for ad in cs.ads:
            asset = ad_assets.get(ad.ad_id, {})
            source_copy = asset.get("copy", {}) if isinstance(asset.get("copy"), dict) else {}
            export_copy = _resolve_export_copy(source_copy, ad.edited_copy)
            image_path = asset.get("image_path")
            image_name = Path(image_path).name if isinstance(image_path, str) and image_path else ""
            writer.writerow([
                ad.position,
                ad.ad_id,
                ad.annotation or "",
                bool(ad.edited_copy),
                export_copy.get("headline", ""),
                export_copy.get("primary_text", ""),
                export_copy.get("cta_button", ""),
                image_name,
            ])
        zf.writestr("curated_export/manifest.csv", csv_buf.getvalue())

        for ad in cs.ads:
            prefix = f"curated_export/ads/{ad.position:02d}_{ad.ad_id}/"
            asset = ad_assets.get(ad.ad_id, {})
            source_copy = asset.get("copy", {}) if isinstance(asset.get("copy"), dict) else {}
            export_copy = _resolve_export_copy(source_copy, ad.edited_copy)
            zf.writestr(prefix + "copy.json", json.dumps(export_copy, indent=2))
            zf.writestr(prefix + "copy.txt", _render_copy_text(export_copy))
            if source_copy:
                zf.writestr(prefix + "original_copy.json", json.dumps(source_copy, indent=2))
            if ad.edited_copy:
                zf.writestr(prefix + "edited_copy.json", json.dumps(ad.edited_copy, indent=2))

            metadata = {
                "ad_id": ad.ad_id,
                "position": ad.position,
                "annotation": ad.annotation,
                "has_edits": bool(ad.edited_copy),
                "image_file": None,
            }

            image_path = asset.get("image_path")
            if isinstance(image_path, str) and image_path:
                image_file = Path(image_path)
                if image_file.exists() and image_file.is_file():
                    export_name = prefix + f"image{image_file.suffix.lower() or '.png'}"
                    zf.write(image_file, export_name)
                    metadata["image_file"] = Path(export_name).name
                    summary["images_included"] += 1

            zf.writestr(prefix + "metadata.json", json.dumps(metadata, indent=2))

        zf.writestr("curated_export/summary.json", json.dumps(summary, indent=2))

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=curated_{session_id}.zip"},
    )
