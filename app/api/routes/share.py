# Ad-Ops-Autopilot — Share session links (PA-11)
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db, init_db
from app.models.session import Session as SessionModel
from app.models.share_token import ShareToken

router = APIRouter()

SHARE_EXPIRY_DAYS = 7


def _get_user_session(db: Session, session_id: str, user_id: str) -> SessionModel:
    row = db.query(SessionModel).filter(
        SessionModel.session_id == session_id,
        SessionModel.user_id == user_id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return row


@router.post("/{session_id}/share")
def create_share_link(
    session_id: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Generate a time-limited read-only share link. Returns existing if active."""
    init_db()
    session_row = _get_user_session(db, session_id, user["user_id"])

    # Check for existing active token
    now = datetime.now(timezone.utc)
    existing = db.query(ShareToken).filter(
        ShareToken.session_id == session_row.id,
        ShareToken.is_revoked == False,  # noqa: E712
        ShareToken.expires_at > now,
    ).first()

    if existing:
        base_url = str(request.base_url).rstrip("/")
        return {
            "share_url": f"{base_url}/shared/{existing.token}",
            "token": existing.token,
            "expires_at": existing.expires_at.isoformat(),
        }

    # Create new token
    token = secrets.token_urlsafe(32)
    expires_at = now + timedelta(days=SHARE_EXPIRY_DAYS)
    share = ShareToken(
        token=token,
        session_id=session_row.id,
        created_by=user["user_id"],
        expires_at=expires_at,
    )
    db.add(share)
    db.commit()

    base_url = str(request.base_url).rstrip("/")
    return {
        "share_url": f"{base_url}/shared/{token}",
        "token": token,
        "expires_at": expires_at.isoformat(),
    }


@router.delete("/{session_id}/share", status_code=204)
def revoke_share_link(
    session_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    """Revoke all active share tokens for a session."""
    init_db()
    session_row = _get_user_session(db, session_id, user["user_id"])
    tokens = db.query(ShareToken).filter(
        ShareToken.session_id == session_row.id,
        ShareToken.is_revoked == False,  # noqa: E712
    ).all()
    for t in tokens:
        t.is_revoked = True
    db.commit()


# --- Public shared endpoint (no auth required) ---

shared_router = APIRouter()


@shared_router.get("/{token}")
def get_shared_session(
    token: str,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """View a shared session — no auth required. Returns session detail + summary."""
    init_db()
    now = datetime.now(timezone.utc)
    share = db.query(ShareToken).filter(ShareToken.token == token).first()

    if not share:
        raise HTTPException(status_code=404, detail="Share link not found")
    if share.is_revoked:
        raise HTTPException(status_code=404, detail="Share link has been revoked")
    # Compare naive datetimes for SQLite compatibility
    expires = share.expires_at if share.expires_at.tzinfo else share.expires_at.replace(tzinfo=timezone.utc)
    if expires < now:
        raise HTTPException(status_code=404, detail="Share link has expired")

    session_row = db.query(SessionModel).filter(SessionModel.id == share.session_id).first()
    if not session_row:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_row.session_id,
        "name": session_row.name,
        "status": session_row.status,
        "config": session_row.config,
        "results_summary": session_row.results_summary,
        "created_at": session_row.created_at.isoformat() if session_row.created_at else None,
        "read_only": True,
    }
