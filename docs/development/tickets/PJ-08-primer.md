# PJ-08 Primer

**Source plan:** [`PJ-00-phase-plan.md`](PJ-00-phase-plan.md) — §10.2 (Settings) and §8.4 (refine touchpoint).
**For:** New Cursor Agent session
**Date:** 2026-06-08
**Previous work:** PJ-07 (Chat UI + reusable component) merged. See `docs/development/DEVLOG.md`.
**Status:** ⏳ Not started

---

# Ticket PJ-08: Settings page brand profile section

## What Is This Ticket?

A user has finished onboarding; now they want to *see* their brand profile and refine it. This ticket adds a "Brand Profile" card to the existing `/settings` page that shows:

1. Phase progress (the same 5-dot bar from PJ-07).
2. A summary of typed-core fields (`business_name`, `industry`, `audience`, `mission`, `value_props`, `tone_descriptors`, palette swatches, logo thumbnail).
3. A collapsible "Extras" viewer showing all keys/values in `brand_profile.extras`.
4. A "Refine your brand" button that opens a modal with `<Chat touchpoint="refine" />`.

Clicking any of the 5 phase dots opens the same refine modal — that's the §7.6 UX: post-onboarding, dots are clickable shortcuts into a phase-scoped refine.

### Why It Matters

- The Settings card is the "memory of what we know about you" surface — proof that the system grew with the user.
- Refine modal is the always-available door back into the agent.
- Reuses `<Chat />` from PJ-07 — first proof the component generalizes.

---

## What Was Already Done

- **PJ-07** — `<Chat />` component, `phase` state in API responses.
- `app/frontend/src/views/Settings.tsx` — existing Settings page (BYO API keys card lives here).
- `app/api/routes/user_keys.py` — pattern for a per-user GET endpoint backing a settings card.

---

## What This Ticket Must Accomplish

### Goal

Add a "Brand Profile" card to `/settings` showing phase, typed-field summary, extras viewer, and a "Refine your brand" button that opens a chat modal.

### Deliverables Checklist

#### A. Implementation

- [ ] `GET /api/me/brand-profile` (new endpoint in `app/api/routes/agent.py` or a new `me.py`) — returns the full `BrandProfile` row for the current user, JSON-serialized. Includes `logo_asset_url` if `logo_asset_id` is set.
- [ ] `app/frontend/src/api/brandProfile.ts` — `getBrandProfile()` client.
- [ ] `app/frontend/src/components/BrandProfileCard.tsx` — the card. Sections:
  - Header with business name + industry badge.
  - 5-dot `PhaseProgress` (each dot clickable, opens refine modal scoped to that phase).
  - "Refine your brand" CTA button (top-right).
  - Typed-field summary grid (audience, mission, value_props as chips, tone_descriptors as chips, do_dont_rules as two columns, palette swatches, logo thumb).
  - Collapsible "Extras (N)" section showing key/value pairs.
- [ ] `app/frontend/src/components/RefineModal.tsx` — modal wrapping `<Chat touchpoint="refine" />`. Closes on `onCompleted` or X click. After close, parent re-fetches `getBrandProfile()` to refresh the card.
- [ ] Modify `app/frontend/src/views/Settings.tsx` to mount `BrandProfileCard` above the existing BYO Keys card.

#### B. Tests

- [ ] `app/frontend/tests-e2e/settings_brand_profile.spec.ts`:
  - Sign in as user with completed brand profile.
  - Navigate to `/settings` → Brand Profile card visible with business name.
  - Click "Refine your brand" → modal opens with chat interface.
  - Send a message in the modal → assistant responds → close modal → card re-renders with updated field if applicable.
  - Click "Extras (N)" header → list expands.
- [ ] Component unit test `app/frontend/src/components/__tests__/BrandProfileCard.test.tsx`:
  - Renders all typed fields when provided.
  - Hides palette swatches when no hex codes present.
  - Logo thumbnail uses `logo_asset_url`.
- [ ] Backend test `tests/test_api/test_me_brand_profile.py`:
  - `test_returns_profile_for_current_user` — fixture user → JSON of their row.
  - `test_returns_404_when_no_profile` — fresh user → 404.
  - `test_does_not_return_other_users_profile` — auth as A, no way to reach B's row (the endpoint takes no path param).

#### C. Integration Expectations

- [ ] No agent prompt or tool changes.
- [ ] Refine modal `onCompleted` triggers parent refresh — uses the same response shape from PJ-07.
- [ ] `BrandProfileCard` is purely presentational + a fetch — no side-effects on the profile.

#### D. Documentation

- [ ] DEVLOG entry: `## 2026-XX-YY — PJ-08: Settings brand profile section (✅)`.

---

## Branch & Merge Workflow

```bash
git switch final-submission && git pull
git switch -c feature/PJ-08-settings-brand-profile
git add app/api/routes/ app/frontend/src/ tests/
git commit -m "feat(PJ-08): Settings brand profile card + refine modal"
git push -u origin feature/PJ-08-settings-brand-profile
```

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `app/api/routes/me.py` (or extend `agent.py`) | `GET /api/me/brand-profile` |
| `app/frontend/src/api/brandProfile.ts` | Client |
| `app/frontend/src/components/BrandProfileCard.tsx` | The card |
| `app/frontend/src/components/RefineModal.tsx` | Modal wrapping `<Chat />` |
| `app/frontend/tests-e2e/settings_brand_profile.spec.ts` | E2E |
| `tests/test_api/test_me_brand_profile.py` | Backend test |

### Files to Modify

| File | Action |
|------|--------|
| `app/frontend/src/views/Settings.tsx` | Mount `BrandProfileCard` above BYO Keys card |
| `app/main.py` | Register new router if creating `me.py` |

### Files to NOT Modify

- `<Chat />`, `<PhaseProgress />` from PJ-07.
- `app/api/agent/*` modules.

### Files to READ for Context

| File | Why |
|------|-----|
| `app/frontend/src/views/Settings.tsx` | Card composition pattern |
| `app/frontend/src/api/userKeys.ts` | Client pattern |
| `app/api/routes/user_keys.py` | Per-user GET endpoint pattern |
| `docs/development/tickets/PJ-00-phase-plan.md` §10.2, §7.6 | UX spec |

---

## Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Reuse `<Chat />` | PJ-00 §10.1 | First reuse outside `/onboarding`; validates the component contract |
| Phase dots clickable post-onboarding | PJ-00 §7.6 | Click → refine modal scoped to that phase's fields |
| GET endpoint, no path param | PJ-00 §6.4 | Auth dep supplies `user_id`; impossible to read another user's profile via this endpoint |
| Refine touchpoint has full tool set | PJ-00 §6.2 + PJ-05 whitelist | `save_field`, `update_extra`, `ingest_asset`, terminals |

---

## Suggested Implementation Pattern

```python
# app/api/routes/me.py
from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user_id
from app.db import get_session
from app.models.brand_profile import BrandProfile

router = APIRouter(prefix="/api/me", tags=["me"])

@router.get("/brand-profile")
def get_my_brand_profile(user_id: str = Depends(get_current_user_id), db = Depends(get_session)):
    row = db.query(BrandProfile).get(user_id)
    if not row:
        raise HTTPException(404, "no_brand_profile")
    return {
        "user_id": row.user_id,
        "business_name": row.business_name,
        "industry": row.industry,
        "audience": row.audience,
        "mission": row.mission,
        "value_props": row.value_props or [],
        "tone_descriptors": row.tone_descriptors or [],
        "avoid_phrases": row.avoid_phrases or [],
        "do_dont_rules": row.do_dont_rules or {"do": [], "dont": []},
        "palette_primary_hex": row.palette_primary_hex,
        "palette_secondary_hex": row.palette_secondary_hex,
        "palette_accent_hex": row.palette_accent_hex,
        "logo_asset_url": f"/api/brand-assets/{row.logo_asset_id}" if row.logo_asset_id else None,
        "extras": row.extras or {},
        "onboarding_phase": row.onboarding_phase,
        "good_enough_at": row.good_enough_at.isoformat() if row.good_enough_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
```

```tsx
// app/frontend/src/components/BrandProfileCard.tsx (skeleton)
import { useEffect, useState } from 'react'
import { getBrandProfile, BrandProfile } from '../api/brandProfile'
import { PhaseProgress } from './PhaseProgress'
import { RefineModal } from './RefineModal'

export function BrandProfileCard() {
  const [profile, setProfile] = useState<BrandProfile | null>(null)
  const [refineOpen, setRefineOpen] = useState(false)
  const [extrasOpen, setExtrasOpen] = useState(false)

  async function refresh() {
    setProfile(await getBrandProfile())
  }
  useEffect(() => { refresh() }, [])

  if (!profile) return <Card><em>Loading brand profile…</em></Card>

  return (
    <Card>
      <Header>
        <h2>{profile.business_name}</h2>
        <IndustryBadge>{profile.industry}</IndustryBadge>
        <button onClick={() => setRefineOpen(true)}>Refine your brand</button>
      </Header>

      <PhaseProgress current={profile.onboarding_phase} onDotClick={() => setRefineOpen(true)} />

      <Grid>
        <Field label="Audience">{profile.audience}</Field>
        <Field label="Mission">{profile.mission}</Field>
        <ChipsField label="Value props" items={profile.value_props} />
        <ChipsField label="Tone" items={profile.tone_descriptors} />
        <DoDont rules={profile.do_dont_rules} />
        <PaletteSwatches
          primary={profile.palette_primary_hex}
          secondary={profile.palette_secondary_hex}
          accent={profile.palette_accent_hex}
        />
        {profile.logo_asset_url && <LogoThumb src={profile.logo_asset_url} />}
      </Grid>

      <ExtrasViewer
        extras={profile.extras}
        open={extrasOpen}
        onToggle={() => setExtrasOpen(!extrasOpen)}
      />

      {refineOpen && (
        <RefineModal
          onClose={() => { setRefineOpen(false); refresh() }}
        />
      )}
    </Card>
  )
}
```

---

## Edge Cases to Handle

1. `value_props` is null vs empty array — handle both as empty.
2. `extras` with deeply-nested values — render as `<pre>` for objects, plain text for scalars.
3. Logo asset deleted (404 on `GET /api/brand-assets/{id}`) — broken image; show fallback icon.
4. Profile with `onboarding_phase='good_enough'` but not yet `'complete'` — show all 5 dots, last one half-lit.
5. Refine modal closes without sending any message — no refetch needed but doing one is cheap.
6. User on `/settings` with no `brand_profile` row (shouldn't happen post-PJ-09 backfill, but defensive) — show "Complete onboarding to set up your brand" CTA.

---

## Definition of Done

- [ ] `npm run build` clean.
- [ ] E2E spec passes.
- [ ] Backend tests pass.
- [ ] Manual: refine modal updates a field, card reflects it on close.
- [ ] DEVLOG entry prepended.
- [ ] Feature branch pushed.

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Backend endpoint + tests | 60 min |
| API client | 15 min |
| `BrandProfileCard` (sections + presentational subcomponents) | 180 min |
| `RefineModal` | 45 min |
| `Settings.tsx` integration | 30 min |
| E2E spec | 90 min |
| Manual polish | 60 min |
| DEVLOG + commit | 15 min |
| **Total** | **~1 day** |

---

## After This Ticket: What Comes Next

- **PJ-09** — Pipeline rewire (no UI dep; can land in parallel)
- **PJ-12** — Doc refresh references the new Settings card
