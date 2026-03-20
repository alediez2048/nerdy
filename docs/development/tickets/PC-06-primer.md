# PC-06 Primer: CampaignList + CampaignCard Frontend Views

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PC-04 (Campaign CRUD API), PC-05 (Session campaign_id FK). See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PC-06 builds the frontend campaign list page — a grid of campaign cards that shows all of a user's campaigns with summary info. This is the equivalent of `SessionList.tsx` but for campaigns. It consumes the `GET /campaigns` API from PC-04.

### Why It Matters

- Users need to see and navigate their campaigns before drilling into sessions
- Campaign cards provide at-a-glance info: name, audience, goal, session count, status
- This view becomes the primary entry point once PC-10 updates navigation
- Reuses the design system (tokens, badges, card patterns) from the session list

---

## What Was Already Done

- PC-04: `GET /campaigns` API with pagination and status filter
- PA-06: `SessionList.tsx` — list view pattern with filters, pagination, polling
- PA-06: `SessionCard.tsx` — card component pattern
- Design tokens: `app/frontend/src/design/tokens.ts` — colors, radii, font

---

## What This Ticket Must Accomplish

### Goal

Create `CampaignList` page view and `CampaignCard` component that display the user's campaigns in a responsive grid.

### Deliverables Checklist

#### A. API Client (`app/frontend/src/api/campaigns.ts` — create)

- [ ] `listCampaigns(params)` — `GET /api/campaigns` with pagination + status filter
- [ ] `getCampaign(campaignId)` — `GET /api/campaigns/{campaignId}`
- [ ] `createCampaign(body)` — `POST /api/campaigns`
- [ ] `updateCampaign(campaignId, body)` — `PATCH /api/campaigns/{campaignId}`
- [ ] `deleteCampaign(campaignId)` — `DELETE /api/campaigns/{campaignId}`
- [ ] Types: `CampaignSummary`, `CampaignDetail`, `CampaignListResponse`

#### B. Types (`app/frontend/src/types/campaign.ts` — create)

- [ ] `CampaignSummary` interface matching API schema
- [ ] `CampaignDetail` interface
- [ ] `CampaignListResponse` interface
- [ ] `CampaignCreate` interface for form submission

#### C. CampaignCard (`app/frontend/src/components/CampaignCard.tsx` — create)

- [ ] Displays: name, description (truncated), audience badge, goal badge, status badge
- [ ] Session count indicator (e.g. "5 sessions")
- [ ] Created date (relative time)
- [ ] Click navigates to `/campaigns/{campaign_id}`
- [ ] Hover effect (border highlight, same as SessionCard)
- [ ] Archive action (icon button, calls PATCH to set status=archived)
- [ ] Style: consistent with `SessionCard` design patterns

#### D. CampaignList (`app/frontend/src/views/CampaignList.tsx` — create)

- [ ] Page header: "Campaigns" + "New Campaign" button (links to `/campaigns/new`)
- [ ] Status filter: All / Active / Archived
- [ ] Responsive grid of CampaignCard components
- [ ] Pagination (Load More button, same as SessionList)
- [ ] Polling for updates (30s interval, same as SessionList)
- [ ] Loading and error states
- [ ] Empty state: "No campaigns yet — create your first one"

#### E. Route Registration (`app/frontend/src/App.tsx` — modify)

- [ ] Add route: `/campaigns` → `CampaignList`
- [ ] Keep existing `/sessions` route (flat view still accessible)

#### F. Documentation

- [ ] Add ticket entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

Work on `develop` branch per project convention.

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `app/frontend/src/api/campaigns.ts` | Campaign API client |
| `app/frontend/src/types/campaign.ts` | Campaign TypeScript types |
| `app/frontend/src/components/CampaignCard.tsx` | Campaign card component |
| `app/frontend/src/views/CampaignList.tsx` | Campaign list page |

### Files to Modify

| File | Action |
|------|--------|
| `app/frontend/src/App.tsx` | Add `/campaigns` route |
| `docs/DEVLOG.md` | Add ticket entry |

### Files You Should NOT Modify

- `app/frontend/src/views/SessionList.tsx` — stays as-is (flat session view)
- `app/frontend/src/components/SessionCard.tsx` — unchanged
- Any backend code

### Files You Should READ for Context

| File | Why |
|------|-----|
| `app/frontend/src/views/SessionList.tsx` | List view pattern to follow |
| `app/frontend/src/components/SessionCard.tsx` | Card component pattern |
| `app/frontend/src/api/sessions.ts` | API client pattern |
| `app/frontend/src/types/session.ts` | Type definition pattern |
| `app/frontend/src/design/tokens.ts` | Design tokens |

---

## Suggested Implementation Pattern

```typescript
// CampaignCard — minimal structure
export default function CampaignCard({ campaign }: { campaign: CampaignSummary }) {
  const navigate = useNavigate()
  return (
    <div onClick={() => navigate(`/campaigns/${campaign.campaign_id}`)} style={s.card}>
      <span style={s.name}>{campaign.name}</span>
      <div style={s.badges}>
        <Badge label={campaign.audience} />
        <Badge label={campaign.campaign_goal} />
        <Badge label={`${campaign.session_count} sessions`} />
      </div>
      {campaign.description && <p style={s.desc}>{campaign.description}</p>}
    </div>
  )
}
```

---

## Edge Cases to Handle

1. No campaigns — show empty state with CTA to create
2. All campaigns archived — empty state when "Active" filter is on
3. Very long campaign name — truncate with ellipsis (same as session cards)
4. Campaign with 0 sessions — show "0 sessions" badge, not empty
5. Polling while user is scrolling — don't reset scroll position

---

## Definition of Done

- [ ] Campaign list page renders at `/campaigns`
- [ ] Campaign cards show name, badges, session count
- [ ] Status filter works (all/active/archived)
- [ ] Pagination works
- [ ] Click navigates to campaign detail
- [ ] New Campaign button links to `/campaigns/new`
- [ ] Empty state shown when no campaigns
- [ ] Design consistent with session list
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time

| Task | Estimate |
|------|----------|
| API client + types | 10 min |
| CampaignCard component | 15 min |
| CampaignList view | 20 min |
| Route wiring | 5 min |
| DEVLOG | 5 min |

---

## After This Ticket: What Comes Next

- **PC-07:** NewCampaignForm — create campaigns from the UI
- **PC-08:** CampaignDetail — drill into a campaign's sessions
