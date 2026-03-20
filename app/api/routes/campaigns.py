# PC-04: Campaign CRUD API
import secrets
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas.campaign import (
    CampaignCreate,
    CampaignDetail,
    CampaignListResponse,
    CampaignStats,
    CampaignSummary,
    CampaignUpdate,
)
from app.api.schemas.session import ProgressSummary, SessionListResponse, SessionSummary
from app.db import get_db, init_db
from app.models.campaign import Campaign as CampaignModel
from app.models.session import Session as SessionModel
from app.workers.progress import get_progress_summary

router = APIRouter()


def _campaign_id() -> str:
    """Generate unique campaign_id: camp_<hex(8)>."""
    return f"camp_{secrets.token_hex(8)}"


def _get_user_campaign(db: Session, campaign_id: str, user_id: str) -> CampaignModel:
    """Get a campaign owned by user_id, or raise 404."""
    row = db.query(CampaignModel).filter(
        CampaignModel.campaign_id == campaign_id,
        CampaignModel.user_id == user_id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return row


def _total_ledger_cost() -> float:
    """Calculate total cost from ALL ledgers (global + session) using real token data.

    Session ledgers often have tokens_consumed=0 (not captured from API),
    so we merge with the global ledger which has real token counts from
    earlier pipeline runs.
    """
    try:
        from output.export_dashboard import merge_ledger_events
        from evaluate.cost_reporter import MODEL_COST_RATES

        global_ledger = Path("data/ledger.jsonl")
        ledger_paths: list[str] = []
        if global_ledger.exists():
            ledger_paths.append(str(global_ledger))
        session_ledgers = sorted(Path("data/sessions").glob("*/ledger.jsonl"))
        ledger_paths.extend(str(p) for p in session_ledgers)

        if not ledger_paths:
            return 0.0

        events = merge_ledger_events(ledger_paths)
        cost = 0.0
        for evt in events:
            model = evt.get("model_used", "unknown")
            tokens = evt.get("tokens_consumed", 0)
            rate = MODEL_COST_RATES.get(model, 0.01 / 1000)
            cost += rate * tokens
        return round(cost, 2)
    except Exception:
        return 0.0


def _compute_campaign_stats(db: Session, campaign_id: str) -> CampaignStats:
    """PC-11: Compute aggregate statistics from all sessions in a campaign."""
    sessions = db.query(SessionModel).filter(SessionModel.campaign_id == campaign_id).all()

    total_ads_gen = 0
    total_ads_pub = 0
    weighted_score_sum = 0.0
    total_weight = 0
    status_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}

    for s in sessions:
        r = s.results_summary or {}
        c = s.config or {}

        # Handle both field name variations
        gen = r.get("ads_generated", 0) or r.get("total_ads_generated", 0)
        pub = r.get("ads_published", 0) or r.get("total_ads_published", 0)
        avg = r.get("avg_score", 0.0) or r.get("avg_quality_score", 0.0)

        total_ads_gen += int(gen) if gen else 0
        total_ads_pub += int(pub) if pub else 0

        if pub and avg:
            weighted_score_sum += float(avg) * int(pub)
            total_weight += int(pub)

        status_counts[s.status] = status_counts.get(s.status, 0) + 1
        stype = c.get("session_type", "image")
        type_counts[stype] = type_counts.get(stype, 0) + 1

    # Use real cost from merged ledgers (global + session)
    total_cost = _total_ledger_cost()

    return CampaignStats(
        total_sessions=len(sessions),
        sessions_by_status=status_counts,
        total_ads_generated=total_ads_gen,
        total_ads_published=total_ads_pub,
        avg_quality_score=round(weighted_score_sum / total_weight, 2) if total_weight > 0 else 0.0,
        total_cost=total_cost,
        session_types=type_counts,
    )


@router.post("", response_model=CampaignDetail, status_code=201)
def create_campaign(
    body: CampaignCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> CampaignDetail:
    """Create a new campaign."""
    init_db()
    cid = _campaign_id()

    campaign_row = CampaignModel(
        campaign_id=cid,
        name=body.name,
        user_id=user["user_id"],
        description=body.description,
        audience=body.audience,
        campaign_goal=body.campaign_goal,
        default_config=body.default_config,
        status="active",
    )
    db.add(campaign_row)
    db.commit()
    db.refresh(campaign_row)

    # Count sessions
    session_count = db.query(SessionModel).filter(SessionModel.campaign_id == cid).count()
    
    # PC-11: Compute stats (will be all zeros for new campaign)
    stats = _compute_campaign_stats(db, cid)

    return CampaignDetail(
        id=campaign_row.id,
        campaign_id=campaign_row.campaign_id,
        name=campaign_row.name,
        description=campaign_row.description,
        audience=campaign_row.audience,
        campaign_goal=campaign_row.campaign_goal,
        default_config=campaign_row.default_config,
        status=campaign_row.status,
        created_at=campaign_row.created_at,
        updated_at=campaign_row.updated_at,
        session_count=session_count,
        stats=stats,
    )


@router.get("", response_model=CampaignListResponse)
def list_campaigns(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    status: str | None = Query(default=None, pattern="^(active|archived)$"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> CampaignListResponse:
    """List user's campaigns with pagination and status filter."""
    query = db.query(CampaignModel).filter(CampaignModel.user_id == user["user_id"])

    # Default to active only if no status filter
    if status is None:
        query = query.filter(CampaignModel.status == "active")
    elif status:
        query = query.filter(CampaignModel.status == status)

    total = query.count()
    rows = query.order_by(CampaignModel.created_at.desc()).offset(offset).limit(limit).all()

    # Build summaries with session counts and lightweight stats
    summaries = []
    for row in rows:
        session_count = db.query(SessionModel).filter(SessionModel.campaign_id == row.campaign_id).count()
        stats = _compute_campaign_stats(db, row.campaign_id)
        summaries.append(
            CampaignSummary(
                id=row.id,
                campaign_id=row.campaign_id,
                name=row.name,
                description=row.description,
                audience=row.audience,
                campaign_goal=row.campaign_goal,
                status=row.status,
                created_at=row.created_at,
                session_count=session_count,
                total_ads_published=stats.total_ads_published,
                avg_quality_score=stats.avg_quality_score,
            )
        )

    return CampaignListResponse(campaigns=summaries, total=total, offset=offset, limit=limit)


@router.get("/{campaign_id}", response_model=CampaignDetail)
def get_campaign(
    campaign_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> CampaignDetail:
    """Get campaign detail by campaign_id."""
    row = _get_user_campaign(db, campaign_id, user["user_id"])

    # Count sessions
    session_count = db.query(SessionModel).filter(SessionModel.campaign_id == campaign_id).count()
    
    # PC-11: Compute stats
    stats = _compute_campaign_stats(db, campaign_id)

    return CampaignDetail(
        id=row.id,
        campaign_id=row.campaign_id,
        name=row.name,
        description=row.description,
        audience=row.audience,
        campaign_goal=row.campaign_goal,
        default_config=row.default_config,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
        session_count=session_count,
        stats=stats,
    )


@router.patch("/{campaign_id}", response_model=CampaignDetail)
def update_campaign(
    campaign_id: str,
    body: CampaignUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> CampaignDetail:
    """Update campaign name, description, or status."""
    row = _get_user_campaign(db, campaign_id, user["user_id"])

    if body.name is not None:
        row.name = body.name
    if body.description is not None:
        row.description = body.description
    if body.status is not None:
        row.status = body.status

    db.commit()
    db.refresh(row)

    # Count sessions
    session_count = db.query(SessionModel).filter(SessionModel.campaign_id == campaign_id).count()
    
    # PC-11: Compute stats
    stats = _compute_campaign_stats(db, campaign_id)

    return CampaignDetail(
        id=row.id,
        campaign_id=row.campaign_id,
        name=row.name,
        description=row.description,
        audience=row.audience,
        campaign_goal=row.campaign_goal,
        default_config=row.default_config,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
        session_count=session_count,
        stats=stats,
    )


@router.delete("/{campaign_id}", response_model=CampaignDetail)
def delete_campaign(
    campaign_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> CampaignDetail:
    """Soft delete campaign (set status to archived)."""
    row = _get_user_campaign(db, campaign_id, user["user_id"])

    row.status = "archived"
    db.commit()
    db.refresh(row)

    # Count sessions
    session_count = db.query(SessionModel).filter(SessionModel.campaign_id == campaign_id).count()
    
    # PC-11: Compute stats
    stats = _compute_campaign_stats(db, campaign_id)

    return CampaignDetail(
        id=row.id,
        campaign_id=row.campaign_id,
        name=row.name,
        description=row.description,
        audience=row.audience,
        campaign_goal=row.campaign_goal,
        default_config=row.default_config,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
        session_count=session_count,
        stats=stats,
    )


@router.post("/{campaign_id}/duplicate", response_model=CampaignDetail, status_code=201)
def duplicate_campaign(
    campaign_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> CampaignDetail:
    """PC-12: Duplicate a campaign — creates new campaign with same config, no sessions."""
    init_db()
    original = _get_user_campaign(db, campaign_id, user["user_id"])

    # Create new campaign with same config
    new_cid = _campaign_id()
    new_name = f"{original.name} (copy)"

    new_campaign = CampaignModel(
        campaign_id=new_cid,
        name=new_name,
        user_id=user["user_id"],
        description=original.description,
        audience=original.audience,
        campaign_goal=original.campaign_goal,
        default_config=original.default_config.copy() if original.default_config else {},
        status="active",
    )
    db.add(new_campaign)
    db.commit()
    db.refresh(new_campaign)

    # Count sessions (will be 0)
    session_count = db.query(SessionModel).filter(SessionModel.campaign_id == new_cid).count()
    
    # Compute stats (will be all zeros)
    stats = _compute_campaign_stats(db, new_cid)

    return CampaignDetail(
        id=new_campaign.id,
        campaign_id=new_campaign.campaign_id,
        name=new_campaign.name,
        description=new_campaign.description,
        audience=new_campaign.audience,
        campaign_goal=new_campaign.campaign_goal,
        default_config=new_campaign.default_config,
        status=new_campaign.status,
        created_at=new_campaign.created_at,
        updated_at=new_campaign.updated_at,
        session_count=session_count,
        stats=stats,
    )


@router.get("/{campaign_id}/sessions", response_model=SessionListResponse)
def get_campaign_sessions(
    campaign_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> SessionListResponse:
    """Get sessions for a specific campaign."""
    # Verify campaign exists and belongs to user
    _get_user_campaign(db, campaign_id, user["user_id"])

    # Query sessions for this campaign
    query = db.query(SessionModel).filter(
        SessionModel.campaign_id == campaign_id,
        SessionModel.user_id == user["user_id"],
    )

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

        # Import here to avoid circular import
        from app.api.routes.sessions import _get_session_ad_preview

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
