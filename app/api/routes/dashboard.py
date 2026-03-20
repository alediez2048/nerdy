# Ad-Ops-Autopilot — Dashboard API endpoints (PA-09)
"""Session-scoped dashboard data endpoints. Reuses output/export_dashboard.py logic."""

import json
import logging
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import SessionLocal, get_db, init_db
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
    """Get dashboard data scoped to this session's own ledger.

    Returns empty data when the session ledger doesn't exist yet (e.g.
    pipeline is pending or just started) instead of falling back to the
    global ledger, which would leak ads from other sessions.
    """
    ledger_path = session.ledger_path
    if not ledger_path or not Path(ledger_path).exists():
        return {}

    try:
        from output.export_dashboard import build_dashboard_data
        return build_dashboard_data(ledger_path, session_id=session.session_id)
    except Exception as e:
        logger.warning("Failed to build dashboard data: %s", e)
        return {}


def _ledger_export_has_metrics(pipeline_summary: dict[str, Any]) -> bool:
    """True when ledger-derived summary has meaningful KPIs (prefer over DB fallback)."""
    gen = int(pipeline_summary.get("total_ads_generated") or 0)
    tok = int(pipeline_summary.get("total_tokens") or 0)
    cost = float(pipeline_summary.get("total_cost_usd") or 0.0)
    return gen > 0 or tok > 0 or cost > 0


def _merge_pipeline_summary_from_db(
    session: SessionModel,
    pipeline_summary: dict[str, Any],
) -> dict[str, Any]:
    """Fill pipeline_summary from DB ``results_summary`` / manifest when ledger export is empty.

    Sessions that ran in another environment, moved disks, or only have manifest
    cost still show Overview + Token Economics totals.
    """
    rs = session.results_summary or {}
    out = dict(pipeline_summary)

    # Ledger (or mocked) export already has KPIs — keep them; patch cost if ledger priced at 0
    if _ledger_export_has_metrics(out):
        cost = float(out.get("total_cost_usd") or 0.0)
        if cost <= 0 and rs.get("cost_so_far") is not None:
            out["total_cost_usd"] = float(rs["cost_so_far"])
            out.setdefault("cost_source", "results_summary")
        return out

    if rs.get("ads_generated") is not None:
        out["total_ads_generated"] = int(rs["ads_generated"])
    if rs.get("ads_published") is not None:
        out["total_ads_published"] = int(rs["ads_published"])
    if rs.get("ads_discarded") is not None:
        out["total_ads_discarded"] = int(rs["ads_discarded"])
    if rs.get("avg_score") is not None:
        out["avg_score"] = float(rs["avg_score"])
    if rs.get("videos_generated") is not None:
        out.setdefault("total_ads_generated", int(rs["videos_generated"]))
    gen = int(out.get("total_ads_generated") or 0)
    pub = int(out.get("total_ads_published") or 0)
    if gen or pub:
        out["publish_rate"] = round(pub / max(gen, 1), 3)

    if rs.get("cost_so_far") is not None:
        out["total_cost_usd"] = float(rs["cost_so_far"])
        out["cost_source"] = "results_summary"
    elif session.ledger_path:
        try:
            from evaluate.cost_reporter import compute_session_cost_usd

            scr = compute_session_cost_usd(session.session_id, session.ledger_path)
            if scr.total_usd > 0:
                out["total_cost_usd"] = scr.total_usd
                out["cost_source"] = scr.source
        except Exception:
            logger.debug("Manifest cost fallback failed for session %s", session.session_id)

    return out


def _merge_token_economics_from_db(
    session: SessionModel,
    token_economics: dict[str, Any],
    pipeline_summary: dict[str, Any],
) -> dict[str, Any]:
    """Ensure token_economics carries total_cost_usd when ledger panel is empty."""
    te = dict(token_economics)
    existing = te.get("total_cost_usd")
    if isinstance(existing, (int, float)) and float(existing) > 0:
        return te
    pc = pipeline_summary.get("total_cost_usd")
    if isinstance(pc, (int, float)) and float(pc) > 0:
        te["total_cost_usd"] = float(pc)
        src = pipeline_summary.get("cost_source")
        if isinstance(src, str):
            te["cost_source"] = src
        return te
    rs = session.results_summary or {}
    if rs.get("cost_so_far") is not None:
        te["total_cost_usd"] = float(rs["cost_so_far"])
        te["cost_source"] = "results_summary"
    elif session.ledger_path:
        try:
            from evaluate.cost_reporter import compute_session_cost_usd

            scr = compute_session_cost_usd(session.session_id, session.ledger_path)
            if scr.total_usd > 0:
                te["total_cost_usd"] = scr.total_usd
                te["cost_source"] = scr.source
        except Exception:
            pass
    return te


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
    ps = _merge_pipeline_summary_from_db(session, data.get("pipeline_summary", {}))
    return {
        "session_id": session_id,
        "pipeline_summary": ps,
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
    ps = _merge_pipeline_summary_from_db(session, data.get("pipeline_summary", {}))
    te = _merge_token_economics_from_db(session, data.get("token_economics", {}), ps)
    return {
        "session_id": session_id,
        "token_economics": te,
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
def get_global_dashboard(timeframe: str = "all") -> dict[str, Any]:
    """Full dashboard data from the global ledger — no auth required."""
    ledger = Path(DEFAULT_LEDGER)
    if not ledger.exists():
        return {}
    try:
        from output.export_dashboard import (
            build_dashboard_data_from_events,
            filter_events_by_timeframe,
            merge_ledger_events,
        )
        session_pairs: list[tuple[str, str]] = []
        session_ledgers = sorted(Path("data/sessions").glob("*/ledger.jsonl"))
        ledger_paths = [str(ledger), *[str(path) for path in session_ledgers]]
        session_labels: dict[str, str] = {}
        init_db()
        db = SessionLocal()
        try:
            rows = db.query(
                SessionModel.session_id,
                SessionModel.name,
                SessionModel.ledger_path,
            ).all()
            session_labels = {
                session_id: (name or session_id)
                for session_id, name, _lp in rows
            }
            session_pairs = [
                (session_id, lp)
                for session_id, _name, lp in rows
                if lp and Path(lp).exists()
            ]
        finally:
            db.close()

        merged_events = merge_ledger_events(ledger_paths, session_labels=session_labels)
        filtered_events = filter_events_by_timeframe(merged_events, timeframe)
        data = build_dashboard_data_from_events(filtered_events, "merged")
        data.setdefault("pipeline_summary", {})

        # Global total: all DB sessions (manifest + ledger) + standalone global ledger
        try:
            from evaluate.cost_reporter import compute_global_total_cost_usd

            data["pipeline_summary"]["total_cost_usd"] = compute_global_total_cost_usd(
                session_pairs,
                global_ledger_path=str(ledger),
            )
            data["pipeline_summary"]["cost_source"] = "global_aggregate"
        except Exception:
            pass

        token_econ = data.get("token_economics") or {}
        token_econ["total_cost_usd"] = data["pipeline_summary"].get("total_cost_usd", 0.0)
        token_econ["cost_source"] = "global_aggregate"
        data["token_economics"] = token_econ

        data["timeframe"] = timeframe
        return data
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
