# Ad-Ops-Autopilot — Per-request agent ToolBox (PJ-04)
"""Closure-bound tool dispatcher. ``user_id`` is captured in the
ToolBox instance and is NEVER exposed to the LLM as a tool argument.

This is the security property called out in PJ-00 §3 decision 12
(GRILL Q2): even if a prompt jailbreak makes the LLM emit
``save_field(user_id="someone_else", ...)``, our dispatcher ignores
any ``user_id`` key the model supplies and uses ``self.user_id`` from
the verified Clerk JWT. Cross-tenant writes from the LLM surface are
physically impossible.

PJ-04 ships only the two terminal stubs (`ask_user`, `finish_touchpoint`)
plus a minimal `save_field` placeholder used in the security test. The
full tool roster (save_field core, update_extra, ingest_asset,
advance_phase, mark_good_enough, propose_brief) lands in PJ-05.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session as SASession

from app.models.brand_profile import BrandProfile


@dataclass
class ToolBox:
    """Per-request closure capturing user identity and DB session.

    Tool methods are bound to this instance. The LLM only ever sees the
    method names + their non-``user_id`` parameters.
    """

    user_id: str
    db: SASession
    touchpoint: str
    session_id: str | None = None

    # ---------------------------------------------------------------
    # Terminal stubs — these exit the loop.
    # ---------------------------------------------------------------

    def ask_user(self, message: str) -> dict[str, Any]:
        """Return control to the user with a question or remark.

        Loop terminator. The frontend renders ``message`` and waits for
        the user's reply, which arrives on the next ``/converse`` call.
        """
        return {
            "_terminal": True,
            "kind": "ask_user",
            "message": message,
        }

    def finish_touchpoint(self, summary: str) -> dict[str, Any]:
        """End the conversation; for onboarding, flip phase to ``complete``."""
        if self.touchpoint == "onboarding":
            row = self.db.query(BrandProfile).filter_by(user_id=self.user_id).first()
            if row is not None:
                row.onboarding_phase = "complete"
                self.db.commit()
        return {
            "_terminal": True,
            "kind": "finish_touchpoint",
            "summary": summary,
        }

    # ---------------------------------------------------------------
    # PJ-05 will replace this stub with the full implementation.
    # Kept minimal here so PJ-04's security test can exercise the
    # closure-binding property end-to-end.
    # ---------------------------------------------------------------

    def save_field(self, name: str, value: Any) -> dict[str, Any]:
        """Stub — writes ONLY to ``self.user_id``'s profile, ignoring
        any ``user_id`` the LLM might attempt to inject. PJ-05 expands
        with full validation, rationale tracking, and field allowlist.
        """
        row = self.db.query(BrandProfile).filter_by(user_id=self.user_id).first()
        if row is None:
            row = BrandProfile(user_id=self.user_id)
            self.db.add(row)
        # Allowlist enforcement is PJ-05's job. v1 accepts anything but
        # uses setattr so unknown columns fail loudly rather than corrupt.
        if hasattr(row, name):
            setattr(row, name, value)
            self.db.commit()
            return {"_terminal": False, "saved": name}
        return {"_terminal": False, "error": f"unknown field: {name}"}

    # ---------------------------------------------------------------
    # Dispatch — turn a Gemini ``function_call`` into a real bound call.
    # ---------------------------------------------------------------

    def dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Look up the method by name and call it with model-supplied args.

        Critically: ``user_id`` is filtered out of ``args`` before the
        call. This is the runtime enforcement of the closure-binding
        rule — defense-in-depth, on top of the schema-level rule that
        the function declarations don't list ``user_id`` as a parameter.
        """
        method = TOOL_METHODS.get(name)
        if method is None:
            return {"error": f"unknown tool: {name}"}
        safe_args = {k: v for k, v in (args or {}).items() if k != "user_id"}
        return method(self, **safe_args)


# Method allowlist. Tools the LLM can call must be listed here.
TOOL_METHODS = {
    "ask_user": ToolBox.ask_user,
    "finish_touchpoint": ToolBox.finish_touchpoint,
    "save_field": ToolBox.save_field,
}
