# Ad-Ops-Autopilot — Agent converse endpoint (PJ-04 scaffold)
"""POST /api/agent/converse — one synchronous chat turn.

Dispatches across 4 touchpoints (``onboarding``, ``post_session``,
``pre_session_prep``, ``refine``) per PJ-00 §8. PJ-04 ships the
scaffold: scoped auth, profile load/upsert, history fetch, and the
function-calling loop with two terminal stubs. PJ-06 brings the real
phased system prompt; PJ-05 brings the real tool roster.
"""
from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session as SASession

from app.api.agent.loop import run_conversation_turn
from app.api.agent.messages import (
    MAX_MESSAGES_RETURNED,
    append_message,
    load_history,
)
from app.api.agent.profile_loader import load_or_create_profile, serialize_profile
from app.api.agent.toolbox import ToolBox
from app.api.deps import get_current_user
from app.db import get_db, init_db
from app.models.brand_profile import BrandProfile

logger = logging.getLogger(__name__)

router = APIRouter()

TOUCHPOINTS = ("onboarding", "post_session", "pre_session_prep", "refine")


@router.post("/converse")
def converse(
    db: Annotated[SASession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    payload: Annotated[dict, Body(...)],
) -> dict[str, Any]:
    """One synchronous turn of the agent loop.

    Request: ``{touchpoint, session_id?, user_message?, uploaded_asset_ids?}``
    Response: ``{assistant_message, phase, good_enough_now, profile_snapshot,
                 asset_extractions?, exit_reason}``
    """
    init_db()

    touchpoint = payload.get("touchpoint")
    if touchpoint not in TOUCHPOINTS:
        raise HTTPException(status_code=400, detail=f"invalid touchpoint: {touchpoint!r}")

    session_id = payload.get("session_id")
    user_message = payload.get("user_message") or None
    uploaded_asset_ids = payload.get("uploaded_asset_ids") or []

    # Per PJ-00 §6.1: any touchpoint other than onboarding requires an
    # existing profile row.
    if touchpoint != "onboarding":
        existing = (
            db.query(BrandProfile)
            .filter_by(user_id=user["user_id"])
            .first()
        )
        if existing is None:
            raise HTTPException(
                status_code=403, detail="brand_profile_not_initialized"
            )

    profile = load_or_create_profile(db, user["user_id"])

    # Persist the user's turn BEFORE running the model so history+context
    # used by the next iteration includes it.
    if user_message:
        append_message(
            db,
            user_id=user["user_id"],
            touchpoint=touchpoint,
            session_id=session_id,
            role="user",
            content=user_message,
            phase=profile.onboarding_phase,
        )

    rows = load_history(
        db,
        user_id=user["user_id"],
        touchpoint=touchpoint,
        session_id=session_id,
        limit=MAX_MESSAGES_RETURNED,
    )
    history = [
        {"role": r.role, "content": r.content}
        for r in rows
        if r.role in ("user", "assistant") and r.content
    ]

    # Pull extracted facts for any newly-uploaded assets into the
    # system-prompt context. PJ-03 populates extracted_facts; if vision
    # hasn't finished yet, the LLM gets a placeholder.
    asset_extractions = _collect_asset_extractions(db, user["user_id"], uploaded_asset_ids)

    # PJ-06 will replace this stub with the real phased system prompt.
    system_prompt = _stub_system_prompt(touchpoint, profile, asset_extractions)

    toolbox = ToolBox(
        user_id=user["user_id"],
        db=db,
        touchpoint=touchpoint,
        session_id=session_id,
    )

    out = run_conversation_turn(toolbox, history, system_prompt)

    # Persist the assistant's reply.
    append_message(
        db,
        user_id=user["user_id"],
        touchpoint=touchpoint,
        session_id=session_id,
        role="assistant",
        content=out["assistant_message"],
        phase=profile.onboarding_phase,
    )
    db.refresh(profile)

    response: dict[str, Any] = {
        "assistant_message": out["assistant_message"],
        "phase": profile.onboarding_phase,
        "good_enough_now": profile.good_enough_at is not None,
        "profile_snapshot": serialize_profile(profile),
        "exit_reason": out.get("exit_reason"),
    }
    if asset_extractions:
        response["asset_extractions"] = asset_extractions
    return response


def _collect_asset_extractions(
    db: SASession, user_id: str, asset_ids: list[str]
) -> dict[str, Any]:
    """Fetch ``extracted_facts`` for the listed assets owned by the user."""
    if not asset_ids:
        return {}
    from app.models.brand_asset import BrandAsset

    out: dict[str, Any] = {}
    rows = (
        db.query(BrandAsset)
        .filter(BrandAsset.user_id == user_id, BrandAsset.id.in_(asset_ids))
        .all()
    )
    for r in rows:
        out[r.id] = r.extracted_facts or {"status": "pending"}
    return out


def _stub_system_prompt(touchpoint: str, profile: BrandProfile, assets: dict) -> str:
    """Minimal system prompt for the PJ-04 scaffold. PJ-06 replaces this
    with the phased onboarding policy + per-touchpoint variants."""
    lines = [
        f"You are AdEngine's onboarding agent. Touchpoint: {touchpoint}.",
        f"Current onboarding_phase: {profile.onboarding_phase}.",
        "Use the available tools rather than free prose. Prefer ask_user "
        "for follow-ups, finish_touchpoint to wrap up.",
    ]
    if assets:
        lines.append(
            "The user has uploaded assets. Extracted facts: "
            f"{assets}. Confirm these with the user before persisting."
        )
    return " ".join(lines)
