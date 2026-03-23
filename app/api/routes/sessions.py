# Ad-Ops-Autopilot — Session CRUD API (PA-04)
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas.session import (
    ProgressSummary,
    SessionCreate,
    SessionDetail,
    SessionListResponse,
    SessionSummary,
    SessionUpdate,
)
from app.db import get_db, init_db
from app.models.campaign import Campaign as CampaignModel
from app.models.session import Session as SessionModel
from app.workers.progress import get_progress_summary
from app.workers.tasks.pipeline_task import run_pipeline_session

router = APIRouter()


def _session_id() -> str:
    return f"sess_{secrets.token_hex(8)}"


def _auto_name(config: dict) -> str:
    """Auto-generate session name: 'SAT Parents Conversion — Mar 15'."""
    audience = config.get("audience", "").title()
    goal = config.get("campaign_goal", "").title()
    date = datetime.now(timezone.utc).strftime("%b %d")
    return f"SAT {audience} {goal} — {date}"


def _get_user_session(db: Session, session_id: str, user_id: str) -> SessionModel:
    """Get a session owned by user_id, or raise 404."""
    row = db.query(SessionModel).filter(
        SessionModel.session_id == session_id,
        SessionModel.user_id == user_id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return row


def _get_session_ad_preview(session_row: SessionModel) -> dict | None:
    """Return the earliest ad preview for a session when a ledger exists."""
    ledger_path = session_row.ledger_path
    if not ledger_path or not Path(ledger_path).exists():
        return None

    try:
        from iterate.ledger import read_events
        from output.export_dashboard import _build_ad_library

        library = _build_ad_library(read_events(ledger_path))
        if not library:
            return None

        def _created_at(item: dict) -> str:
            return item.get("created_at", "")

        cfg = session_row.config or {}
        if cfg.get("session_type") == "video":
            with_video = [a for a in library if a.get("video_url")]
            first_ad = min(with_video, key=_created_at) if with_video else min(library, key=_created_at)
        else:
            first_ad = min(library, key=_created_at)
        copy = first_ad.get("copy", {})
        return {
            "ad_id": first_ad.get("ad_id", ""),
            "image_url": first_ad.get("image_url"),
            "video_url": first_ad.get("video_url"),
            "video_remote_url": first_ad.get("video_remote_url"),
            "primary_text": copy.get("primary_text", ""),
            "headline": copy.get("headline", ""),
            "cta_button": copy.get("cta_button"),
            "status": first_ad.get("status", "in_progress"),
            "aggregate_score": first_ad.get("aggregate_score", 0.0),
        }
    except Exception:
        return None


@router.get("/{session_id}/ledger")
def get_session_ledger(session_id: str, db: Annotated[Session, Depends(get_db)]) -> Any:
    """Return raw ledger events for debugging."""
    from app.models.session import Session as SessionModel
    row = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    lp = row.ledger_path
    if not lp or not Path(lp).exists():
        return {"events": [], "error": f"ledger not found: {lp}"}
    import json as _json
    with open(lp) as f:
        events = [_json.loads(line) for line in f if line.strip()]
    return {"count": len(events), "events": events}


@router.post("", response_model=SessionDetail, status_code=201)
def create_session(
    body: SessionCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> SessionModel:
    """Create session and trigger Celery pipeline job."""
    init_db()
    sid = _session_id()
    config_dict = body.config.model_dump(mode="json")
    name = body.name or _auto_name(config_dict)

    # Validate campaign_id if provided
    campaign_id = None
    if body.campaign_id:
        campaign = db.query(CampaignModel).filter(
            CampaignModel.campaign_id == body.campaign_id,
            CampaignModel.user_id == user["user_id"],
        ).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        campaign_id = body.campaign_id

    session_row = SessionModel(
        session_id=sid,
        name=name,
        user_id=user["user_id"],
        campaign_id=campaign_id,
        config=config_dict,
        status="pending",
        ledger_path=f"data/sessions/{sid}/ledger.jsonl",
        output_path=f"output/sessions/{sid}",
    )
    db.add(session_row)
    db.commit()
    db.refresh(session_row)

    task = run_pipeline_session.delay(sid)
    session_row.celery_task_id = task.id
    db.commit()
    db.refresh(session_row)

    # Get campaign name if linked
    campaign_name = None
    if session_row.campaign_id:
        campaign = db.query(CampaignModel).filter(
            CampaignModel.campaign_id == session_row.campaign_id
        ).first()
        if campaign:
            campaign_name = campaign.name

    # Build response dict with campaign_name
    return {
        "id": session_row.id,
        "session_id": session_row.session_id,
        "name": session_row.name,
        "user_id": session_row.user_id,
        "config": session_row.config or {},
        "status": session_row.status,
        "campaign_id": session_row.campaign_id,
        "campaign_name": campaign_name,
        "celery_task_id": session_row.celery_task_id,
        "results_summary": session_row.results_summary,
        "ledger_path": session_row.ledger_path,
        "output_path": session_row.output_path,
        "created_at": session_row.created_at,
        "updated_at": session_row.updated_at,
        "completed_at": session_row.completed_at,
    }


@router.get("", response_model=SessionListResponse)
def list_sessions(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    session_type: str | None = Query(default=None),
    audience: str | None = Query(default=None),
    campaign_goal: str | None = Query(default=None),
    campaign_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> SessionListResponse:
    """List current user's sessions with optional filters and pagination."""
    init_db()
    query = db.query(SessionModel).filter(SessionModel.user_id == user["user_id"])

    # Apply filters on JSON config fields
    if session_type:
        query = query.filter(SessionModel.config["session_type"].as_string() == session_type)
    if audience:
        query = query.filter(SessionModel.config["audience"].as_string() == audience)
    if campaign_goal:
        query = query.filter(SessionModel.config["campaign_goal"].as_string() == campaign_goal)
    if campaign_id:
        query = query.filter(SessionModel.campaign_id == campaign_id)
    if status:
        query = query.filter(SessionModel.status == status)

    total = query.count()
    rows = query.order_by(SessionModel.created_at.desc()).offset(offset).limit(limit).all()

    sessions: list[SessionSummary] = []
    for row in rows:
        progress_summary = None
        if row.status == "running":
            summary = get_progress_summary(row.session_id)
            if summary:
                progress_summary = ProgressSummary(
                    current_cycle=summary.get("cycle", 0),
                    ads_generated=summary.get("ads_generated", 0),
                    ads_evaluated=summary.get("ads_evaluated", 0),
                    ads_published=summary.get("ads_published", 0),
                    current_score_avg=summary.get("current_score_avg", 0.0),
                    cost_so_far=summary.get("cost_so_far", 0.0),
                )
        sessions.append(
            SessionSummary(
                id=row.id,
                session_id=row.session_id,
                name=row.name,
                status=row.status,
                config=row.config or {},
                created_at=row.created_at,
                campaign_id=row.campaign_id,
                progress_summary=progress_summary,
                results_summary=row.results_summary,
                ad_preview=_get_session_ad_preview(row),
            )
        )

    return SessionListResponse(sessions=sessions, total=total, offset=offset, limit=limit)


@router.get("/{session_id}", response_model=SessionDetail)
def get_session(
    session_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Get session detail. Per-user isolation enforced."""
    init_db()
    row = _get_user_session(db, session_id, user["user_id"])

    # Get campaign name if linked
    campaign_name = None
    if row.campaign_id:
        campaign = db.query(CampaignModel).filter(
            CampaignModel.campaign_id == row.campaign_id
        ).first()
        if campaign:
            campaign_name = campaign.name

    # Build response dict with campaign_name
    return {
        "id": row.id,
        "session_id": row.session_id,
        "name": row.name,
        "user_id": row.user_id,
        "config": row.config or {},
        "status": row.status,
        "campaign_id": row.campaign_id,
        "campaign_name": campaign_name,
        "celery_task_id": row.celery_task_id,
        "results_summary": row.results_summary,
        "ledger_path": row.ledger_path,
        "output_path": row.output_path,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "completed_at": row.completed_at,
    }


@router.patch("/{session_id}", response_model=SessionDetail)
def update_session(
    session_id: str,
    body: SessionUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Update editable session metadata: name and/or campaign_id (PC-12)."""
    init_db()
    row = _get_user_session(db, session_id, user["user_id"])

    # PC-12: Cannot reassign running sessions
    if body.campaign_id is not None and row.status == "running":
        raise HTTPException(
            status_code=400,
            detail="Cannot reassign running session. Wait for it to complete or cancel it first."
        )

    # Update name if provided
    if body.name is not None:
        normalized_name = body.name.strip()
        if not normalized_name:
            raise HTTPException(status_code=400, detail="Session name cannot be empty")
        row.name = normalized_name

    # PC-12: Update campaign_id if provided
    if body.campaign_id is not None:
        if body.campaign_id and body.campaign_id.strip():
            # Validate campaign exists and belongs to user
            campaign = db.query(CampaignModel).filter(
                CampaignModel.campaign_id == body.campaign_id,
                CampaignModel.user_id == user["user_id"],
            ).first()
            if not campaign:
                raise HTTPException(status_code=404, detail="Campaign not found")
            row.campaign_id = body.campaign_id
        else:
            # Set to None to remove from campaign (empty string or None)
            row.campaign_id = None

    db.commit()
    db.refresh(row)

    # Get campaign name if linked
    campaign_name = None
    if row.campaign_id:
        campaign = db.query(CampaignModel).filter(
            CampaignModel.campaign_id == row.campaign_id
        ).first()
        if campaign:
            campaign_name = campaign.name

    # Build response dict with campaign_name
    return {
        "id": row.id,
        "session_id": row.session_id,
        "name": row.name,
        "user_id": row.user_id,
        "config": row.config or {},
        "status": row.status,
        "campaign_id": row.campaign_id,
        "campaign_name": campaign_name,
        "celery_task_id": row.celery_task_id,
        "results_summary": row.results_summary,
        "ledger_path": row.ledger_path,
        "output_path": row.output_path,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "completed_at": row.completed_at,
    }


@router.get("/{session_id}/brief-expansions")
def get_brief_expansions(
    session_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Brief expansion events from this session's ledger (testing / QA).

    Each event may include ``outputs.expanded_brief`` — the full structured
    brief after ``expand_brief()`` — when using a current pipeline build.
    """
    init_db()
    row = _get_user_session(db, session_id, user["user_id"])
    ledger_path = row.ledger_path
    if not ledger_path or not Path(ledger_path).exists():
        return {"session_id": session_id, "events": []}
    from iterate.ledger import read_events

    events = [e for e in read_events(ledger_path) if e.get("event_type") == "BriefExpanded"]
    return {"session_id": session_id, "events": events}


@router.delete("/{session_id}", status_code=204)
def delete_session(
    session_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> Response:
    """Delete session. Only owner can delete. Cancels running Celery task."""
    init_db()
    row = _get_user_session(db, session_id, user["user_id"])

    # Cancel Celery task if still running
    if row.status == "running" and row.celery_task_id:
        try:
            from app.workers.celery_app import celery_app
            celery_app.control.revoke(row.celery_task_id, terminate=True)
        except Exception:
            pass  # Best-effort cancel

    db.delete(row)
    db.commit()
    return Response(status_code=204)
