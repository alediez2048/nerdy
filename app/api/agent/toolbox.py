# Ad-Ops-Autopilot — Per-request agent ToolBox (PJ-05)
"""Closure-bound tool dispatcher. ``user_id`` is captured in the
``ToolBox`` instance and is NEVER exposed to the LLM as a tool argument.

This is the security property called out in PJ-00 §3 decision 12
(GRILL Q2). The dispatcher filters ``user_id`` out of LLM-supplied args
as defense-in-depth on top of the schema-level rule that function
declarations don't list ``user_id`` as a parameter.

PJ-05 fills in the real tool roster: ``save_field``, ``update_extra``,
``ingest_asset``, ``advance_phase``, ``mark_good_enough``,
``propose_brief``. Per-touchpoint × per-phase whitelisting is enforced
both at declaration-build time (``build_function_declarations(allowed)``
in ``loop.py``) AND at dispatch time here.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session as SASession

from app.api.agent.validators import (
    RESERVED_EXTRAS_KEYS,
    brief_field_ok,
    normalize_extras_key,
    validate,
    validate_extras_value,
)
from app.api.agent.whitelist import can_advance_to, whitelist_for
from app.models.brand_asset import BrandAsset
from app.models.brand_profile import BrandProfile

logger = logging.getLogger(__name__)


@dataclass
class ToolBox:
    """Per-request closure capturing user identity and DB session."""

    user_id: str
    db: SASession
    touchpoint: str
    session_id: str | None = None
    # Bag the route reads after dispatch — propose_brief writes here,
    # the route surfaces the contents in the /converse response.
    side_effects: dict[str, Any] = field(default_factory=dict)

    # ---------------------------------------------------------------
    # Profile helper.
    # ---------------------------------------------------------------

    def _profile(self) -> BrandProfile:
        row = (
            self.db.query(BrandProfile)
            .filter_by(user_id=self.user_id)
            .first()
        )
        if row is None:
            row = BrandProfile(user_id=self.user_id)
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
        return row

    # ---------------------------------------------------------------
    # Terminal tools — these exit the loop.
    # ---------------------------------------------------------------

    def ask_user(self, message: str) -> dict[str, Any]:
        """Return control to the user with a question or remark."""
        return {
            "_terminal": True,
            "kind": "ask_user",
            "message": message,
        }

    def finish_touchpoint(self, summary: str) -> dict[str, Any]:
        """End the conversation; for onboarding, flip phase to ``complete``."""
        if self.touchpoint == "onboarding":
            row = self._profile()
            row.onboarding_phase = "complete"
            self.db.commit()
        return {
            "_terminal": True,
            "kind": "finish_touchpoint",
            "summary": summary,
        }

    # ---------------------------------------------------------------
    # Typed-field write.
    # ---------------------------------------------------------------

    def save_field(
        self,
        name: str,
        value: Any,
        confidence: float | None = None,
        rationale: str | None = None,
    ) -> dict[str, Any]:
        """Write a typed-core column on ``brand_profile``.

        ``confidence`` and ``rationale`` are accepted from the LLM but not
        persisted in v1 — the value itself is what the pipeline reads.
        Future work can route them into an audit log if useful.
        """
        v = validate(name, value)
        if not v["ok"]:
            return {"ok": False, "error": v["error"]}
        row = self._profile()
        setattr(row, name, v["value"])
        self.db.commit()
        return {
            "ok": True,
            "field": name,
            "stored": v["value"],
            "_meta": {
                "confidence": confidence,
                "rationale": rationale,
            },
        }

    # ---------------------------------------------------------------
    # Open-bag write.
    # ---------------------------------------------------------------

    def update_extra(
        self,
        key: str,
        value: Any,
        confidence: float | None = None,
        rationale: str | None = None,
    ) -> dict[str, Any]:
        """Merge an industry-specific fact into ``brand_profile.extras``."""
        normalized = normalize_extras_key(key)
        if not normalized:
            return {"ok": False, "error": "empty_or_invalid_key"}
        if normalized in RESERVED_EXTRAS_KEYS:
            return {
                "ok": False,
                "error": f"reserved_typed_column:{normalized}",
                "hint": "use save_field for typed-core columns",
            }
        v = validate_extras_value(value)
        if not v["ok"]:
            return {"ok": False, "error": v["error"]}

        row = self._profile()
        extras = dict(row.extras or {})
        extras[normalized] = {
            "value": v["value"],
            "confidence": confidence,
            "rationale": rationale,
        }
        row.extras = extras
        self.db.commit()
        return {"ok": True, "key": normalized}

    # ---------------------------------------------------------------
    # Asset facts.
    # ---------------------------------------------------------------

    def ingest_asset(
        self,
        asset_id: str,
        derive_palette: bool = True,
        derive_fonts: bool = True,
    ) -> dict[str, Any]:
        """Read ``brand_assets.extracted_facts`` for an asset the user owns.

        When ``derive_palette`` is true and the facts carry a palette, also
        write the hex values into the typed-core ``palette_*_hex`` columns
        so the pipeline picks them up without an extra confirmation turn.
        """
        asset = (
            self.db.query(BrandAsset)
            .filter_by(id=asset_id)
            .first()
        )
        if asset is None or asset.user_id != self.user_id:
            return {"ok": False, "error": "asset_not_found_for_user"}

        facts = asset.extracted_facts or {}
        if "error" in facts:
            return {
                "ok": False,
                "error": "vision_pass_failed",
                "detail": facts["error"],
            }
        if not facts:
            return {"ok": False, "error": "vision_pass_pending"}

        applied: dict[str, Any] = {}
        if derive_palette:
            palette = facts.get("dominant_colors") or facts.get("palette_hex") or []
            for col, hex_val in zip(
                ("palette_primary_hex", "palette_secondary_hex", "palette_accent_hex"),
                palette,
            ):
                v = validate(col, hex_val)
                if v["ok"]:
                    setattr(self._profile(), col, v["value"])
                    applied[col] = v["value"]
            if applied:
                self.db.commit()

        fonts = facts.get("detected_fonts") or facts.get("font_names") or []
        applied_fonts = bool(derive_fonts and fonts)

        # Also pin the logo_asset_id so the pipeline knows where to find it.
        if asset.asset_type == "logo":
            row = self._profile()
            row.logo_asset_id = asset.id
            self.db.commit()

        return {
            "ok": True,
            "asset_id": asset.id,
            "asset_type": asset.asset_type,
            "facts": facts,
            "applied_palette": applied,
            "applied_fonts": applied_fonts,
        }

    # ---------------------------------------------------------------
    # Phase advance + good-enough gate.
    # ---------------------------------------------------------------

    def advance_phase(self, next_phase: str, why: str | None = None) -> dict[str, Any]:
        """Move ``onboarding_phase`` strictly forward.

        Only callable during the onboarding touchpoint. Skipping a phase is
        rejected. Calling with the current phase is an idempotent no-op
        (returns ``ok: True``).
        """
        if self.touchpoint != "onboarding":
            return {"ok": False, "error": "only_in_onboarding"}
        row = self._profile()
        if not can_advance_to(row.onboarding_phase, next_phase):
            return {
                "ok": False,
                "error": "invalid_phase_transition",
                "current": row.onboarding_phase,
                "requested": next_phase,
            }
        if next_phase != row.onboarding_phase:
            row.onboarding_phase = next_phase
            self.db.commit()
        return {"ok": True, "phase": row.onboarding_phase, "why": why}

    def mark_good_enough(self) -> dict[str, Any]:
        """Set ``good_enough_at = now()`` if the typed-core gate passes.

        Per PJ-00 §7.5: business_name, industry, audience, mission all
        non-null AND len(value_props) >= 2 AND len(tone_descriptors) >= 2.
        Calling twice is an idempotent no-op.
        """
        row = self._profile()
        missing: list[str] = []
        for col in ("business_name", "industry", "audience", "mission"):
            if not getattr(row, col):
                missing.append(col)
        if not row.value_props or len(row.value_props) < 2:
            missing.append("value_props>=2")
        if not row.tone_descriptors or len(row.tone_descriptors) < 2:
            missing.append("tone_descriptors>=2")
        if missing:
            return {"ok": False, "error": "gate_not_met", "missing": missing}
        if row.good_enough_at is None:
            row.good_enough_at = datetime.now(timezone.utc)
            self.db.commit()
        return {"ok": True, "good_enough_at": row.good_enough_at.isoformat()}

    # ---------------------------------------------------------------
    # Pre-session prep — read-only on brand_profile (GRILL Q6).
    # ---------------------------------------------------------------

    def propose_brief(
        self,
        audience: str,
        persona: str,
        campaign_goal: str,
        key_message: str,
        creative_brief: str,
    ) -> dict[str, Any]:
        """Return a session brief draft to the frontend.

        Does NOT write to ``brand_profile``. The route attaches the
        result to the ``/converse`` response under ``proposed_brief``.
        PJ-11 will route this into ``NewSessionForm`` pre-fill.
        """
        if self.touchpoint != "pre_session_prep":
            return {"ok": False, "error": "only_in_pre_session_prep"}

        fields = {
            "audience": audience,
            "persona": persona,
            "campaign_goal": campaign_goal,
            "key_message": key_message,
            "creative_brief": creative_brief,
        }
        for k, v in fields.items():
            if not brief_field_ok(v):
                return {"ok": False, "error": f"brief_field_invalid:{k}"}

        # Stash for the route to pick up.
        self.side_effects["proposed_brief"] = fields
        return {"ok": True, "brief": fields}

    # ---------------------------------------------------------------
    # Dispatch.
    # ---------------------------------------------------------------

    def dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Look up the method by name and call it with model-supplied args.

        Two safeguards:
        - ``user_id`` is filtered out of args (closure binding).
        - The call is rejected unless ``name`` is in the active whitelist
          for ``(self.touchpoint, current_phase)``.
        """
        # Recompute phase so the LLM can't game the whitelist by advancing
        # phase in the same turn it tries an off-phase tool.
        phase = self._profile().onboarding_phase or "identify"
        allowed = set(whitelist_for(self.touchpoint, phase))
        if name not in allowed:
            return {
                "ok": False,
                "error": "tool_not_in_whitelist",
                "tool": name,
                "touchpoint": self.touchpoint,
                "phase": phase,
            }
        method = TOOL_METHODS.get(name)
        if method is None:
            return {"ok": False, "error": f"unknown tool: {name}"}
        safe_args = {k: v for k, v in (args or {}).items() if k != "user_id"}
        try:
            return method(self, **safe_args)
        except TypeError as e:
            # Wrong arity / unexpected kwarg from the LLM — surface to the
            # model as a tool-result error, not a 500.
            logger.warning("Bad args for tool %s: %s", name, e)
            return {"ok": False, "error": "bad_arguments", "detail": str(e)}


# Method allowlist — must be kept in sync with build_function_declarations.
TOOL_METHODS = {
    "ask_user": ToolBox.ask_user,
    "finish_touchpoint": ToolBox.finish_touchpoint,
    "save_field": ToolBox.save_field,
    "update_extra": ToolBox.update_extra,
    "ingest_asset": ToolBox.ingest_asset,
    "advance_phase": ToolBox.advance_phase,
    "mark_good_enough": ToolBox.mark_good_enough,
    "propose_brief": ToolBox.propose_brief,
}
