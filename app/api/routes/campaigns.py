# PC-04: Campaign CRUD API
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas.campaign import (
    CampaignCreate,
    CampaignDetail,
    CampaignListResponse,
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

    # Build summaries with session counts
    summaries = []
    for row in rows:
        session_count = db.query(SessionModel).filter(SessionModel.campaign_id == row.campaign_id).count()
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
