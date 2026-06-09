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

from app.api.agent.loop import build_function_declarations, run_conversation_turn
from app.api.agent.messages import (
    MAX_MESSAGES_RETURNED,
    append_message,
    load_history,
)
from app.api.agent.profile_loader import load_or_create_profile, serialize_profile
from app.api.agent.prompts import build_prompt_for
from app.api.agent.toolbox import ToolBox
from app.api.agent.whitelist import whitelist_for
from app.api.deps import get_current_user
from app.db import get_db, init_db
from app.models.brand_profile import BrandProfile

logger = logging.getLogger(__name__)

router = APIRouter()

TOUCHPOINTS = ("onboarding", "post_session", "pre_session_prep", "refine")


@router.get("/profile-status")
def profile_status(
    db: Annotated[SASession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Lightweight check used by the frontend's onboarding-gate redirect.

    Returns ``{phase, good_enough_now}``. Defaults to phase=``'identify'``
    and ``good_enough_now=False`` when the user has no profile row yet
    (i.e. brand-new user, never onboarded).
    """
    init_db()
    row = (
        db.query(BrandProfile)
        .filter_by(user_id=user["user_id"])
        .first()
    )
    if row is None:
        return {"phase": "identify", "good_enough_now": False}
    return {
        "phase": row.onboarding_phase or "identify",
        "good_enough_now": row.good_enough_at is not None,
    }


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

    # Page-refresh shortcut: if the user opened the chat with no input
    # and no new uploads AND there's already an assistant message in
    # history, return the latest assistant turn without re-prompting
    # Gemini. Without this, the LLM sees its own prior greeting and
    # often emits empty text → "(no response)" surfaces to the user.
    if not user_message and not uploaded_asset_ids:
        last_assistant = next(
            (r for r in reversed(rows) if r.role == "assistant" and r.content),
            None,
        )
        if last_assistant is not None:
            return {
                "assistant_message": last_assistant.content,
                "phase": profile.onboarding_phase,
                "good_enough_now": profile.good_enough_at is not None,
                "profile_snapshot": serialize_profile(profile),
                "exit_reason": "resumed_from_history",
            }

    # Pull extracted facts for any newly-uploaded assets into the
    # system-prompt context. PJ-03 populates extracted_facts; if vision
    # hasn't finished yet, the LLM gets a placeholder.
    asset_extractions = _collect_asset_extractions(db, user["user_id"], uploaded_asset_ids)

    # PJ-06: phase-aware system prompt with industry hints + snapshot.
    session_summary = (payload.get("session_summary") or {}) if isinstance(payload, dict) else {}
    session_type = (payload.get("session_type") or "image") if isinstance(payload, dict) else "image"
    system_prompt = build_prompt_for(
        touchpoint,
        profile,
        session_summary=session_summary,
        session_type=session_type,
    )
    if asset_extractions:
        system_prompt += (
            "\n\n### Uploaded asset extractions\n"
            f"{asset_extractions}\n"
            "Confirm these with the user before persisting via ingest_asset."
        )

    toolbox = ToolBox(
        user_id=user["user_id"],
        db=db,
        touchpoint=touchpoint,
        session_id=session_id,
    )

    allowed = whitelist_for(touchpoint, profile.onboarding_phase or "identify")
    function_decls = build_function_declarations(allowed)
    out = run_conversation_turn(toolbox, history, system_prompt, function_decls)

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
    if "proposed_brief" in toolbox.side_effects:
        response["proposed_brief"] = toolbox.side_effects["proposed_brief"]
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


