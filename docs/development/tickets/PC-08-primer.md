# PC-08 Primer: CampaignDetail View + Session List

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PC-04 (Campaign CRUD API), PC-05 (Session campaign_id FK + campaign sessions endpoint), PC-06 (CampaignList), PC-07 (NewCampaignForm). See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PC-08 builds the campaign detail page — the view a user sees when they click into a campaign. It shows the campaign header (editable name, description, status), a "New Session" button scoped to this campaign, and a list of all sessions belonging to the campaign using the existing `SessionCard` component.

### Why It Matters

- This is where users manage a campaign's sessions — the central hub for a marketing initiative
- Reuses `SessionCard` so users get the same rich preview (ad images, scores, progress) within the campaign context
- The "New Session" button navigates to the session form pre-scoped to this campaign (PC-09)
- Editable campaign name follows the same inline-edit pattern as `SessionDetail.tsx`

---

## What Was Already Done

- PC-04: `GET /campaigns/{id}` — campaign detail API
- PC-05: `GET /campaigns/{id}/sessions` — sessions filtered by campaign
- PC-06: `CampaignList.tsx` — navigates to `/campaigns/{campaign_id}`
- PA-09: `SessionDetail.tsx` — inline name editing pattern (reference)
- PA-06: `SessionCard.tsx` — session card component (reuse directly)

---

## What This Ticket Must Accomplish

### Goal

Create the campaign detail page at `/campaigns/:campaignId` showing campaign info, session list, and campaign management actions.

### Deliverables Checklist

#### A. CampaignDetail View (`app/frontend/src/views/CampaignDetail.tsx` — create)

- [ ] Fetch campaign detail via `GET /api/campaigns/{campaignId}`
- [ ] Fetch campaign sessions via `GET /api/campaigns/{campaignId}/sessions`
- [ ] Header section:
  - Campaign name (inline editable — click to edit, save on blur/Enter)
  - Description (displayed below name, editable)
  - Status badge (Active/Archived)
  - Audience + Goal badges
- [ ] Action bar:
  - "New Session" button → navigates to `/campaigns/{campaignId}/sessions/new`
  - Archive/Unarchive toggle button
- [ ] Session list:
  - Reuse `SessionCard` component
  - Responsive grid layout (same as SessionList)
  - Empty state: "No sessions in this campaign yet — create your first one"
- [ ] Breadcrumbs: Campaigns / [Campaign Name]
- [ ] Polling for session updates (30s, for running sessions)
- [ ] Loading and error states

#### B. Route Registration (`app/frontend/src/App.tsx` — modify)

- [ ] Add route: `/campaigns/:campaignId` → `CampaignDetail`
- [ ] Add route: `/campaigns/:campaignId/sessions/new` → `NewSessionForm` (PC-09 wires the pre-fill)

#### C. Documentation

- [ ] Add ticket entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

Work on `develop` branch per project convention.

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `app/frontend/src/views/CampaignDetail.tsx` | Campaign detail page |

### Files to Modify

| File | Action |
|------|--------|
| `app/frontend/src/App.tsx` | Add campaign detail + campaign session routes |
| `docs/DEVLOG.md` | Add ticket entry |

### Files You Should NOT Modify

- `app/frontend/src/components/SessionCard.tsx` — reuse as-is
- `app/frontend/src/views/SessionList.tsx` — unchanged
- Any backend code

### Files You Should READ for Context

| File | Why |
|------|-----|
| `app/frontend/src/views/SessionDetail.tsx` | Inline name editing pattern |
| `app/frontend/src/views/SessionList.tsx` | Session list rendering pattern |
| `app/frontend/src/components/SessionCard.tsx` | Card component to reuse |
| `app/frontend/src/api/campaigns.ts` | Campaign API client |
| `app/frontend/src/api/sessions.ts` | Session API client (for listSessions with campaign filter) |

---

## Suggested Implementation Pattern

```typescript
export default function CampaignDetail() {
  const { campaignId } = useParams<{ campaignId: string }>()
  const navigate = useNavigate()
  const [campaign, setCampaign] = useState<CampaignDetailType | null>(null)
  const [sessions, setSessions] = useState<SessionSummary[]>([])

  useEffect(() => {
    if (!campaignId) return
    getCampaign(campaignId).then(setCampaign)
    listCampaignSessions(campaignId).then(setSessions)
  }, [campaignId])

  return (
    <div>
      {/* Breadcrumbs */}
      <span onClick={() => navigate('/campaigns')}>Campaigns</span> / {campaign?.name}

      {/* Header with editable name */}
      {/* Action bar: New Session + Archive */}
      <button onClick={() => navigate(`/campaigns/${campaignId}/sessions/new`)}>
        New Session
      </button>

      {/* Session grid — reuses SessionCard */}
      <div style={s.grid}>
        {sessions.map(session => (
          <SessionCard key={session.session_id} session={session} />
        ))}
      </div>
    </div>
  )
}
```

---

## Edge Cases to Handle

1. Campaign not found (404 from API) — show error with back link
2. Campaign with no sessions — empty state with CTA
3. Campaign is archived — show "Archived" badge, still allow viewing sessions
4. Many sessions (20+) — pagination via Load More
5. Running sessions in campaign — poll for progress updates
6. Campaign name edit — same inline pattern as session name (blur/Enter to save, Escape to cancel)

---

## Definition of Done

- [ ] Campaign detail page renders at `/campaigns/:campaignId`
- [ ] Campaign header shows name (editable), description, badges
- [ ] Session list uses existing SessionCard components
- [ ] "New Session" button navigates to scoped session creation
- [ ] Archive/unarchive toggle works
- [ ] Breadcrumbs navigate back to campaign list
- [ ] Empty state for campaigns with no sessions
- [ ] Polling for running session updates
- [ ] Design consistent with SessionDetail
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time

| Task | Estimate |
|------|----------|
| CampaignDetail component | 30 min |
| Inline name editing | 10 min |
| Session grid integration | 10 min |
| Route wiring | 5 min |
| DEVLOG | 5 min |

---

## After This Ticket: What Comes Next

- **PC-09:** Pre-fill session form from campaign defaults
- **PC-11:** Campaign roll-up stats (aggregate across sessions)
