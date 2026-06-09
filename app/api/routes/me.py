# Ad-Ops-Autopilot — Current-user resource endpoints (PJ-08)
"""``/api/me/*`` routes return resources scoped to the authenticated user.

These endpoints take NO path parameter for ``user_id`` — the user is
resolved from the verified Clerk JWT in ``get_current_user``. This is
the same closure-binding pattern the agent loop uses (PJ-00 §3
decision 12 / GRILL Q2): the auth dep is the source of identity, so
there is no LLM- or URL-supplied user_id to forge.
"""
from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SASession

from app.api.deps import get_current_user
from app.db import get_db, init_db
from app.models.brand_profile import BrandProfile

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/brand-profile")
def get_my_brand_profile(
    db: Annotated[SASession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Return the current user's full ``brand_profile`` row.

    Returns 404 if the user has no row yet — that signals to the
    frontend that onboarding hasn't started.
    """
    init_db()
    row = (
        db.query(BrandProfile)
        .filter_by(user_id=user["user_id"])
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="no_brand_profile")

    return {
        "user_id": row.user_id,
        "business_name": row.business_name,
        "industry": row.industry,
        "audience": row.audience,
        "mission": row.mission,
        "value_props": row.value_props or [],
        "tone_descriptors": row.tone_descriptors or [],
        "avoid_phrases": row.avoid_phrases or [],
        "do_dont_rules": row.do_dont_rules or None,
        "palette_primary_hex": row.palette_primary_hex,
        "palette_secondary_hex": row.palette_secondary_hex,
        "palette_accent_hex": row.palette_accent_hex,
        "logo_asset_id": row.logo_asset_id,
        "logo_asset_url": (
            f"/api/brand-assets/{row.logo_asset_id}"
            if row.logo_asset_id else None
        ),
        "extras": row.extras or {},
        "onboarding_phase": row.onboarding_phase,
        "good_enough_at": (
            row.good_enough_at.isoformat() if row.good_enough_at else None
        ),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
