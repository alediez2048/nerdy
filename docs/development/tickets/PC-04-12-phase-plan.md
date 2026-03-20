# Phase PC (Part 2): Campaign Module — Organizing Sessions at Scale

## Context

PC-00 through PC-03 added the video pipeline track (session types, video generation, evaluation, app integration). PC-04 through PC-12 introduce the **Campaign** entity — a named container that groups related sessions, provides default configuration, and surfaces aggregate statistics.

Today every session is a standalone item in a flat list. With campaigns, users can organize sessions by marketing initiative (e.g. "Spring SAT Push", "Back-to-School Awareness"), spin up sessions pre-filled from campaign defaults, and evaluate performance at the campaign level.

## Tickets (9)

### PC-04: Campaign Model + Migration + CRUD API
- `app/models/campaign.py` — Campaign SQLAlchemy model (campaign_id, name, user_id, description, audience, campaign_goal, default_config, status)
- `app/api/routes/campaigns.py` — POST/GET/PATCH/DELETE with per-user isolation
- `app/api/schemas/campaign.py` — CampaignCreate, CampaignSummary, CampaignDetail, CampaignListResponse
- **AC:** 12+ tests, CRUD functional, pagination, soft delete

### PC-05: Session campaign_id FK + API Filter
- `app/models/session.py` — add nullable `campaign_id` FK to campaigns
- `app/api/routes/sessions.py` — filter sessions by campaign_id, validate on create
- `GET /campaigns/{id}/sessions` endpoint
- **AC:** 8+ new tests, backward compatible (existing sessions unaffected)

### PC-06: CampaignList + CampaignCard Frontend
- `app/frontend/src/views/CampaignList.tsx` — paginated campaign grid with status filter
- `app/frontend/src/components/CampaignCard.tsx` — name, badges, session count, click-to-detail
- `app/frontend/src/api/campaigns.ts` — API client
- `app/frontend/src/types/campaign.ts` — TypeScript types
- **AC:** Campaign list renders, cards show metadata, pagination works

### PC-07: NewCampaignForm Frontend
- `app/frontend/src/views/NewCampaignForm.tsx` — name (required), description, audience/goal/persona defaults
- Progressive disclosure for advanced defaults (session type, ad count, quality threshold)
- **AC:** Form creates campaign via API, navigates to detail on success

### PC-08: CampaignDetail View + Session List
- `app/frontend/src/views/CampaignDetail.tsx` — campaign header (editable name), session grid using SessionCard
- "New Session" button scoped to campaign
- Breadcrumbs: Campaigns / [Campaign Name]
- **AC:** Detail page shows campaign info + sessions, archive toggle works

### PC-09: Pre-fill Session Form from Campaign Defaults
- Modify `NewSessionForm.tsx` to detect campaign context via route params
- Merge campaign `default_config` into form initial state
- Campaign context banner, `campaign_id` attached on submit
- **AC:** Session form pre-fills from campaign, defaults overridable, session linked to campaign

### PC-10: Navigation Update — Home → Campaigns + Breadcrumbs
- `/` → `/campaigns` (campaigns become the home page)
- Persistent `NavBar` component replaces floating logo + theme toggle
- Reusable `Breadcrumbs` component across all views
- Campaign-aware breadcrumbs in SessionDetail
- **AC:** All navigation flows work, breadcrumbs show hierarchy

### PC-11: Campaign Roll-up Stats
- `_compute_campaign_stats()` — aggregate metrics from session results_summary
- Stats: total sessions, ads generated/published, avg quality score, total cost, type breakdown
- CampaignCard shows summary stats, CampaignDetail shows full stats panel
- **AC:** 6+ new tests, stats correct, zero-session campaigns handled

### PC-12: Campaign Archiving + Management (Capstone)
- Campaign duplication (`POST /campaigns/{id}/duplicate`)
- Session reassignment to campaigns (`PATCH /sessions/{id}` with campaign_id)
- Archive confirmation UX, archived campaign styling
- Empty state improvements
- **AC:** 7+ new tests, duplicate/archive/reassign all functional

## Dependency Graph

```
PC-04 (Model + CRUD API)
  │
  v
PC-05 (Session FK)
  │
  ├──────────────────────┐
  v                      v
PC-06 (List + Card)    PC-09 (Pre-fill) ← needs PC-07
  │                      │
  v                      │
PC-07 (New Form)         │
  │                      │
  v                      v
PC-08 (Detail) ─────────┘
  │
  v
PC-10 (Navigation)
  │
  v
PC-11 (Roll-up Stats)
  │
  v
PC-12 (Archiving + Management — Capstone)
```

## Key Decisions

1. **Campaigns are organizational containers, not pipeline executors** — a campaign never "runs"; sessions within it do
2. **Nullable FK for backward compatibility** — existing sessions have no campaign and continue to work
3. **`default_config` is a JSON template** — any SessionConfig field can be a campaign default; user overrides at session creation
4. **Soft archive, not hard delete** — archived campaigns remain queryable with all their sessions
5. **Session reassignment is a move, not a copy** — sessions have physical ledger files; moving the FK is clean
6. **Stats aggregated on-demand** — no materialized views; computed from session `results_summary` at query time

## Status: ⏳ NOT STARTED
