# Ad-Ops-Autopilot — Session CRUD API (PA-04)
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas.session import ProgressSummary, SessionCreate, SessionDetail, SessionSummary
from app.db import get_db, init_db
from app.models.session import Session as SessionModel
from app.workers.progress import get_progress_summary
from app.workers.tasks.pipeline_task import run_pipeline_session

router = APIRouter()


def _session_id() -> str:
    return f"sess_{secrets.token_hex(8)}"


@router.post("", response_model=SessionDetail)
def create_session(
    body: SessionCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> SessionModel:
    """Create session and trigger Celery pipeline job."""
    init_db()
    session_id = _session_id()
    session_row = SessionModel(
        session_id=session_id,
        user_id=user["user_id"],
        config=body.config,
        status="pending",
    )
    db.add(session_row)
    db.commit()
    db.refresh(session_row)

    task = run_pipeline_session.delay(session_id)
    session_row.celery_task_id = task.id
    db.commit()
    db.refresh(session_row)

    return session_row


@router.get("", response_model=list[SessionSummary])
def list_sessions(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
) -> list[SessionSummary]:
    """List sessions with progress_summary for running ones."""
    init_db()
    rows = db.query(SessionModel).order_by(SessionModel.created_at.desc()).all()
    result: list[SessionSummary] = []
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
        result.append(
            SessionSummary(
                id=row.id,
                session_id=row.session_id,
                status=row.status,
                created_at=row.created_at,
                progress_summary=progress_summary,
            )
        )
    return result


@router.get("/{session_id}", response_model=SessionDetail)
def get_session(
    session_id: str,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
) -> SessionModel:
    """Get session detail by session_id."""
    init_db()
    row = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return row
