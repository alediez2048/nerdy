# PJ-04 Primer

**Source plan:** [`PJ-00-phase-plan.md`](PJ-00-phase-plan.md) — §6 (Conversation loop) and §3 decisions 11–12 (GRILL Q1, Q2).
**For:** New Cursor Agent session
**Date:** 2026-06-08
**Previous work:** PJ-01 (models), PJ-02 (assets API), PJ-03 (vision pass) merged. See `docs/development/DEVLOG.md`.
**Status:** ⏳ Not started

---

# Ticket PJ-04: Agent endpoint scaffold

## What Is This Ticket?

The heart of PJ: a single `POST /api/agent/converse` endpoint that all four touchpoints (`onboarding`, `post_session`, `pre_session_prep`, `refine`) hit. This ticket lands the **scaffold** — the request/response shape, mode dispatch, message persistence, profile loading, and the Gemini function-calling loop infrastructure. Real tools come in PJ-05; real prompts come in PJ-06.

Two load-bearing decisions shape this ticket:

- **GRILL Q1 (decision 11):** The agent runs on a **separate host-side key** `AGENT_GEMINI_API_KEY`, NOT the user's BYO key. The pipeline still needs BYO; the agent does not. Reason: onboarding precedes Settings, so requiring BYO before onboarding is a chicken-and-egg.
- **GRILL Q2 (decision 12):** `user_id` is **closure-bound**, never an LLM-visible argument. A per-request `ToolBox` captures `user_id` from the verified Clerk JWT; tool function signatures sent to Gemini omit `user_id`. Cross-tenant writes from the LLM surface are physically impossible.

### Why It Matters

- Every other PJ ticket (05, 06, 07, 10, 11) flows through this endpoint.
- Per-request `ToolBox` is the security boundary — get it wrong and any tool call could write to another user's profile.
- Bounded tool loop (MAX_TOOL_ITERATIONS = 8) is the cost cap.

---

## What Was Already Done

- **PJ-01** — `brand_profile`, `conversation_messages`, `brand_assets` tables.
- **PJ-02** — assets uploadable; `asset_id` references resolvable.
- **PJ-03** — vision pass populates `brand_assets.extracted_facts`.
- `AGENT_GEMINI_API_KEY` env var is already documented from PJ-03.
- `app/api/routes/user_keys.py` — auth dep pattern (Clerk JWT → `user_id`).

---

## What This Ticket Must Accomplish

### Goal

Stand up `POST /api/agent/converse` with mode dispatch, message persistence, profile load/upsert, closure-bound `ToolBox`, and a bounded Gemini function-calling loop. **No real tools yet** — register two stubs (`ask_user`, `finish_touchpoint`) so the loop terminates cleanly.

### Deliverables Checklist

#### A. Implementation

- [ ] `app/api/routes/agent.py` — the router with `POST /api/agent/converse`.
- [ ] `app/api/agent/toolbox.py` — `ToolBox` class. Constructor takes `user_id`, `db`, `touchpoint`, `session_id`. Captures all of them as instance state. Tool methods are bound methods.
- [ ] `app/api/agent/loop.py` — `run_conversation_turn(toolbox, profile, history, system_prompt, tools)` runs the Gemini function-calling loop with `MAX_TOOL_ITERATIONS = 8` and returns `(assistant_message, profile_snapshot, exit_reason)`.
- [ ] `app/api/agent/profile_loader.py` — `load_or_create_profile(db, user_id)`: returns existing row or upserts an empty one with `onboarding_phase='identify'`.
- [ ] `app/api/agent/messages.py` — append + load helpers for `conversation_messages`.
- [ ] Request schema: `{touchpoint, session_id?, user_message?, uploaded_asset_ids?}`.
- [ ] Response schema: `{assistant_message, phase, good_enough_now, profile_snapshot, asset_extractions?}`.
- [ ] 403 if `touchpoint != 'onboarding'` and no `brand_profile` row exists.
- [ ] Stubs registered: `ask_user(message)` (terminal — returns to user) and `finish_touchpoint(summary)` (terminal — sets `onboarding_phase='complete'` if touchpoint=onboarding).
- [ ] Loop returns 422 if a tool call fails validation, surfacing the error to the LLM (next iteration), not the user.

#### B. Tests (`tests/test_api/test_agent_converse.py`)

- [ ] TDD first.
- [ ] `test_first_converse_creates_profile` — empty user → POST `onboarding` → profile row exists.
- [ ] `test_converse_persists_user_and_assistant_messages` — POST with `user_message` → two rows in `conversation_messages` after the turn.
- [ ] `test_403_for_non_onboarding_without_profile` — fresh user → POST `post_session` → 403.
- [ ] `test_max_iterations_caps_loop` — stub Gemini to never call a terminal tool → loop exits after 8 iterations with a synthetic `ask_user`-equivalent message.
- [ ] `test_toolbox_user_id_not_in_function_schema` — introspect the tools registered for Gemini; assert `user_id` is NOT in any parameter list.
- [ ] `test_cross_tenant_save_field_rejected` — stub LLM to try writing for user B while authed as user A → write hits user A's profile only (it physically can't reach B because there's no `user_id` parameter).
- [ ] `test_history_loads_last_20_messages` — seed 25 messages, assert only the 20 most recent are passed to Gemini.

#### C. Integration Expectations

- [ ] Endpoint uses `AGENT_GEMINI_API_KEY` (not BYO).
- [ ] Auth dep mirrors `user_keys.py`.
- [ ] Vision-pass results (from PJ-03) are inlined into the system prompt context when `uploaded_asset_ids` is non-empty.
- [ ] `MAX_TOOL_ITERATIONS = 8`, `MAX_MESSAGES_RETURNED = 20` — constants, not magic numbers.

#### D. Documentation

- [ ] DEVLOG entry: `## 2026-XX-YY — PJ-04: Agent endpoint scaffold (✅)`.
- [ ] Note the closure-bound `ToolBox` security property explicitly.

---

## Branch & Merge Workflow

```bash
git switch final-submission && git pull
git switch -c feature/PJ-04-agent-endpoint-scaffold
# implement, run tests
git add app/api/routes/agent.py app/api/agent/ tests/test_api/test_agent_converse.py
git commit -m "feat(PJ-04): agent converse endpoint scaffold + ToolBox"
git push -u origin feature/PJ-04-agent-endpoint-scaffold
```

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `app/api/routes/agent.py` | The endpoint |
| `app/api/agent/toolbox.py` | Per-request closure capturing `user_id` |
| `app/api/agent/loop.py` | Gemini function-calling loop |
| `app/api/agent/profile_loader.py` | Load-or-create profile helper |
| `app/api/agent/messages.py` | Conversation message persistence |
| `tests/test_api/test_agent_converse.py` | Loop + scoping + persistence tests |

### Files to Modify

| File | Action |
|------|--------|
| `app/main.py` | Register the agent router |

### Files to NOT Modify

- `app/models/*` — schemas frozen at PJ-01.
- `app/workers/tasks/pipeline_task.py` — pipeline rewire is PJ-09.
- `app/api/routes/sessions.py` — gate is PJ-09.

### Files to READ for Context

| File | Why |
|------|-----|
| `app/api/routes/user_keys.py` | Auth-dep pattern |
| `app/workers/user_keys_loader.py` | Per-user resource loading pattern |
| `docs/development/tickets/PJ-00-phase-plan.md` §6 | Loop pseudocode, tool list, safety rails |

---

## Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Host-side key for agent | PJ-00 §3 decision 11 (GRILL Q1) | `AGENT_GEMINI_API_KEY` separate from BYO |
| Closure-bound user_id | PJ-00 §3 decision 12 (GRILL Q2) | `ToolBox` captures `user_id`; LLM never sees it as a tool parameter |
| Synchronous request/response | PJ-00 §3 decision 7 | One `/converse` call per turn, no SSE |
| Bounded loop | PJ-00 §6.4 | `MAX_TOOL_ITERATIONS = 8`, `MAX_MESSAGES_RETURNED = 20` |
| Tool whitelist server-side | PJ-00 §3 decision 10 | Backend not LLM enforces phase rules — set up in PJ-05 |

---

## Suggested Implementation Pattern

```python
# app/api/agent/toolbox.py
from dataclasses import dataclass
from sqlalchemy.orm import Session

@dataclass
class ToolBox:
    """Per-request closure. user_id is NEVER exposed to the LLM."""
    user_id: str
    db: Session
    touchpoint: str
    session_id: str | None

    # PJ-05 will add: save_field, update_extra, ingest_asset, ...
    # All bound methods. user_id is self.user_id, never a parameter.

    def ask_user(self, message: str) -> dict:
        return {"_terminal": True, "kind": "ask_user", "message": message}

    def finish_touchpoint(self, summary: str) -> dict:
        if self.touchpoint == "onboarding":
            # PJ-05 will validate good_enough_at is set first
            from app.models.brand_profile import BrandProfile
            row = self.db.query(BrandProfile).get(self.user_id)
            row.onboarding_phase = "complete"
            self.db.commit()
        return {"_terminal": True, "kind": "finish_touchpoint", "summary": summary}
```

```python
# app/api/agent/loop.py
import google.generativeai as genai
import os

MAX_TOOL_ITERATIONS = 8

def run_conversation_turn(toolbox, profile, history, system_prompt, tool_decls):
    genai.configure(api_key=os.environ["AGENT_GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=system_prompt, tools=tool_decls)
    chat = model.start_chat(history=history)

    last_message = None
    for _ in range(MAX_TOOL_ITERATIONS):
        resp = chat.send_message(...)
        fn_call = _extract_function_call(resp)
        if not fn_call:
            return {"assistant_message": resp.text, "exit_reason": "no_tool"}
        result = _dispatch(toolbox, fn_call)
        if result.get("_terminal"):
            return {"assistant_message": result.get("message") or result.get("summary"),
                    "exit_reason": result["kind"]}
        # feed tool result back, loop again
    return {"assistant_message": "(loop bound reached)", "exit_reason": "max_iter"}
```

```python
# app/api/routes/agent.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth import get_current_user_id
from app.db import get_session
from app.api.agent.toolbox import ToolBox
from app.api.agent.loop import run_conversation_turn
from app.api.agent.profile_loader import load_or_create_profile
from app.api.agent.messages import append_message, load_history

router = APIRouter(prefix="/api/agent", tags=["agent"])

class ConverseRequest(BaseModel):
    touchpoint: str
    session_id: str | None = None
    user_message: str | None = None
    uploaded_asset_ids: list[str] | None = None

@router.post("/converse")
def converse(req: ConverseRequest, user_id: str = Depends(get_current_user_id), db = Depends(get_session)):
    if req.touchpoint != "onboarding":
        from app.models.brand_profile import BrandProfile
        if not db.query(BrandProfile).get(user_id):
            raise HTTPException(403, "brand_profile_not_initialized")

    profile = load_or_create_profile(db, user_id)
    history = load_history(db, user_id, req.touchpoint, req.session_id, limit=20)
    if req.user_message:
        append_message(db, user_id, req.touchpoint, req.session_id, role="user", content=req.user_message)

    tb = ToolBox(user_id=user_id, db=db, touchpoint=req.touchpoint, session_id=req.session_id)
    # PJ-06 will build the real prompt + tool whitelist; here, stub:
    system_prompt = f"You are the onboarding agent. Touchpoint: {req.touchpoint}."
    tool_decls = [_decl_ask_user(), _decl_finish_touchpoint()]
    out = run_conversation_turn(tb, profile, history, system_prompt, tool_decls)

    append_message(db, user_id, req.touchpoint, req.session_id, role="assistant", content=out["assistant_message"])
    return {
        "assistant_message": out["assistant_message"],
        "phase": profile.onboarding_phase,
        "good_enough_now": profile.good_enough_at is not None,
        "profile_snapshot": _serialize(profile),
    }
```

The critical security property to verify in tests: **the function declarations passed to Gemini for `ask_user` and `finish_touchpoint` do NOT declare `user_id`**. Only `message` / `summary`. PJ-05 will follow the same rule for every other tool.

---

## Edge Cases to Handle

1. Empty `user_message` and empty `uploaded_asset_ids` — first-load case. Agent should respond with the opening greeting (LLM-driven; nothing to do server-side beyond running the loop).
2. Gemini returns an empty function-call list AND empty text — surface a default fallback message to keep UX from dead-ending.
3. Tool call returns a validation error — feed the error as a tool-result back to the LLM so it adapts, do NOT 422 to the user.
4. Profile row exists but `onboarding_phase IS NULL` (corrupted state) — coerce to `'identify'` and log a warning.
5. History contains malformed JSON in `tool_calls` — skip those rows; do not crash the load.
6. `AGENT_GEMINI_API_KEY` missing — fail fast at module import.

---

## Definition of Done

- [ ] All seven tests pass.
- [ ] Manual `curl POST /api/agent/converse` round-trips with stub tools.
- [ ] Closure-bound property visibly enforced: tool decls have no `user_id` field.
- [ ] `ruff check .` clean.
- [ ] DEVLOG entry prepended.
- [ ] Feature branch pushed.

---

## Estimated Time

| Task | Estimate |
|------|----------|
| ToolBox + closure scaffolding | 60 min |
| Loop + Gemini integration | 90 min |
| Profile loader + message persistence | 45 min |
| Endpoint + request/response | 45 min |
| Tests (esp. closure property test) | 120 min |
| DEVLOG + commit | 15 min |
| **Total** | **~1 day** |

---

## After This Ticket: What Comes Next

- **PJ-05** — Real tools (save_field, update_extra, ingest_asset, …) plug into `ToolBox`
- **PJ-06** — Real system prompt + per-phase tool whitelist replace the stub prompt
- **PJ-07** — Frontend `<Chat />` POSTs to `/api/agent/converse`
