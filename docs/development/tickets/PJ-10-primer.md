# PJ-10 Primer

**Source plan:** [`PJ-00-phase-plan.md`](PJ-00-phase-plan.md) — §8.2 (`post_session` touchpoint).
**For:** New Cursor Agent session
**Date:** 2026-06-08
**Previous work:** PJ-05 (tools), PJ-07 (`<Chat />`), PJ-09 (pipeline rewire) merged. See `docs/development/DEVLOG.md`.
**Status:** ⏳ Not started

---

# Ticket PJ-10: Post-session reflection touchpoint

## What Is This Ticket?

The `post_session` touchpoint is the "grows with you" promise made concrete. When a pipeline session completes, a modal auto-opens on the session detail page. The agent reads the session's ledger summary (top dimensions the winner won on, the rejection reasons for losers) and asks 1–2 short reflection questions like:

> "Your best-scoring variant won on emotional resonance via the parent-anxiety angle. Should I make that the default emotional angle for future sessions?"

If the user says yes, the agent calls `save_field` or `update_extra` and the *next* session's brief expansion picks it up. That's the feedback loop in action.

### Why It Matters

- It's the most visible "memory" feature — users see the system encoding what worked.
- Validates the §15.5 success criterion: "Post-session reflection writes a new `extras` key when the user accepts the assistant's suggestion; the next session's brief reflects it."
- Tests that PJ-09's rewire actually picks up newly-written profile fields.

---

## What Was Already Done

- **PJ-05** — `save_field`, `update_extra` tools available in `post_session` touchpoint per the whitelist.
- **PJ-06** — `build_post_session_prompt(profile, session_summary)` exists.
- **PJ-07** — `<Chat />` component ready to be reused.
- **PJ-09** — Pipeline reads `brand_profile`, so any field written here flows into next session.
- Existing `iterate/ledger_reader.py` and the ledger event model from PI provide a summary-extraction path.
- `app/frontend/src/views/SessionDetail.tsx` (or equivalent) — current session detail view.

---

## What This Ticket Must Accomplish

### Goal

Auto-open a chat modal on session completion with a session summary in the prompt. Agent asks 1–3 reflection questions, writes back via `save_field` / `update_extra`, exits via `finish_touchpoint`.

### Deliverables Checklist

#### A. Implementation — Backend

- [ ] `app/api/agent/session_summary.py` — `build_session_summary(session_id, user_id) -> dict` reads the session's ledger and returns:
  - `winner_variant_type`, `winner_composite_score`
  - `top_dimensions` — the 2–3 dimensions where the winner most outperformed the mean
  - `loser_rejection_reasons` — top 2 worst-dim rationales across non-winners
  - `media_type` (image/video)
- [ ] Modify `app/api/routes/agent.py` — when `touchpoint == 'post_session'`, fetch the session summary via the helper and inline it into the prompt passed to `build_post_session_prompt`.
- [ ] Modify `build_post_session_prompt` in `app/api/agent/prompts.py` (from PJ-06) to take the summary dict as a second arg and inline it.

#### B. Implementation — Frontend

- [ ] `app/frontend/src/components/PostSessionReflectionModal.tsx` — modal wrapping `<Chat touchpoint="post_session" sessionId={...} />`. Dismissible (X button + "Maybe later" link).
- [ ] Modify `app/frontend/src/views/SessionDetail.tsx`:
  - Watch session `status`. When it transitions to `completed`, auto-open the modal once per session per user (use a sessionStorage key like `pj10_reflected:<session_id>`).
  - User can dismiss; dismissal also sets the sessionStorage key.
  - On `onCompleted`, close modal silently.

#### C. Tests

- [ ] `tests/test_api/test_session_summary.py`:
  - `test_summary_picks_winner_and_top_dimensions` — synthetic ledger → correct winner + top dims.
  - `test_summary_returns_loser_rejection_reasons` — non-winner with `rejection_reason` → reasons surfaced.
  - `test_summary_for_video_session_has_media_type_video`.
- [ ] `tests/test_api/test_post_session_converse.py`:
  - `test_post_session_prompt_includes_summary` — POST `/converse` with `touchpoint='post_session'` + `session_id` → assert the system prompt to Gemini contained "winner_variant_type" or the actual values.
  - `test_post_session_writes_extras_when_user_accepts` — full LLM stub turn → `update_extra` called → row updated.
- [ ] `app/frontend/tests-e2e/post_session_reflection.spec.ts`:
  - Run a pipeline session locally (or seed a `completed` session).
  - Navigate to `/sessions/:id` → modal auto-opens.
  - Send accept message → modal closes → returning to the session detail page, no auto-open.
- [ ] Integration test (manual or scripted): write an `extras` key via reflection, then create + run a new session; assert the next session's brief expansion mentions the key. Doc in DEVLOG.

#### D. Documentation

- [ ] DEVLOG entry: `## 2026-XX-YY — PJ-10: Post-session reflection touchpoint (✅)`.
- [ ] Include a screenshot or transcript showing one full reflection cycle.

---

## Branch & Merge Workflow

```bash
git switch final-submission && git pull
git switch -c feature/PJ-10-post-session-reflection
git add app/api/agent/session_summary.py app/api/agent/prompts.py app/api/routes/agent.py app/frontend/src/ tests/
git commit -m "feat(PJ-10): post-session reflection touchpoint + auto-open modal"
git push -u origin feature/PJ-10-post-session-reflection
```

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `app/api/agent/session_summary.py` | Ledger → summary dict for the agent prompt |
| `app/frontend/src/components/PostSessionReflectionModal.tsx` | The modal |
| `tests/test_api/test_session_summary.py` | Summary tests |
| `tests/test_api/test_post_session_converse.py` | End-to-end touchpoint tests |
| `app/frontend/tests-e2e/post_session_reflection.spec.ts` | E2E |

### Files to Modify

| File | Action |
|------|--------|
| `app/api/agent/prompts.py` | `build_post_session_prompt` accepts summary dict |
| `app/api/routes/agent.py` | Dispatch summary fetch for `post_session` |
| `app/frontend/src/views/SessionDetail.tsx` | Auto-open modal on status transition |

### Files to NOT Modify

- `iterate/ledger_reader.py` — read-only consumer.
- `app/api/agent/toolbox.py`, `whitelist.py`, `validators.py` — frozen.

### Files to READ for Context

| File | Why |
|------|-----|
| `iterate/ledger_events.py` | Ledger event types (`MediaEvaluation` carries winner + rejection_reason from PI) |
| `iterate/ledger_reader.py` | How to load + filter events |
| `app/frontend/src/views/SessionDetail.tsx` | Current view to extend |
| `docs/development/tickets/PJ-00-phase-plan.md` §8.2 | Touchpoint spec |

---

## Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Triggered, not always-on | PJ-00 §3 decision 3 | Modal pops once per session per user; dismissible |
| Summary in prompt, not as tool result | PJ-00 §8.2 | LLM sees the ledger summary as part of system context |
| Tool whitelist excludes `mark_good_enough` | PJ-00 §6.2 + PJ-05 whitelist | Post-session can't gate-flip the profile |
| Feedback loop closes via next pipeline run | PJ-09 + PJ-10 | Profile write here → brief expansion next time |

---

## Suggested Implementation Pattern

```python
# app/api/agent/session_summary.py
from iterate.ledger_reader import LedgerReader
from pathlib import Path

def build_session_summary(session_id: str, user_id: str) -> dict:
    path = Path(f"data/sessions/{session_id}/ledger.jsonl")
    if not path.exists():
        return {"error": "ledger not found"}
    reader = LedgerReader(str(path))
    me_events = [e for e in reader.events() if e.get("event_type") == "MediaEvaluation"]
    if not me_events:
        return {"error": "no MediaEvaluation events"}
    winner = next((e for e in me_events if e["outputs"].get("is_winner")), me_events[0])
    losers = [e for e in me_events if not e["outputs"].get("is_winner")]
    return {
        "winner_variant_type": winner["outputs"].get("variant_type"),
        "winner_composite_score": winner["outputs"].get("composite_score"),
        "top_dimensions": _top_distinguishing(winner, me_events, k=3),
        "loser_rejection_reasons": [
            l["outputs"].get("rejection_reason", {}).get("worst_dimension_rationale")
            for l in losers[:2]
        ],
        "media_type": winner["outputs"].get("media_type"),
    }
```

```python
# app/api/agent/prompts.py — addition
POST_SESSION_PREAMBLE = """## Touchpoint: Post-session reflection
A session just finished. Here's the summary:
{summary_block}

Ask 1–2 short reflection questions to learn what worked and what didn't.
If the user confirms a pattern, call `save_field` or `update_extra` to encode it
for future sessions. After 1–3 turns, call `finish_touchpoint(summary=...)`.
Do NOT ask for permission to call `finish_touchpoint`; just close warmly when
you have what you need or the user disengages."""

def build_post_session_prompt(profile, summary: dict) -> str:
    summary_block = (
        f"- Winner: {summary['winner_variant_type']} (composite "
        f"{summary['winner_composite_score']:.1f})\n"
        f"- Top dims: {summary['top_dimensions']}\n"
        f"- Loser reasons: {summary['loser_rejection_reasons']}"
    ) if "error" not in summary else "(summary unavailable)"
    return "\n\n".join([
        IDENTITY,
        POST_SESSION_PREAMBLE.format(summary_block=summary_block),
        _snapshot(profile),
    ])
```

```tsx
// app/frontend/src/components/PostSessionReflectionModal.tsx
import { Chat } from './Chat'

export function PostSessionReflectionModal({ sessionId, onClose }) {
  return (
    <ModalShell onClose={onClose} title="Quick reflection">
      <Chat
        touchpoint="post_session"
        sessionId={sessionId}
        onCompleted={() => onClose()}
      />
      <button onClick={onClose} className="link">Maybe later</button>
    </ModalShell>
  )
}
```

```tsx
// app/frontend/src/views/SessionDetail.tsx — addition
useEffect(() => {
  if (session?.status === 'completed') {
    const key = `pj10_reflected:${session.session_id}`
    if (!sessionStorage.getItem(key)) {
      setReflectionOpen(true)
    }
  }
}, [session?.status])

const handleReflectionClose = () => {
  sessionStorage.setItem(`pj10_reflected:${session.session_id}`, '1')
  setReflectionOpen(false)
}
```

---

## Edge Cases to Handle

1. Session ledger missing or empty — summary returns `{"error": ...}`; prompt falls back to a generic "How did this session go?" question.
2. Session completed before PJ ships (pre-PJ) — no reflection modal (sessionStorage check + status transition is the trigger). Pre-existing completed sessions are not retroactively prompted.
3. User dismisses modal → returns to page → modal does NOT re-open (sessionStorage flag).
4. Modal opens during another user action — keep it dismissible, never block the page.
5. Agent calls `save_field` for a typed column that conflicts with onboarding-set value — the conflict is fine; latest wins, with the rationale recorded in `conversation_messages`.
6. Pipeline failed (`status='failed'`) — modal does NOT open (we only prompt on `completed`).

---

## Definition of Done

- [ ] All listed backend + E2E tests pass.
- [ ] Manual: run a small pipeline session, watch modal auto-open, accept a suggestion, confirm DB row updated.
- [ ] Manual: dismiss modal → confirm no re-open on refresh.
- [ ] Cross-session check: write an `extras` key via reflection, kick off a new session, verify the brief expansion incorporates it.
- [ ] `ruff check .` + `pytest` clean.
- [ ] DEVLOG entry prepended.
- [ ] Feature branch pushed.

---

## Estimated Time

| Task | Estimate |
|------|----------|
| `session_summary.py` + tests | 90 min |
| Prompt builder update | 30 min |
| Modal + SessionDetail integration | 90 min |
| E2E spec | 90 min |
| End-to-end manual flow + cross-session verification | 90 min |
| DEVLOG + commit | 15 min |
| **Total** | **~1 day** |

---

## After This Ticket: What Comes Next

- **PJ-11** — Pre-session prep touchpoint (next-up of the four)
- **PJ-13** — Verification gate exercises the full feedback loop
