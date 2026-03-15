# PA-09 Primer: Session Detail — Dashboard Integration

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-08 (Watch Live) should be complete. P5 dashboard (8-panel HTML) must exist. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PA-09 integrates the **existing P5 dashboard into the application layer** as the session detail view. The P5 dashboard becomes a dynamic, session-scoped view — clicking a session card opens its dashboard with 7 tabs (R5-Q8, Section 4.7.6).

### Why It Matters

- **The Reviewer Is a User, Too** (Pillar 8): The dashboard is the primary review surface
- The P5 dashboard (P5-01 through P5-06) already has 8 panels with all the right visualizations
- This ticket bridges static HTML → dynamic React, scoped to individual sessions
- Dashboard metrics always reflect original pipeline output (never curated edits)

---

## What Was Already Done

- P5-01: `output/export_dashboard.py` — reads JSONL ledger, produces `dashboard_data.json`
- P5-02: `output/dashboard_builder.py` — generates self-contained 8-panel HTML dashboard with Chart.js
- P5-03/04: Quality trends, dimension deep-dive, ad library panels
- P5-05/06: Token economics, system health, competitive intel panels
- PA-04: `GET /sessions/{session_id}` returns session detail with config and results_summary
- PA-06: Session cards link to session detail

**The P5 dashboard currently reads from a single global `data/ledger.jsonl`. It needs to be scoped to per-session ledger files.**

---

## What This Ticket Must Accomplish

### Goal

Build dashboard API endpoints that return session-scoped data, and a React session detail page with 7 tabs that render the dashboard panels.

### Deliverables Checklist

#### A. Dashboard API Endpoints (`app/api/routes/dashboard.py`)

- [ ] `GET /sessions/{session_id}/summary` — hero metrics (ads generated, published, pass rate, avg score, cost)
- [ ] `GET /sessions/{session_id}/cycles` — per-cycle aggregation (cycle number, avg score, pass rate, cost, ads count)
- [ ] `GET /sessions/{session_id}/dimensions` — dimension scores per cycle (5 dimensions × N cycles)
- [ ] `GET /sessions/{session_id}/costs` — token attribution breakdown (by model, stage, format)
- [ ] `GET /sessions/{session_id}/ads` — full ad objects with copy, scores, status, images
- [ ] `GET /sessions/{session_id}/spc` — SPC control chart data (mean, UCL, LCL, data points)
- [ ] All endpoints read from session-scoped ledger at `session.ledger_path`
- [ ] Reuse logic from `output/export_dashboard.py` and `output/export_ad_library.py`
- [ ] Register router in `app/api/main.py`

#### B. Competitive Intelligence Endpoint

- [ ] `GET /competitive/summary` — pattern database summary (not session-scoped, shared across all)
- [ ] Reads from `data/competitive/patterns.json`

#### C. Session Detail Page (`src/views/SessionDetail.tsx`)

- [ ] Route: `/sessions/{sessionId}`
- [ ] Breadcrumb: "Sessions > Session Name"
- [ ] Back button → session list
- [ ] Session header: name, status badge, created date, config summary
- [ ] 7-tab navigation with URL-based tab persistence (`?tab=quality`)

#### D. Dashboard Tabs

1. **Overview** (`src/tabs/Overview.tsx`)
   - [ ] Hero metrics row: ads generated, published, pass rate, avg score, cost/ad, total cost
   - [ ] Quality trend chart (score per cycle)
   - [ ] Pipeline summary

2. **Quality Trends** (`src/tabs/Quality.tsx`)
   - [ ] Score distribution histogram
   - [ ] Per-cycle quality improvement line chart
   - [ ] Dimension breakdown radar chart
   - [ ] Pass/fail ratio per cycle

3. **Ad Library** (`src/tabs/AdLibrary.tsx`)
   - [ ] Grid/list of all generated ads
   - [ ] Each ad: copy, headline, description, CTA, 5 dimension scores, aggregate score, status
   - [ ] Sort by score, filter by status (published/improvable/discarded)
   - [ ] Click to expand full ad detail

4. **Competitive Intel** (`src/tabs/CompetitiveIntel.tsx`)
   - [ ] Top hook types, emotional angles, CTA styles from pattern database
   - [ ] Frequency charts
   - [ ] (Shared data, not session-scoped)

5. **Token Economics** (`src/tabs/TokenEconomics.tsx`)
   - [ ] Cost breakdown by model (Flash vs Pro)
   - [ ] Cost breakdown by stage (expansion, generation, evaluation, regen)
   - [ ] Cost per published ad trend
   - [ ] Total spend vs budget cap

6. **Curated Set** (`src/tabs/CuratedSet.tsx`)
   - [ ] Placeholder for PA-10 — show "No curated set yet" with CTA to start curating

7. **System Health** (`src/tabs/SystemHealth.tsx`)
   - [ ] SPC control chart (mean, UCL, LCL)
   - [ ] Evaluator drift monitoring
   - [ ] Regen cycle efficiency

#### E. Caching

- [ ] Cache dashboard data in Redis (TTL 5 min) — avoids re-reading JSONL on every tab switch
- [ ] Invalidate cache when session status changes

#### F. Tests (`tests/test_app/test_dashboard.py`)

- [ ] TDD first
- [ ] Test summary endpoint returns correct metrics from session ledger
- [ ] Test cycles endpoint returns per-cycle data
- [ ] Test ads endpoint returns all ads for session
- [ ] Test endpoints return 404 for non-existent session
- [ ] Test per-user isolation on dashboard endpoints
- [ ] Minimum: 5+ tests

#### G. Documentation

- [ ] Add PA-09 entry in `docs/DEVLOG.md`

---

## Important Context

### Data Wiring (PRD Section 4.7.10)

| Mock Data | Production API | Notes |
|-----------|---------------|-------|
| heroMetrics | GET /sessions/:id/summary | From decision ledger |
| cycleData | GET /sessions/:id/cycles | Per-cycle aggregation |
| dimOverTime | GET /sessions/:id/dimensions | Dimension scores per cycle |
| costData | GET /sessions/:id/costs | Token attribution output |
| sampleAds | GET /sessions/:id/ads | Full ad objects with media |
| compIntel | GET /competitive/summary | Pattern database |
| spcData | GET /sessions/:id/spc | SPC control chart data |

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Dashboard IS the session detail | R5-Q8, Section 4.7.6 | No separate detail page — the dashboard is it |
| 7 tabs | Section 4.7.10 | Overview, Quality, Ad Library, Competitive Intel, Token Economics, Curated Set, System Health |
| Session-scoped ledger | Section 4.7.2 | Each session has its own `ledger.jsonl` at `session.ledger_path` |

### Files to Create

| File | Why |
|------|-----|
| `app/api/routes/dashboard.py` | Dashboard API endpoints |
| `src/views/SessionDetail.tsx` | Session detail page with tab router |
| `src/tabs/Overview.tsx` | Overview tab |
| `src/tabs/Quality.tsx` | Quality trends tab |
| `src/tabs/AdLibrary.tsx` | Ad library tab |
| `src/tabs/CompetitiveIntel.tsx` | Competitive intel tab |
| `src/tabs/TokenEconomics.tsx` | Token economics tab |
| `src/tabs/CuratedSet.tsx` | Curated set placeholder |
| `src/tabs/SystemHealth.tsx` | System health tab |
| `tests/test_app/test_dashboard.py` | Dashboard API tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `docs/reference/prd.md` (Section 4.7.6, 4.7.10) | Dashboard integration + data wiring spec |
| `output/export_dashboard.py` | Existing dashboard data extraction logic — reuse this |
| `output/export_ad_library.py` | Ad library extraction logic — reuse this |
| `output/dashboard_builder.py` | P5 HTML dashboard — reference for what each panel shows |

---

## Definition of Done

- [ ] 7 dashboard API endpoints return session-scoped data
- [ ] Session detail page with 7 tabs
- [ ] Tab persistence in URL
- [ ] Breadcrumb navigation + back button
- [ ] Redis caching for dashboard data
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time: 120–180 minutes (largest PA ticket)

---

## After This Ticket: What Comes Next

**PA-10 (Curation Layer)** fills in the "Curated Set" tab placeholder with select, reorder, annotate, edit, and export functionality.
