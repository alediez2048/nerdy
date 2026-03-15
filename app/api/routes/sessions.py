# Ad-Ops-Autopilot — Session CRUD API (PA-04)
import secrets
from datetime import datetime, timezone
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
