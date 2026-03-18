# Ad-Ops-Autopilot — Session CRUD API (PA-04)
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

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

        first_ad = min(library, key=lambda item: item.get("created_at", ""))
        copy = first_ad.get("copy", {})
        return {
            "ad_id": first_ad.get("ad_id", ""),
            "image_url": first_ad.get("image_url"),
            "primary_text": copy.get("primary_text", ""),
            "headline": copy.get("headline", ""),
            "cta_button": copy.get("cta_button"),
            "status": first_ad.get("status", "in_progress"),
            "aggregate_score": first_ad.get("aggregate_score", 0.0),
        }
    except Exception:
        return None


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

    session_row = SessionModel(
        session_id=sid,
        name=name,
        user_id=user["user_id"],
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

    return session_row


@router.get("", response_model=SessionListResponse)
def list_sessions(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    audience: str | None = Query(default=None),
    campaign_goal: str | None = Query(default=None),
    status: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> SessionListResponse:
    """List current user's sessions with optional filters and pagination."""
    init_db()
    query = db.query(SessionModel).filter(SessionModel.user_id == user["user_id"])

    # Apply filters on JSON config fields
    if audience:
        query = query.filter(SessionModel.config["audience"].as_string() == audience)
    if campaign_goal:
        query = query.filter(SessionModel.config["campaign_goal"].as_string() == campaign_goal)
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
) -> SessionModel:
    """Get session detail. Per-user isolation enforced."""
    init_db()
    return _get_user_session(db, session_id, user["user_id"])


@router.patch("/{session_id}", response_model=SessionDetail)
def update_session(
    session_id: str,
    body: SessionUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> SessionModel:
    """Update editable session metadata such as display name."""
    init_db()
    row = _get_user_session(db, session_id, user["user_id"])
    normalized_name = body.name.strip()
    if not normalized_name:
        raise HTTPException(status_code=400, detail="Session name cannot be empty")

    row.name = normalized_name
    db.commit()
    db.refresh(row)
    return row


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
