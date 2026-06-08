# PJ-11 Primer

**Source plan:** [`PJ-00-phase-plan.md`](PJ-00-phase-plan.md) — §8.3 (`pre_session_prep` touchpoint) and §3 decision 16 (GRILL Q6 — chat THEN form, `propose_brief` tool).
**For:** New Cursor Agent session
**Date:** 2026-06-08
**Previous work:** PJ-05 (tools, esp. `propose_brief`), PJ-07 (`<Chat />`), PJ-09 (gated session create) merged. See `docs/development/DEVLOG.md`.
**Status:** ⏳ Not started

---

# Ticket PJ-11: Pre-session prep touchpoint

## What Is This Ticket?

When a user clicks "Create Session" they should not start with an empty form. This ticket shows a `pre_session_prep` chat modal first: the agent reads the user's `brand_profile` and proposes a complete brief draft (`audience`, `persona`, `campaign_goal`, `key_message`, `creative_brief`). The user refines via 4–6 chat turns. When they accept, the existing `NewSessionForm` opens with all 5 brief-shaped fields **pre-filled**. The user still picks technical fields (aspect_ratio, model, video duration, etc.) on the form.

Per GRILL Q6 (PJ-00 §3 decision 16), the pre-session prep is **chat THEN form**, not chat *instead of* form. And it uses the new `propose_brief` tool (from PJ-05) that returns the draft to the frontend WITHOUT writing to `brand_profile`.

### Why It Matters

- Closes the loop: user's brand knowledge directly seeds every session.
- Validates the §15.3 success criterion: ads reference the user's mission, value props, and audience.
- `propose_brief` is the first read-only-on-profile tool path — a useful pattern for future touchpoints.

---

## What Was Already Done

- **PJ-05** — `ToolBox.propose_brief(audience, persona, campaign_goal, key_message, creative_brief)` validated + returned in the `/converse` response under `proposed_brief`.
- **PJ-06** — `build_pre_session_prep_prompt(profile, session_type)` exists.
- **PJ-07** — `<Chat />` reusable.
- **PJ-09** — Session create gate verified; passes once a profile is good enough.
- Existing `NewSessionForm` somewhere under `app/frontend/src/` — find it and identify the 5 brief-shaped fields.

---

## What This Ticket Must Accomplish

### Goal

Show a `pre_session_prep` chat modal before `NewSessionForm`. Agent proposes a brief; user refines via chat; on accept, `NewSessionForm` opens with the 5 brief fields pre-filled. Technical fields stay on the form.

### Deliverables Checklist

#### A. Implementation — Backend

- [ ] Confirm `propose_brief` from PJ-05 is whitelisted only for `pre_session_prep` (it already is — verify).
- [ ] Confirm `agent.py` returns `proposed_brief` in the response when the tool was called. If not, wire it.
- [ ] Refine `build_pre_session_prep_prompt(profile, session_type)` in `app/api/agent/prompts.py` to:
  - Open with the agent proposing a complete brief based on the profile.
  - Ask "Want to refine any of these?" as the second turn.
  - Call `propose_brief` exactly once with the final values, then `finish_touchpoint`.
  - For video sessions, the `creative_brief` should include action/motion hints; for image, composition hints.

#### B. Implementation — Frontend

- [ ] `app/frontend/src/components/PreSessionPrepModal.tsx` — modal wrapping `<Chat touchpoint="pre_session_prep" initialMessage="Let me draft a brief for you…" onCompleted={onProposed} />`. Props: `sessionType`, `onProposed(brief)`, `onCancel`.
- [ ] Modify the entry-point to `NewSessionForm` (likely a "Create Session" button on the sessions list or dashboard):
  1. Click "Create Session" → open `PreSessionPrepModal`.
  2. When `onProposed` fires with a brief dict, close modal and open `NewSessionForm` with `defaultValues` set from the brief.
  3. User can also "Skip — fill it manually" link in the modal → close + open empty form (existing behavior).
- [ ] Modify `NewSessionForm` to accept `defaultValues` (likely already supports via React Hook Form or controlled inputs — wire it if not).

#### C. Tests

- [ ] `tests/test_api/test_propose_brief_flow.py`:
  - `test_propose_brief_returned_in_response` — stub LLM calls `propose_brief` → response has `proposed_brief` key.
  - `test_propose_brief_does_not_write_profile` — profile timestamp unchanged after the call.
  - `test_propose_brief_validation_rejects_partial` — call with missing `audience` → tool result `ok=False`.
- [ ] `app/frontend/tests-e2e/pre_session_prep.spec.ts`:
  - Sign in as user with completed profile.
  - Click "Create Session" → modal opens with agent's brief draft.
  - Send "good, accept" → modal closes → form opens with 5 fields pre-filled.
  - Submit form → session created (verified via session list).
  - Re-run flow, click "Skip — fill it manually" → form opens empty.

#### D. Documentation

- [ ] DEVLOG entry: `## 2026-XX-YY — PJ-11: Pre-session prep touchpoint (✅)`.
- [ ] Note the chat-THEN-form pattern explicitly (it's a recurring UX question).

---

## Branch & Merge Workflow

```bash
git switch final-submission && git pull
git switch -c feature/PJ-11-pre-session-prep
git add app/api/agent/prompts.py app/frontend/src/ tests/
git commit -m "feat(PJ-11): pre-session prep chat THEN form-prefill flow"
git push -u origin feature/PJ-11-pre-session-prep
```

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `app/frontend/src/components/PreSessionPrepModal.tsx` | The chat modal that runs before NewSessionForm |
| `tests/test_api/test_propose_brief_flow.py` | Backend tool flow tests |
| `app/frontend/tests-e2e/pre_session_prep.spec.ts` | E2E |

### Files to Modify

| File | Action |
|------|--------|
| `app/api/agent/prompts.py` | Tighten `build_pre_session_prep_prompt` per spec |
| `app/api/routes/agent.py` | Verify `proposed_brief` surfaced in response (likely already from PJ-05) |
| `NewSessionForm.tsx` (find under `app/frontend/src/`) | Accept `defaultValues` and pre-fill |
| Sessions list "Create Session" button location | Open modal first |

### Files to NOT Modify

- `app/api/agent/toolbox.py`, `whitelist.py`, `validators.py`.
- `<Chat />` itself.

### Files to READ for Context

| File | Why |
|------|-----|
| Current `NewSessionForm` component | Identify the 5 brief fields, form library in use |
| `docs/development/tickets/PJ-00-phase-plan.md` §8.3 + §3 decision 16 | Touchpoint spec + GRILL Q6 |
| `app/api/agent/toolbox.py` — `propose_brief` method | Confirm shape returned |

---

## Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Chat THEN form | PJ-00 §3 decision 16 (GRILL Q6) | Agent proposes the 5 brief fields; form stays for technical fields |
| `propose_brief` is read-only | PJ-00 §6.2 | Tool returns shape; never writes `brand_profile` |
| Single-touchpoint-only tool | PJ-00 §6.2 | `propose_brief` whitelisted ONLY for `pre_session_prep` |
| "Skip — fill it manually" escape | UX necessity | Power users / regression cases get the existing path |

---

## Suggested Implementation Pattern

```python
# app/api/agent/prompts.py — refined builder
PRE_SESSION_PREP_PREAMBLE = """## Touchpoint: Pre-session prep
The user is about to create a new {session_type} session. Their brand profile is
attached below. Your job, in 4–6 turns max:

1. Open with a complete draft brief proposing the 5 fields:
   audience, persona, campaign_goal, key_message, creative_brief.
   Anchor the proposal in their value props, mission, and tone.
2. Ask if they want to refine anything.
3. Iterate based on user feedback.
4. When user accepts (or after 2 refinement rounds), call `propose_brief`
   exactly once with the final values, then `finish_touchpoint`.

For {session_type} sessions, the `creative_brief` should emphasize:
- image: composition, visual style, key motif
- video: opening hook, action arc, closing line

Do NOT call `save_field` or `update_extra`. This touchpoint is read-only on the profile."""

def build_pre_session_prep_prompt(profile, session_type: str) -> str:
    return "\n\n".join([
        IDENTITY,
        PRE_SESSION_PREP_PREAMBLE.format(session_type=session_type),
        _snapshot(profile),
    ])
```

```tsx
// app/frontend/src/components/PreSessionPrepModal.tsx
import { Chat } from './Chat'

interface Props {
  sessionType: 'image' | 'video'
  onProposed: (brief: ProposedBrief) => void
  onCancel: () => void
}

export interface ProposedBrief {
  audience: string
  persona: string
  campaign_goal: string
  key_message: string
  creative_brief: string
}

export function PreSessionPrepModal({ sessionType, onProposed, onCancel }: Props) {
  return (
    <ModalShell onClose={onCancel} title="Let's prep your brief">
      <Chat
        touchpoint="pre_session_prep"
        onCompleted={(res) => {
          if (res.proposed_brief) onProposed(res.proposed_brief as ProposedBrief)
          else onCancel()  // touchpoint finished without a brief — treat as cancel
        }}
      />
      <button onClick={onCancel} className="link">Skip — fill it manually</button>
    </ModalShell>
  )
}
```

```tsx
// Sessions list / dashboard — Create Session button
const [prepOpen, setPrepOpen] = useState(false)
const [prefill, setPrefill] = useState<ProposedBrief | null>(null)
const [formOpen, setFormOpen] = useState(false)

<button onClick={() => setPrepOpen(true)}>Create session</button>

{prepOpen && (
  <PreSessionPrepModal
    sessionType={selectedType}
    onProposed={(brief) => { setPrepOpen(false); setPrefill(brief); setFormOpen(true) }}
    onCancel={() => { setPrepOpen(false); setFormOpen(true) }}
  />
)}

{formOpen && (
  <NewSessionForm defaultValues={prefill ?? {}} onClose={() => setFormOpen(false)} />
)}
```

---

## Edge Cases to Handle

1. Agent times out mid-conversation — user closes modal → opens empty form (don't lose the click).
2. Agent calls `propose_brief` with partial data — validator from PJ-05 rejects; LLM sees error and asks user for the missing piece.
3. User accepts very quickly (single turn) — `propose_brief` fires, `finish_touchpoint` fires, modal closes, form pre-filled. Smooth.
4. `NewSessionForm` already has logic for image vs video — pre-fill only the brief-shaped fields; leave aspect_ratio, model, duration alone.
5. User edits a pre-filled field on the form — the form value wins; agent has no callback after `finish_touchpoint`.
6. `propose_brief` not called by LLM (it just `finish_touchpoint`-ed) — frontend treats as cancel and opens empty form.
7. Profile not yet good_enough — Create Session would 403 anyway from PJ-09 gate. Modal never appears because user is redirected to `/onboarding` from PJ-07 redirect.

---

## Definition of Done

- [ ] All listed backend + E2E tests pass.
- [ ] Manual: complete a brand profile → click Create Session → modal flows → form pre-fills → session creates successfully.
- [ ] Manual: "Skip — fill it manually" → empty form, sessions still creatable.
- [ ] No `brand_profile.updated_at` movement after a `pre_session_prep` conversation (read-only verified).
- [ ] `ruff check .` + `pytest` clean.
- [ ] DEVLOG entry prepended.
- [ ] Feature branch pushed.

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Prompt refinement | 45 min |
| Modal component | 60 min |
| `NewSessionForm` pre-fill plumbing | 90 min |
| "Create Session" entry-point wiring | 30 min |
| Backend tests | 60 min |
| E2E spec | 90 min |
| Manual smoke + iteration | 90 min |
| DEVLOG + commit | 15 min |
| **Total** | **~1.5 days** |

---

## After This Ticket: What Comes Next

- **PJ-12** — Documentation refresh (writes about all four touchpoints)
- **PJ-13** — Verification gate exercises the full flow end-to-end
