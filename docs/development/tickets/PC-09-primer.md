# PC-09 Primer: Pre-fill Session Form from Campaign Defaults

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PC-04 (Campaign CRUD API with default_config), PC-05 (Session campaign_id FK), PC-07 (NewCampaignForm), PC-08 (CampaignDetail with "New Session" button). See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PC-09 wires the session creation form to pre-fill from a campaign's defaults when creating a session within a campaign. When a user clicks "New Session" from a campaign detail page, the form loads with the campaign's audience, goal, persona, and other defaults already set — and the `campaign_id` is automatically attached.

### Why It Matters

- This is the key UX payoff of campaigns — configure once, create sessions quickly
- Without pre-fill, campaigns are just folders; with pre-fill, they're workflow accelerators
- The user can always override any default — campaigns are templates, not constraints
- The `campaign_id` must be passed to `POST /sessions` so the session is linked

---

## What Was Already Done

- PC-04: Campaign `default_config` JSON field stores template settings
- PC-05: `POST /sessions` accepts `campaign_id`, links session to campaign
- PC-07: `NewCampaignForm` lets users set default audience, goal, persona, etc.
- PC-08: "New Session" button navigates to `/campaigns/{campaignId}/sessions/new`
- PA-05: `NewSessionForm.tsx` — existing session form with local state

---

## What This Ticket Must Accomplish

### Goal

When creating a session from a campaign context, pre-fill the session form from the campaign's `default_config` and automatically set `campaign_id` on submission.

### Deliverables Checklist

#### A. Route Parameter (`app/frontend/src/App.tsx` — verify)

- [ ] Route `/campaigns/:campaignId/sessions/new` renders `NewSessionForm`
- [ ] `campaignId` available via `useParams`

#### B. Campaign Default Loading (`app/frontend/src/views/NewSessionForm.tsx` — modify)

- [ ] On mount, check for `campaignId` route param
- [ ] If `campaignId` present:
  - Fetch campaign detail via `GET /api/campaigns/{campaignId}`
  - Merge campaign's `default_config` into form initial state
  - Override individual fields: `audience`, `campaign_goal`, `persona` from campaign top-level fields
  - Show campaign context banner: "Creating session for [Campaign Name]"
  - Store `campaignId` in local state
- [ ] If no `campaignId` (standalone session creation at `/sessions/new`):
  - Use existing defaults (unchanged behavior)
- [ ] All pre-filled fields are editable — user can override anything
- [ ] On submit:
  - Include `campaign_id: campaignId` in the POST body
  - On success: navigate to `/campaigns/{campaignId}` (back to campaign detail, not session list)

#### C. Campaign Context Banner

- [ ] Shown at top of form when creating within a campaign
- [ ] Shows campaign name and link back to campaign
- [ ] Subtle styling (info bar, not intrusive)

#### D. API Client Update (`app/frontend/src/api/sessions.ts` — modify)

- [ ] `createSession()` must accept optional `campaign_id` parameter
- [ ] Pass through to `POST /api/sessions` body

#### E. Tests (`tests/test_app/test_sessions.py` — extend)

- [ ] Test that session created with `campaign_id` via API has correct FK value
- [ ] (Frontend tests are manual/visual — no Jest tests required for form pre-fill)

#### F. Documentation

- [ ] Add ticket entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

Work on `develop` branch per project convention.

---

## Important Context

### Files to Create

None — this ticket modifies existing files.

### Files to Modify

| File | Action |
|------|--------|
| `app/frontend/src/views/NewSessionForm.tsx` | Add campaign pre-fill logic |
| `app/frontend/src/api/sessions.ts` | Add `campaign_id` to create function |
| `docs/DEVLOG.md` | Add ticket entry |

### Files You Should NOT Modify

- `app/api/routes/sessions.py` — already accepts `campaign_id` from PC-05
- `app/api/schemas/session.py` — already has `campaign_id` from PC-05
- `app/frontend/src/views/NewCampaignForm.tsx` — campaign form stays as-is

### Files You Should READ for Context

| File | Why |
|------|-----|
| `app/frontend/src/views/NewSessionForm.tsx` | Form to modify |
| `app/frontend/src/api/campaigns.ts` | `getCampaign()` to fetch defaults |
| `app/frontend/src/api/sessions.ts` | `createSession()` to extend |
| `app/api/schemas/campaign.py` | `default_config` structure |

---

## Suggested Implementation Pattern

```typescript
// In NewSessionForm:
const { campaignId } = useParams<{ campaignId?: string }>()
const [campaignName, setCampaignName] = useState<string | null>(null)

useEffect(() => {
  if (!campaignId) return
  getCampaign(campaignId).then((c) => {
    setCampaignName(c.name)
    // Merge defaults into form state
    const defaults = c.default_config || {}
    setConfig(prev => ({
      ...prev,
      audience: c.audience || prev.audience,
      campaign_goal: c.campaign_goal || prev.campaign_goal,
      ...defaults,
    }))
  })
}, [campaignId])

// On submit:
const body = { name, config, campaign_id: campaignId || undefined }
const result = await createSession(body)
if (campaignId) {
  navigate(`/campaigns/${campaignId}`)
} else {
  navigate(`/sessions/${result.session_id}`)
}
```

---

## Edge Cases to Handle

1. Campaign fetch fails — show error, let user still create standalone session
2. Campaign has no `default_config` — use form defaults (no merge needed)
3. Campaign defaults conflict with form constraints (e.g. ad_count > 200) — form validation catches it
4. User navigates directly to `/campaigns/{id}/sessions/new` with invalid campaignId — show error
5. Back navigation from campaign session form — should go to campaign detail, not session list

---

## Definition of Done

- [ ] Session form pre-fills from campaign defaults when accessed via `/campaigns/{id}/sessions/new`
- [ ] Campaign context banner shown with campaign name
- [ ] All defaults are overridable
- [ ] `campaign_id` included in POST body
- [ ] Post-creation redirects to campaign detail (not session list)
- [ ] Standalone session creation (`/sessions/new`) unchanged
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Campaign fetch + merge logic | 15 min |
| Context banner | 10 min |
| API client update | 5 min |
| Navigation flow | 5 min |
| DEVLOG | 5 min |

---

## After This Ticket: What Comes Next

- **PC-10:** Navigation update — home page becomes campaigns
- **PC-11:** Campaign roll-up stats
