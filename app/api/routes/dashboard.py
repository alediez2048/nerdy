# Ad-Ops-Autopilot — Dashboard API endpoints (PA-09)
"""Session-scoped dashboard data endpoints. Reuses output/export_dashboard.py logic."""

import json
import logging
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db, init_db
from app.models.session import Session as SessionModel

router = APIRouter()
logger = logging.getLogger(__name__)

DEFAULT_LEDGER = "data/ledger.jsonl"


def _get_session(db: Session, session_id: str, user_id: str) -> SessionModel:
    """Get a session owned by user, or 404."""
    row = db.query(SessionModel).filter(
        SessionModel.session_id == session_id,
        SessionModel.user_id == user_id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return row


def _get_dashboard_data(session: SessionModel) -> dict:
    """Get full dashboard data, falling back to global ledger if no session ledger."""
    ledger_path = session.ledger_path or DEFAULT_LEDGER
    if not Path(ledger_path).exists():
        ledger_path = DEFAULT_LEDGER

    try:
        from output.export_dashboard import build_dashboard_data
        return build_dashboard_data(ledger_path)
    except Exception as e:
        logger.warning("Failed to build dashboard data: %s", e)
        return {}


@router.get("/{session_id}/summary")
def get_summary(
    session_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Hero metrics for session dashboard."""
    init_db()
    session = _get_session(db, session_id, user["user_id"])
    data = _get_dashboard_data(session)
    return {
        "session_id": session_id,
        "pipeline_summary": data.get("pipeline_summary", {}),
        "results_summary": session.results_summary or {},
    }


@router.get("/{session_id}/cycles")
def get_cycles(
    session_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Per-cycle iteration data."""
    init_db()
    session = _get_session(db, session_id, user["user_id"])
    data = _get_dashboard_data(session)
    return {
        "session_id": session_id,
        "iteration_cycles": data.get("iteration_cycles", []),
        "quality_trends": data.get("quality_trends", {}),
    }


@router.get("/{session_id}/dimensions")
def get_dimensions(
    session_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Dimension scores per cycle."""
    init_db()
    session = _get_session(db, session_id, user["user_id"])
    data = _get_dashboard_data(session)
    return {
        "session_id": session_id,
        "dimension_deep_dive": data.get("dimension_deep_dive", {}),
    }


@router.get("/{session_id}/costs")
def get_costs(
    session_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Token economics breakdown."""
    init_db()
    session = _get_session(db, session_id, user["user_id"])
    data = _get_dashboard_data(session)
    return {
        "session_id": session_id,
        "token_economics": data.get("token_economics", {}),
    }


@router.get("/{session_id}/ads")
def get_ads(
    session_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Full ad library for session."""
    init_db()
    session = _get_session(db, session_id, user["user_id"])
    data = _get_dashboard_data(session)
    return {
        "session_id": session_id,
        "ad_library": data.get("ad_library", []),
    }


@router.get("/{session_id}/spc")
def get_spc(
    session_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """SPC control chart + system health data."""
    init_db()
    session = _get_session(db, session_id, user["user_id"])
    data = _get_dashboard_data(session)
    return {
        "session_id": session_id,
        "system_health": data.get("system_health", {}),
    }


# --- Global dashboard (no auth, reads global ledger) ---

global_dashboard_router = APIRouter()


@global_dashboard_router.get("/global")
def get_global_dashboard() -> dict[str, Any]:
    """Full dashboard data from the global ledger — no auth required."""
    ledger = Path(DEFAULT_LEDGER)
    if not ledger.exists():
        return {}
    try:
        from output.export_dashboard import build_dashboard_data
        return build_dashboard_data(str(ledger))
    except Exception as e:
        logger.warning("Failed to build global dashboard: %s", e)
        raise HTTPException(status_code=500, detail="Failed to build dashboard data")


# --- Competitive intel (shared, not session-scoped) ---

competitive_router = APIRouter()


@competitive_router.get("/summary")
def get_competitive_summary() -> dict[str, Any]:
    """Competitive intelligence summary from pattern database."""
    result: dict[str, Any] = {}
    try:
        from output.export_dashboard import _build_competitive_intel
        result = _build_competitive_intel("data/ledger.jsonl")
    except Exception:
        pass

    patterns_path = Path("data/competitive/patterns.json")
    if patterns_path.exists():
        with open(patterns_path) as f:
            raw = json.load(f)
        if "competitor_summaries" in raw:
            result["competitor_summaries"] = raw["competitor_summaries"]
        if "metadata" in raw:
            result["metadata"] = raw["metadata"]
    return result
