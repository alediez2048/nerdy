# Ad-Ops-Autopilot — Brand profile load/upsert helper (PJ-04)
"""Load the current user's ``brand_profile`` row, creating an empty one
on first call. Used at the top of every ``/converse`` turn so the
agent always has a row to update."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session as SASession

from app.models.brand_profile import BrandProfile

logger = logging.getLogger(__name__)


def load_or_create_profile(db: SASession, user_id: str) -> BrandProfile:
    """Return the user's ``brand_profile`` row, inserting if missing.

    A ``NULL onboarding_phase`` is coerced to ``'identify'`` and a
    warning is logged — defensive against bad migrations or manual
    DB edits.
    """
    row = db.query(BrandProfile).filter_by(user_id=user_id).first()
    if row is None:
        row = BrandProfile(user_id=user_id, onboarding_phase="identify")
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    if not row.onboarding_phase:
        logger.warning(
            "brand_profile for %s had NULL onboarding_phase, coercing to 'identify'",
            user_id,
        )
        row.onboarding_phase = "identify"
        db.commit()
        db.refresh(row)
    return row


def serialize_profile(row: BrandProfile) -> dict:
    """Return a JSON-safe dict snapshot of the typed-core fields + lifecycle."""
    return {
        "user_id": row.user_id,
        "business_name": row.business_name,
        "industry": row.industry,
        "audience": row.audience,
        "mission": row.mission,
        "value_props": row.value_props or [],
        "tone_descriptors": row.tone_descriptors or [],
        "avoid_phrases": row.avoid_phrases or [],
        "do_dont_rules": row.do_dont_rules,
        "palette_primary_hex": row.palette_primary_hex,
        "palette_secondary_hex": row.palette_secondary_hex,
        "palette_accent_hex": row.palette_accent_hex,
        "logo_asset_id": row.logo_asset_id,
        "extras": row.extras or {},
        "onboarding_phase": row.onboarding_phase,
        "good_enough_at": row.good_enough_at.isoformat() if row.good_enough_at else None,
    }
