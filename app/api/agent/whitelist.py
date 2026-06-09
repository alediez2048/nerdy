# Ad-Ops-Autopilot — Per-touchpoint × per-phase tool whitelist (PJ-05)
"""Which tools is the LLM allowed to see / call right now?

PJ-00 §6.4 calls this the safety rail: the LLM might try to
``mark_good_enough`` during the ``identify`` phase, or ``advance_phase``
during ``refine``. The backend rejects those calls — but better, the
backend never advertises those tools in the first place. The LLM
literally doesn't see a tool that isn't whitelisted for the current
``(touchpoint, phase)``.

Backend is law. The whitelist is enforced in two places:
1. Tool decls sent to Gemini are filtered by ``whitelist_for(...)``.
2. ``ToolBox.dispatch`` rechecks the whitelist before executing, so a
   malicious or buggy LLM that emits an off-whitelist call is rejected
   at runtime as defense-in-depth.
"""
from __future__ import annotations

PHASE_ORDER: tuple[str, ...] = (
    "identify",
    "core",
    "extras",
    "assets",
    "good_enough",
    "complete",
)


def _onboarding_tools(phase: str) -> list[str]:
    base = ["save_field", "advance_phase", "ask_user", "finish_touchpoint"]
    if phase in ("core", "extras", "assets", "good_enough"):
        base.append("update_extra")
    if phase in ("assets", "good_enough"):
        base.append("ingest_asset")
    if phase == "good_enough":
        base.append("mark_good_enough")
    return base


def whitelist_for(touchpoint: str, phase: str) -> list[str]:
    """Return the ordered list of tool names allowed in this context."""
    base = ["ask_user", "finish_touchpoint"]
    if touchpoint == "onboarding":
        return _onboarding_tools(phase)
    if touchpoint == "post_session":
        return ["save_field", "update_extra", *base]
    if touchpoint == "pre_session_prep":
        # Read-only on brand_profile per PJ-00 §3 decision 16 (GRILL Q6).
        return ["propose_brief", *base]
    if touchpoint == "refine":
        return ["save_field", "update_extra", "ingest_asset", *base]
    # Unknown touchpoint — return the minimum so the LLM can at least
    # bail via ask_user / finish_touchpoint.
    return base


def next_phase(current: str) -> str | None:
    """The next phase in canonical order, or None if already at the end."""
    try:
        idx = PHASE_ORDER.index(current)
    except ValueError:
        return PHASE_ORDER[0]
    if idx + 1 >= len(PHASE_ORDER):
        return None
    return PHASE_ORDER[idx + 1]


def can_advance_to(current: str, requested: str) -> bool:
    """Phase advance is strictly forward, no skipping. ``current == requested``
    is allowed (idempotent advance)."""
    try:
        a = PHASE_ORDER.index(current)
        b = PHASE_ORDER.index(requested)
    except ValueError:
        return False
    return b == a or b == a + 1
