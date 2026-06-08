# PJ-07 Primer

**Source plan:** [`PJ-00-phase-plan.md`](PJ-00-phase-plan.md) — §10 (Frontend chat UI).
**For:** New Cursor Agent session
**Date:** 2026-06-08
**Previous work:** PJ-04..PJ-06 merged (agent endpoint + tools + prompts). See `docs/development/DEVLOG.md`.
**Status:** ⏳ Not started

---

# Ticket PJ-07: Onboarding chat UI

## What Is This Ticket?

The backend can converse; the frontend can't yet. This ticket ships the **reusable `<Chat />` component** plus a dedicated `/onboarding` route with a 5-dot phase progress bar, file-drop, optimistic message UX, and an app-level redirect that forces new users into onboarding before they can access anything else.

`<Chat />` is the centerpiece — it'll be reused by Settings (PJ-08), SessionDetail post-session reflection (PJ-10), and NewSessionForm pre-session prep (PJ-11). Get the component contract right here and the four-touchpoint integration in §10.2 of PJ-00 falls out cleanly.

### Why It Matters

- This is what users *see* — the onboarding wall blocking new users until the brand profile is `good_enough`.
- The component contract is reused by three other touchpoints, so its props need to generalize.
- File-drop upload is the asset path; vision-pass polling lives here.

---

## What Was Already Done

- **PJ-02** — `POST /api/brand-assets` upload + `GET /api/brand-assets/{id}` serve.
- **PJ-03** — `POST /api/brand-assets/{id}/extract` + `GET .../status` for vision pass.
- **PJ-04..PJ-06** — `POST /api/agent/converse` returning `{assistant_message, phase, good_enough_now, profile_snapshot}`.
- `app/frontend/src/views/Settings.tsx` — view-component pattern (auth-gated, fetches once on mount).
- `app/frontend/src/api/userKeys.ts` — typed API-client pattern.

---

## What This Ticket Must Accomplish

### Goal

Ship `<Chat />`, `/onboarding` view with 5-dot progress + file-drop + optimistic UX, an API client for the agent + brand-assets endpoints, and a top-level redirect when `brand_profile.onboarding_phase != 'complete'`.

### Deliverables Checklist

#### A. Implementation

- [ ] `app/frontend/src/api/agent.ts` — `converse(touchpoint, opts)` POSTs to `/api/agent/converse` and returns typed response.
- [ ] `app/frontend/src/api/brandAssets.ts` — `uploadAsset(file, assetType)`, `triggerExtract(assetId)`, `getExtractStatus(assetId)`.
- [ ] `app/frontend/src/components/Chat.tsx` — reusable component. Props:
  - `touchpoint: 'onboarding' | 'post_session' | 'pre_session_prep' | 'refine'`
  - `sessionId?: string`
  - `initialMessage?: string`
  - `onCompleted?: (snapshot) => void` (called when assistant returns `finish_touchpoint`-like exit)
  - State: messages[], pending, input, droppedAssets[]
  - Renders: message list (user/assistant/tool), file-drop zone, input box, "Sending…" indicator.
- [ ] `app/frontend/src/views/Onboarding.tsx` — wraps `<Chat touchpoint="onboarding" />` with a 5-dot progress bar above (`Identify · Core · Extras · Assets · Ready`).
- [ ] `app/frontend/src/components/PhaseProgress.tsx` — 5-dot bar; current phase highlighted.
- [ ] `app/frontend/src/App.tsx` (modify) — top-level effect that:
  1. On mount, calls a new lightweight `/api/agent/profile-status` endpoint (or reuses `GET /api/me/brand-profile` if added in PJ-08) to fetch `onboarding_phase`.
  2. If `phase != 'complete'` and current route isn't `/onboarding`, redirect to `/onboarding`.
- [ ] On asset drop: upload via `uploadAsset`, kick off extract via `triggerExtract`, poll `getExtractStatus` every 1.5s until `status == 'ready'` or `'failed'`, then include the asset_id in the next `/converse` call.
- [ ] Optimistic UX: user's typed message renders immediately; "assistant typing…" indicator appears while `converse` is in flight.

#### B. Tests

- [ ] `app/frontend/tests-e2e/onboarding.spec.ts` (Playwright):
  - Sign in fresh test user → automatically routed to `/onboarding`.
  - Chat opening message appears.
  - Type "Acme Tutoring" → assistant responds → progress dot for Identify lit.
  - File-drop a small PNG → upload succeeds → "✓ Uploaded logo.png" inline card appears.
  - After full conversation flow → assistant calls `finish_touchpoint` → user redirected away from `/onboarding`.
- [ ] Component unit tests in `app/frontend/src/components/__tests__/Chat.test.tsx`:
  - User message renders optimistically before fetch resolves.
  - Loading indicator visible during fetch.
  - Tool result (palette swatches) renders as a confirmation card when present.

#### C. Integration Expectations

- [ ] `<Chat />` is touchpoint-agnostic — passing `touchpoint='refine'` works without any onboarding-specific logic firing.
- [ ] Server-side gate from PJ-09 (`POST /api/sessions` → 403 `brand_profile_not_ready`) is the source of truth; client-side redirect is a UX nicety.
- [ ] No design system changes — reuse existing `colors`, `font`, `styles` from `app/frontend/src/styles.ts` (or equivalent).

#### D. Documentation

- [ ] DEVLOG entry: `## 2026-XX-YY — PJ-07: Onboarding chat UI (✅)`.

---

## Branch & Merge Workflow

```bash
git switch final-submission && git pull
git switch -c feature/PJ-07-onboarding-ui
git add app/frontend/src/
git commit -m "feat(PJ-07): onboarding chat UI + <Chat /> reusable + phase progress"
git push -u origin feature/PJ-07-onboarding-ui
```

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `app/frontend/src/api/agent.ts` | `/api/agent/converse` client |
| `app/frontend/src/api/brandAssets.ts` | upload + extract + status clients |
| `app/frontend/src/components/Chat.tsx` | Reusable chat component |
| `app/frontend/src/components/PhaseProgress.tsx` | 5-dot progress bar |
| `app/frontend/src/views/Onboarding.tsx` | The `/onboarding` view |
| `app/frontend/tests-e2e/onboarding.spec.ts` | E2E smoke |

### Files to Modify

| File | Action |
|------|--------|
| `app/frontend/src/App.tsx` | Top-level redirect-to-onboarding effect + new route |
| `app/frontend/src/router.tsx` (or wherever routes live) | Add `/onboarding` route |

### Files to NOT Modify

- `app/frontend/src/views/Settings.tsx` — that's PJ-08.
- Existing routes — only adding `/onboarding`.

### Files to READ for Context

| File | Why |
|------|-----|
| `app/frontend/src/views/Settings.tsx` | View-component pattern with auth gate |
| `app/frontend/src/api/userKeys.ts` | Typed API client pattern |
| `docs/development/tickets/PJ-00-phase-plan.md` §10 | UI spec |
| `app/frontend/tests-e2e/*.spec.ts` | Playwright test pattern |

---

## Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Reusable `<Chat />` | PJ-00 §10.1 | One component, four consumers (onboarding/settings/post-session/pre-session) |
| File-drop in chat | PJ-00 §10.3 | Inline upload, status poll, extracted facts render as confirmation cards |
| Client-side redirect | PJ-00 §10.4 | Server enforces with 403 at `POST /api/sessions`; client redirect is UX polish |
| Synchronous converse | PJ-00 §3 decision 7 | No SSE; "typing…" indicator covers the 3–8s turn latency |

---

## Suggested Implementation Pattern

```typescript
// app/frontend/src/api/agent.ts
import { post } from './client'

export interface ConverseResponse {
  assistant_message: string
  phase: 'identify' | 'core' | 'extras' | 'assets' | 'good_enough' | 'complete'
  good_enough_now: boolean
  profile_snapshot: Record<string, unknown>
  asset_extractions?: Record<string, unknown>
  proposed_brief?: Record<string, string>
}

export const converse = (body: {
  touchpoint: 'onboarding' | 'post_session' | 'pre_session_prep' | 'refine'
  session_id?: string
  user_message?: string
  uploaded_asset_ids?: string[]
}) => post<ConverseResponse>('/api/agent/converse', body)
```

```typescript
// app/frontend/src/components/Chat.tsx (skeleton)
import { useState } from 'react'
import { converse, ConverseResponse } from '../api/agent'
import { uploadAsset, triggerExtract, getExtractStatus } from '../api/brandAssets'

interface Msg { role: 'user' | 'assistant' | 'tool'; content: string; meta?: any }

interface Props {
  touchpoint: ConverseRequest['touchpoint']
  sessionId?: string
  onCompleted?: (snap: ConverseResponse) => void
}

export function Chat({ touchpoint, sessionId, onCompleted }: Props) {
  const [msgs, setMsgs] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [pending, setPending] = useState(false)
  const [pendingAssetIds, setPendingAssetIds] = useState<string[]>([])

  async function send() {
    const userMsg = input.trim()
    if (!userMsg && pendingAssetIds.length === 0) return
    setMsgs(m => [...m, { role: 'user', content: userMsg }])
    setInput('')
    setPending(true)
    try {
      const res = await converse({
        touchpoint, session_id: sessionId,
        user_message: userMsg || undefined,
        uploaded_asset_ids: pendingAssetIds.length ? pendingAssetIds : undefined,
      })
      setMsgs(m => [...m, { role: 'assistant', content: res.assistant_message, meta: res }])
      setPendingAssetIds([])
      if (res.phase === 'complete' || res.good_enough_now) onCompleted?.(res)
    } finally { setPending(false) }
  }

  async function handleDrop(files: FileList) {
    for (const f of files) {
      const { asset_id } = await uploadAsset(f, inferAssetType(f))
      await triggerExtract(asset_id)
      await pollUntilReady(asset_id)
      setPendingAssetIds(ids => [...ids, asset_id])
      setMsgs(m => [...m, { role: 'tool', content: `✓ Uploaded ${f.name}` }])
    }
  }

  return (
    <div className="chat" onDrop={e => { e.preventDefault(); handleDrop(e.dataTransfer.files) }}>
      <MessageList msgs={msgs} pending={pending} />
      <InputBar value={input} onChange={setInput} onSend={send} disabled={pending} />
    </div>
  )
}

function inferAssetType(f: File): string {
  if (f.type === 'application/pdf') return 'style_guide'
  return 'logo'  // default for images; user can correct via the chat prompt
}
```

```typescript
// app/frontend/src/App.tsx — top-level redirect effect
useEffect(() => {
  if (!isSignedIn) return
  fetch('/api/agent/profile-status').then(r => r.json()).then(({ phase }) => {
    if (phase !== 'complete' && location.pathname !== '/onboarding') {
      navigate('/onboarding')
    }
  })
}, [isSignedIn])
```

(If `/api/agent/profile-status` doesn't exist yet, add a 10-line endpoint to `app/api/routes/agent.py` that returns `{phase, good_enough_at}` for the current user.)

---

## Edge Cases to Handle

1. Vision pass takes >30s — show a "still processing logo…" inline card; allow user to skip and continue without the asset_id.
2. Network failure on `/converse` — show "Retry" button on last message; preserve user input in the box.
3. User navigates away from `/onboarding` mid-flow — return on next mount; history reloads from `conversation_messages`.
4. Asset drop with unsupported MIME — show inline error; backend rejection from PJ-02 message surfaces.
5. `phase === 'complete'` mid-conversation (user finished) — call `onCompleted`, redirect to `/sessions`.
6. Race: two file drops in quick succession — both upload + poll independently; both `asset_id`s queue into next converse.
7. User refreshes during onboarding — `<Chat />` initial fetch loads `conversation_messages` history so context isn't lost.

---

## Definition of Done

- [ ] `npm run build` in `app/frontend` clean (no TS errors).
- [ ] `npx playwright test onboarding.spec.ts` passes.
- [ ] Component unit tests pass.
- [ ] Manual: fresh Clerk user gets redirected to `/onboarding` on first sign-in.
- [ ] Manual: drop a PNG, wait for extraction, see palette confirmation in chat.
- [ ] DEVLOG entry prepended.
- [ ] Feature branch pushed.

---

## Estimated Time

| Task | Estimate |
|------|----------|
| API clients (agent + brand-assets) | 60 min |
| `<Chat />` component | 240 min |
| `PhaseProgress` + `Onboarding` view | 60 min |
| `App.tsx` redirect + route wiring | 45 min |
| Playwright spec | 90 min |
| Unit tests | 60 min |
| Manual smoke + polish | 90 min |
| DEVLOG + commit | 15 min |
| **Total** | **~2 days** |

---

## After This Ticket: What Comes Next

- **PJ-08** — Settings reuses `<Chat />` for the refine modal
- **PJ-10** — SessionDetail reuses `<Chat />` for post-session reflection
- **PJ-11** — NewSessionForm reuses `<Chat />` for pre-session prep
