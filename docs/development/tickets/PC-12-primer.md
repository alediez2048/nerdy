# PC-12 Primer: Campaign Archiving + Management

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PC-04 through PC-11 (full campaign infrastructure). See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PC-12 is the capstone of the Campaign module — it adds polish and management features: campaign archiving UX, campaign duplication (clone with new name), bulk actions, and empty-state guidance. This ticket also adds the ability to move existing sessions into a campaign.

### Why It Matters

- Archiving needs a clear UX flow: confirmation, visual distinction, easy unarchive
- Users with many sessions created before campaigns need to organize them retroactively
- Campaign duplication lets users spin up new campaigns from proven templates
- Bulk session actions (archive all, move all) reduce manual work for large campaigns

---

## What Was Already Done

- PC-04: `PATCH /campaigns/{id}` supports `status: archived`
- PC-04: `DELETE /campaigns/{id}` sets status to archived (soft delete)
- PC-06: CampaignCard with status badge
- PC-08: CampaignDetail with archive toggle
- PC-10: Navigation with breadcrumbs
- PC-11: Campaign roll-up stats

---

## What This Ticket Must Accomplish

### Goal

Add campaign management features: archiving UX, campaign duplication, assign existing sessions to campaigns, and polish for production readiness.

### Deliverables Checklist

#### A. Campaign Duplication (`app/api/routes/campaigns.py` — extend)

- [ ] `POST /campaigns/{campaign_id}/duplicate` — create a new campaign with:
  - Same `audience`, `campaign_goal`, `default_config`
  - Name = "{original_name} (copy)"
  - New `campaign_id`
  - No sessions (empty clone)
- [ ] Returns the new `CampaignDetail`

#### B. Assign Session to Campaign (`app/api/routes/sessions.py` — extend)

- [ ] `PATCH /sessions/{session_id}` — extend to accept optional `campaign_id`
  - Validates campaign exists and belongs to user
  - Updates session's `campaign_id`
  - Set to `null` to remove from campaign
- [ ] Only allowed on completed or pending sessions (not running)

#### C. Frontend — Archive Flow (`app/frontend/src/views/CampaignDetail.tsx` — modify)

- [ ] Archive confirmation dialog (modal or inline):
  - "Archive [Campaign Name]? Sessions will not be deleted."
  - Confirm / Cancel buttons
- [ ] Archived campaigns:
  - Dimmed card styling in campaign list
  - "Archived" banner on detail page
  - "Unarchive" button replaces "Archive"
  - Sessions still visible and accessible

#### D. Frontend — Campaign Duplication

- [ ] "Duplicate" button on CampaignDetail action bar
- [ ] Calls `POST /campaigns/{id}/duplicate`
- [ ] Navigates to new campaign's detail page
- [ ] Success toast/notification

#### E. Frontend — Assign Session to Campaign

- [ ] On SessionDetail or SessionList: "Move to Campaign" dropdown/modal
  - Shows list of user's active campaigns
  - "Remove from Campaign" option
- [ ] Calls `PATCH /sessions/{id}` with new `campaign_id`
- [ ] Visual feedback on success

#### F. Frontend — Empty State Improvements

- [ ] CampaignList empty state: illustration + "Create your first campaign to organize your ad sessions"
- [ ] CampaignDetail with no sessions: "Add sessions to get started" + "New Session" CTA + "Move existing sessions here" hint

#### G. Tests (`tests/test_app/test_campaigns.py` + `tests/test_app/test_sessions.py` — extend)

- [ ] TDD first
- [ ] Test duplicate campaign creates new campaign with same config
- [ ] Test duplicate campaign has no sessions
- [ ] Test duplicate campaign name has "(copy)" suffix
- [ ] Test assign session to campaign updates FK
- [ ] Test assign session to invalid campaign returns 404
- [ ] Test remove session from campaign (set campaign_id=null)
- [ ] Test cannot reassign running session
- [ ] Minimum: 7+ new tests

#### H. Documentation

- [ ] Add ticket entry in `docs/DEVLOG.md`
- [ ] Update decision log: "Campaign management scope — what's in and what's out"

---

## Branch & Merge Workflow

Work on `develop` branch per project convention.

---

## Important Context

### Files to Create

None — extends existing files.

### Files to Modify

| File | Action |
|------|--------|
| `app/api/routes/campaigns.py` | Add duplicate endpoint |
| `app/api/routes/sessions.py` | Extend PATCH for campaign_id |
| `app/frontend/src/views/CampaignDetail.tsx` | Archive flow, duplicate button |
| `app/frontend/src/views/SessionDetail.tsx` | Move-to-campaign action |
| `app/frontend/src/views/CampaignList.tsx` | Archived styling |
| `app/frontend/src/components/CampaignCard.tsx` | Archived card styling |
| `tests/test_app/test_campaigns.py` | Duplication tests |
| `tests/test_app/test_sessions.py` | Session reassignment tests |
| `docs/DEVLOG.md` | Add ticket entry |

### Files You Should NOT Modify

- Any pipeline code
- `app/models/campaign.py` — no schema changes
- `app/models/session.py` — no schema changes (campaign_id already exists from PC-05)

### Files You Should READ for Context

| File | Why |
|------|-----|
| `app/api/routes/campaigns.py` | Current endpoints to extend |
| `app/api/routes/sessions.py` | Current PATCH endpoint |
| `app/frontend/src/views/CampaignDetail.tsx` | View to extend |

---

## Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| Duplicate = new campaign, no sessions | Sessions contain execution state — cloning them is complex and error-prone |
| No hard delete for campaigns | Data preservation. Archived is recoverable. |
| Session reassignment blocked during running | Prevents confusion in progress tracking and ledger paths |
| Move-to-campaign, not copy-to-campaign | Sessions have physical ledger files — moving the FK is clean, duplicating state is not |

---

## Edge Cases to Handle

1. Duplicate a campaign that was already a duplicate — name becomes "Campaign (copy) (copy)" — acceptable
2. Archive campaign with running sessions — allow it (sessions continue running)
3. Move session to archived campaign — allow it (archived ≠ locked)
4. User with no campaigns tries to "Move to Campaign" — show "No campaigns available, create one first"
5. Concurrent archive + session creation — eventual consistency, both succeed

---

## Definition of Done

- [ ] Campaign duplication works end-to-end
- [ ] Session reassignment to campaign works with validation
- [ ] Archive flow has confirmation dialog
- [ ] Archived campaigns visually distinct in list
- [ ] Unarchive works from detail page
- [ ] Empty states guide users toward next action
- [ ] 7+ new tests pass
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Tests (TDD) | 15 min |
| API: duplicate + reassign | 20 min |
| Frontend: archive flow | 15 min |
| Frontend: duplicate + move | 20 min |
| Frontend: empty states | 10 min |
| DEVLOG + decision log | 10 min |

---

## After This Ticket: Campaign Module Complete

The full Campaign → Sessions hierarchy is in place:
- **Create** campaigns with default config
- **Create sessions** within campaigns (pre-filled from defaults)
- **View** campaign list with roll-up stats
- **Manage** campaigns: rename, archive/unarchive, duplicate
- **Organize** existing sessions by moving them into campaigns
- **Navigate** via breadcrumbs: Campaigns → Campaign → Session → Tabs

Next priorities:
- Dashboard integration: campaign-level views in the global dashboard
- Campaign comparison: side-by-side stats across campaigns
