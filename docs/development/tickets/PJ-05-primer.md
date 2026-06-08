# PJ-05 Primer

**Source plan:** [`PJ-00-phase-plan.md`](PJ-00-phase-plan.md) — §6.2 (Tools), §6.4 (Safety rails), §7.5 (Good-enough gate), §3 decision 16 (GRILL Q6 — propose_brief).
**For:** New Cursor Agent session
**Date:** 2026-06-08
**Previous work:** PJ-04 (agent endpoint scaffold) merged. See `docs/development/DEVLOG.md`.
**Status:** ⏳ Not started

---

# Ticket PJ-05: Agent tools + validators

## What Is This Ticket?

PJ-04 stood up the loop with two stub tools (`ask_user`, `finish_touchpoint`). This ticket fills in the **real** tools: `save_field`, `update_extra`, `ingest_asset`, `advance_phase`, `mark_good_enough`, and a touchpoint-scoped `propose_brief`. Every tool is a `ToolBox` bound method (so `user_id` stays closure-captured), every tool has server-side validation, and every tool obeys the per-phase / per-touchpoint **whitelist**.

The whitelist is the source of authority. The LLM might call `mark_good_enough` during the `identify` phase; the backend rejects it. The LLM might call `advance_phase('assets')` before typed-core fields are filled; the backend rejects it. Backend is law; LLM is policy.

### Why It Matters

- These tools are the only legal way the LLM can mutate user state.
- Validation here is the difference between "agent learns the user's brand" and "agent corrupts the profile."
- `propose_brief` is the `pre_session_prep` touchpoint's hook (PJ-11); it shapes a brief without writing to `brand_profile`.

---

## What Was Already Done

- **PJ-04** — `ToolBox`, the conversation loop, stub `ask_user` / `finish_touchpoint`.
- **PJ-03** — `brand_assets.extracted_facts` available for `ingest_asset` to read.
- `app/models/brand_profile.py` — typed columns; the allowlist of writable fields lives here.

---

## What This Ticket Must Accomplish

### Goal

Implement seven tools on `ToolBox` with server-side validation + per-phase whitelisting. After this ticket, the LLM can fill a `brand_profile` from a conversation, and the backend physically prevents schema, scope, or phase violations.

### Deliverables Checklist

#### A. Implementation

- [ ] `ToolBox.save_field(name, value, confidence, rationale)` — writes one typed column. `name` must be in `TYPED_COLUMNS` allowlist (see §6.2). Value validated per column.
- [ ] `ToolBox.update_extra(key, value, confidence, rationale)` — merges into `brand_profile.extras`. Key normalized to `snake_case`. Value must be JSON-serializable.
- [ ] `ToolBox.ingest_asset(asset_id, derive_palette, derive_fonts)` — reads `brand_assets.extracted_facts` for the asset, returns the relevant subset. Asserts `asset.user_id == self.user_id`. If `derive_palette=True` and palette present, also calls `save_field('palette_primary_hex', …)` etc.
- [ ] `ToolBox.advance_phase(next_phase, why)` — updates `brand_profile.onboarding_phase`. Only callable when `touchpoint == 'onboarding'`. Phase order strictly enforced (identify → core → extras → assets → good_enough → complete; can't skip).
- [ ] `ToolBox.mark_good_enough()` — sets `good_enough_at = now()`. Rejected unless all gate conditions met (§7.5).
- [ ] `ToolBox.propose_brief(audience, persona, campaign_goal, key_message, creative_brief)` — `pre_session_prep` ONLY. Validates the full brief shape, attaches to the response payload as `proposed_brief`, does NOT write to `brand_profile`.
- [ ] `app/api/agent/whitelist.py` — `whitelist_for(touchpoint, phase) -> list[ToolDecl]`. Encodes:
  - `onboarding` phase=`identify`: `save_field`, `advance_phase`, `ask_user`, `finish_touchpoint`
  - `onboarding` phase=`core`: + `update_extra`
  - `onboarding` phase=`extras`: same as core
  - `onboarding` phase=`assets`: + `ingest_asset`
  - `onboarding` phase=`good_enough`: + `mark_good_enough`
  - `post_session`: `save_field`, `update_extra`, `ask_user`, `finish_touchpoint`
  - `pre_session_prep`: `propose_brief`, `ask_user`, `finish_touchpoint` (read-only on profile)
  - `refine`: `save_field`, `update_extra`, `ingest_asset`, `ask_user`, `finish_touchpoint`
- [ ] `app/api/agent/validators.py` — column-specific validators:
  - `palette_*_hex` matches `^#[0-9a-fA-F]{6}$`
  - `value_props`, `tone_descriptors`, `avoid_phrases` are list[str] with len ≥ 1
  - `do_dont_rules` matches `{"do": [str], "dont": [str]}` shape
  - `industry` lowercased to snake_case
  - All other typed columns are non-empty str
- [ ] Update `app/api/routes/agent.py` to call `whitelist_for(touchpoint, profile.onboarding_phase)` when building `tool_decls`.

#### B. Tests (`tests/test_api/test_agent_tools.py`)

- [ ] TDD first.
- [ ] `test_save_field_valid` — `save_field("business_name", "Acme Co", …)` writes.
- [ ] `test_save_field_unknown_column_rejected` — `save_field("hax", "x")` returns validation error result.
- [ ] `test_save_field_invalid_hex_rejected` — `save_field("palette_primary_hex", "not-a-hex")` rejected.
- [ ] `test_update_extra_snake_case_normalization` — `update_extra("Subjects Taught", [...])` writes key `subjects_taught`.
- [ ] `test_ingest_asset_other_user_rejected` — asset belongs to user B, tool called with user A's ToolBox → rejected.
- [ ] `test_advance_phase_skip_rejected` — current `identify`, try jump to `assets` → rejected.
- [ ] `test_advance_phase_in_non_onboarding_rejected` — touchpoint=`refine`, call `advance_phase` → rejected.
- [ ] `test_mark_good_enough_blocked_without_typed_core` — missing `audience` → rejected with structured reason.
- [ ] `test_mark_good_enough_passes_when_complete` — all required filled → sets `good_enough_at`.
- [ ] `test_propose_brief_only_in_pre_session_prep` — call from `onboarding` → rejected.
- [ ] `test_propose_brief_does_not_write_profile` — call returns shape; profile row unchanged.
- [ ] `test_whitelist_excludes_mark_good_enough_in_identify` — assert tool not present.

#### C. Integration Expectations

- [ ] None of the tool function declarations have `user_id` in their parameter schema (re-verify the closure property from PJ-04).
- [ ] Validation errors are returned as tool results (so the LLM can adapt), not raised exceptions.
- [ ] `propose_brief` result lands in the `/converse` response under a new `proposed_brief` field.

#### D. Documentation

- [ ] DEVLOG entry: `## 2026-XX-YY — PJ-05: Agent tools + validators (✅)`.

---

## Branch & Merge Workflow

```bash
git switch final-submission && git pull
git switch -c feature/PJ-05-agent-tools
git add app/api/agent/ tests/test_api/test_agent_tools.py
git commit -m "feat(PJ-05): real agent tools + per-phase whitelist + validators"
git push -u origin feature/PJ-05-agent-tools
```

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `app/api/agent/whitelist.py` | Per-touchpoint × per-phase tool allowlist |
| `app/api/agent/validators.py` | Column-specific value validators |
| `tests/test_api/test_agent_tools.py` | One test per tool + gate scenario |

### Files to Modify

| File | Action |
|------|--------|
| `app/api/agent/toolbox.py` | Add the seven real tool methods |
| `app/api/routes/agent.py` | Use `whitelist_for()` to scope `tool_decls`; surface `proposed_brief` in response |

### Files to NOT Modify

- `app/models/*` — schemas frozen.
- `generate/brief_expansion.py` — that's PJ-09.

### Files to READ for Context

| File | Why |
|------|-----|
| `docs/development/tickets/PJ-00-phase-plan.md` §6.2, §6.4, §7.5 | Tool spec, safety rails, gate conditions |
| `app/api/agent/toolbox.py` (from PJ-04) | Closure pattern to extend |

---

## Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Backend is law | PJ-00 §3 decision 10 | LLM proposes, backend disposes; every tool validated server-side |
| Per-phase whitelist | PJ-00 §6.4 | Tools physically unavailable to LLM in wrong phase |
| `propose_brief` is read-only | PJ-00 §3 decision 16 (GRILL Q6) | Returns brief draft to frontend; no `brand_profile` writes |
| Validation errors loop back | PJ-00 §6.3 | LLM sees the error result and adapts, doesn't surface to user |
| `extras` is normalized | PJ-00 §6.2 | snake_case keys, JSON-serializable values |

---

## Suggested Implementation Pattern

```python
# app/api/agent/validators.py
import re

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

TYPED_COLUMNS = {
    "business_name": "str",
    "industry": "snake_case_str",
    "audience": "str",
    "mission": "str",
    "value_props": "str_list",
    "tone_descriptors": "str_list",
    "avoid_phrases": "str_list",
    "do_dont_rules": "do_dont",
    "palette_primary_hex": "hex",
    "palette_secondary_hex": "hex",
    "palette_accent_hex": "hex",
}

def validate(name: str, value):
    if name not in TYPED_COLUMNS:
        return {"ok": False, "error": f"unknown_column:{name}"}
    kind = TYPED_COLUMNS[name]
    if kind == "hex" and not (isinstance(value, str) and HEX.match(value)):
        return {"ok": False, "error": "invalid_hex_format"}
    if kind == "str_list":
        if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
            return {"ok": False, "error": "must_be_nonempty_string_list"}
    if kind == "do_dont":
        if not (isinstance(value, dict) and set(value) == {"do", "dont"}):
            return {"ok": False, "error": "must_be_do_dont_object"}
    if kind in ("str", "snake_case_str"):
        if not isinstance(value, str) or not value.strip():
            return {"ok": False, "error": "must_be_nonempty_string"}
        if kind == "snake_case_str":
            value = value.lower().strip().replace(" ", "_")
    return {"ok": True, "value": value}
```

```python
# app/api/agent/toolbox.py — extending PJ-04
from datetime import datetime, timezone
from app.api.agent.validators import validate

class ToolBox:
    # ... (PJ-04 fields + ask_user/finish_touchpoint)

    def save_field(self, name: str, value, confidence: float, rationale: str) -> dict:
        v = validate(name, value)
        if not v["ok"]:
            return {"ok": False, "error": v["error"]}
        from app.models.brand_profile import BrandProfile
        row = self.db.query(BrandProfile).get(self.user_id)
        setattr(row, name, v["value"])
        self.db.commit()
        return {"ok": True, "field": name, "stored": v["value"]}

    def update_extra(self, key: str, value, confidence: float, rationale: str) -> dict:
        try:
            import json; json.dumps(value)
        except Exception:
            return {"ok": False, "error": "value_not_json_serializable"}
        key_snake = key.lower().strip().replace(" ", "_")
        from app.models.brand_profile import BrandProfile
        row = self.db.query(BrandProfile).get(self.user_id)
        extras = dict(row.extras or {})
        extras[key_snake] = {"value": value, "confidence": confidence, "rationale": rationale}
        row.extras = extras
        self.db.commit()
        return {"ok": True, "key": key_snake}

    def mark_good_enough(self) -> dict:
        from app.models.brand_profile import BrandProfile
        row = self.db.query(BrandProfile).get(self.user_id)
        missing = []
        for col in ("business_name", "industry", "audience", "mission"):
            if not getattr(row, col):
                missing.append(col)
        if not row.value_props or len(row.value_props) < 2:
            missing.append("value_props>=2")
        if not row.tone_descriptors or len(row.tone_descriptors) < 2:
            missing.append("tone_descriptors>=2")
        if missing:
            return {"ok": False, "error": "gate_not_met", "missing": missing}
        row.good_enough_at = datetime.now(timezone.utc)
        self.db.commit()
        return {"ok": True, "good_enough_at": row.good_enough_at.isoformat()}
```

```python
# app/api/agent/whitelist.py
ORDER = ["identify", "core", "extras", "assets", "good_enough", "complete"]

def whitelist_for(touchpoint: str, phase: str) -> list[str]:
    base = ["ask_user", "finish_touchpoint"]
    if touchpoint == "onboarding":
        tools = ["save_field", "advance_phase"] + base
        if phase in ("core", "extras", "assets", "good_enough"):
            tools.append("update_extra")
        if phase in ("assets", "good_enough"):
            tools.append("ingest_asset")
        if phase == "good_enough":
            tools.append("mark_good_enough")
        return tools
    if touchpoint == "post_session":
        return ["save_field", "update_extra"] + base
    if touchpoint == "pre_session_prep":
        return ["propose_brief"] + base
    if touchpoint == "refine":
        return ["save_field", "update_extra", "ingest_asset"] + base
    return base
```

---

## Edge Cases to Handle

1. LLM calls `save_field` with `value=None` → validator rejects, LLM sees `must_be_nonempty_string`, asks user.
2. LLM calls `advance_phase` to the same phase it's in — accept idempotently (no-op).
3. `update_extra` with a key colliding with a typed column name (e.g., key=`audience`) — reject, point to `save_field` in the error message.
4. `ingest_asset` for an asset whose vision pass failed (`extracted_facts.error` present) — return the error to the LLM so it asks the user manually.
5. `propose_brief` called outside `pre_session_prep` — whitelist would already exclude it, but defense-in-depth: tool body re-checks `self.touchpoint`.
6. `mark_good_enough` called twice — second call is a no-op, returns same `good_enough_at`.
7. Concurrency: two `/converse` requests from the same user racing — last write wins on `brand_profile`; not catastrophic for v1.

---

## Definition of Done

- [ ] All twelve tests pass.
- [ ] No tool declaration has `user_id` in its parameter schema (re-checked in tests).
- [ ] Whitelist excludes `mark_good_enough` in `identify` phase.
- [ ] `propose_brief` returns brief shape; profile row stays unchanged after the call.
- [ ] `ruff check .` clean.
- [ ] DEVLOG entry prepended.
- [ ] Feature branch pushed.

---

## Estimated Time

| Task | Estimate |
|------|----------|
| `validators.py` + unit tests | 60 min |
| `whitelist.py` + unit tests | 30 min |
| Seven tool methods on `ToolBox` | 150 min |
| Integration tests | 120 min |
| `agent.py` wiring (`propose_brief` in response, whitelist call) | 30 min |
| DEVLOG + commit | 15 min |
| **Total** | **~1.5 days** |

---

## After This Ticket: What Comes Next

- **PJ-06** — Onboarding system prompt (uses these tools per phase)
- **PJ-10** — Post-session reflection (uses `save_field`/`update_extra`)
- **PJ-11** — Pre-session prep (uses `propose_brief`)
