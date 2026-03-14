# PA-06 Primer: Session List UI (React)

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-01 (FastAPI scaffold), PA-02 (database schema), PA-03 (Google SSO), PA-04 (Session CRUD API), PA-05 (brief config form) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PA-06 builds the **React session list page** — a flat, reverse-chronological card list showing all of the user's ad generation sessions. Each card displays key metadata at a glance: name, date, audience/goal badges, scores, cost, and status. Filters, sort, and search let users find sessions quickly.

### Why It Matters

- **The Tool Is the Product** (Pillar 9): The session list is the home screen — users land here after login
- Flat list with filters beats nested folders for the expected volume (~10–50 sessions per user) (R5-Q2)
- Running sessions must show live progress without requiring click-through (R5-Q4)
- Quality sparklines give at-a-glance trend information — did this session improve over cycles?
- Filters + sort + search make it easy to find a specific session or compare across sessions

---

## What Was Already Done

- PA-04: `GET /sessions` endpoint with filter, sort, search, pagination
- PA-05: API client (`sessions.ts`) and TypeScript types (`session.ts`)
- PA-03: JWT authentication flow

---

## What This Ticket Must Accomplish

### Goal

Build a session list page with reverse-chronological card layout. Each card shows all key metadata. Filters, sort controls, and search bar at the top. Running sessions show progress inline.

### Deliverables Checklist

#### A. Session List Page (`app/frontend/src/pages/SessionListPage.tsx`)

- [ ] Fetches sessions from `GET /sessions` on mount
- [ ] Renders cards in reverse chronological order (newest first)
- [ ] Shows empty state when no sessions exist ("No sessions yet. Create your first one!")
- [ ] "New Session" button links to brief config form (PA-05)
- [ ] Auto-refreshes running sessions every 30 seconds (polling)
- [ ] Pagination or infinite scroll for large lists

#### B. Session Card (`app/frontend/src/components/SessionCard.tsx`)

- [ ] **Header row:** Session name + date (relative: "2 hours ago")
- [ ] **Badges:** Audience badge + Campaign goal badge (awareness = blue, conversion = green)
- [ ] **Metrics row:**
  - Ad count (e.g., "42 ads")
  - Avg text score (e.g., "7.4 avg")
  - Avg visual score (e.g., "8.1 visual")
  - Cost per ad (e.g., "$0.12/ad")
- [ ] **Quality sparkline:** Small inline chart showing per-cycle average scores (from `results_summary.quality_trend`)
- [ ] **Status badge:**
  - `pending` — gray, "Pending"
  - `running` — blue pulse animation, "Cycle X/Y" (from progress data)
  - `completed` — green, "Completed"
  - `failed` — red, "Failed"
  - `cancelled` — gray, "Cancelled"
- [ ] Click card → navigate to session detail page (PA-09)
- [ ] Hover state with subtle elevation change

#### C. Filters & Sort Bar (`app/frontend/src/components/SessionFilters.tsx`)

- [ ] **Search:** Text input with debounced search (300ms) — filters by session name
- [ ] **Audience filter:** Dropdown populated from unique audiences in user's sessions
- [ ] **Goal filter:** Dropdown — "All", "Awareness", "Conversion"
- [ ] **Status filter:** Dropdown — "All", "Pending", "Running", "Completed", "Failed"
- [ ] **Sort control:** Dropdown — "Newest first", "Oldest first", "Highest score", "Most ads", "Lowest cost"
- [ ] Filters update URL query params (shareable/bookmarkable filter state)
- [ ] "Clear filters" button when any filter is active

#### D. Quality Sparkline (`app/frontend/src/components/Sparkline.tsx`)

- [ ] Minimal inline SVG chart (no chart library dependency)
- [ ] Renders `quality_trend` array as connected line
- [ ] Shows the quality ratchet threshold as a dotted baseline
- [ ] Color: green if final score > threshold, yellow if close, red if below
- [ ] Tooltip on hover showing exact values
- [ ] Graceful fallback for sessions with < 2 data points (show single dot or dash)

#### E. Running Session Progress

- [ ] Running sessions poll for updates every 30 seconds
- [ ] Card shows "Cycle X/Y" in the status badge
- [ ] Progress bar or percentage beneath the status badge
- [ ] Smooth transition when status changes (running → completed)

#### F. Tests (`app/frontend/src/pages/__tests__/SessionListPage.test.tsx`)

- [ ] TDD first
- [ ] Test cards render with all metadata fields
- [ ] Test empty state renders when no sessions
- [ ] Test running sessions show progress badge
- [ ] Test completed sessions show green status
- [ ] Test filter by audience updates displayed cards
- [ ] Test filter by goal updates displayed cards
- [ ] Test filter by status updates displayed cards
- [ ] Test search filters by name
- [ ] Test sort by newest first (default)
- [ ] Test sort by highest score
- [ ] Test sparkline renders with quality_trend data
- [ ] Test click card navigates to detail page
- [ ] Minimum: 10+ tests

#### G. Documentation

- [ ] Add PA-06 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/PA-06-session-list-ui
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Flat list, not folders | R5-Q2 | Reverse-chronological cards. At expected volume (~10–50 sessions), flat list + filters is simpler and faster than hierarchical navigation. |
| Background polling | R5-Q4 | Session list polls every 30s for running sessions. SSE reserved for "Watch Live" view (PA-08). |
| Sparkline for trends | R5-Q2 | Quality sparkline gives at-a-glance trend without clicking into the session. |
| Status badges | R5-Q2 | Visual status at a glance: gray (pending), blue pulse (running), green (done), red (failed). |

### Files to Create

| File | Why |
|------|-----|
| `app/frontend/src/pages/SessionListPage.tsx` | Session list page |
| `app/frontend/src/components/SessionCard.tsx` | Individual session card |
| `app/frontend/src/components/SessionFilters.tsx` | Filter/sort/search bar |
| `app/frontend/src/components/Sparkline.tsx` | Inline quality trend chart |
| `app/frontend/src/pages/__tests__/SessionListPage.test.tsx` | Page tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `app/api/schemas/session.py` | Response schema defining available fields (PA-04) |
| `app/frontend/src/api/sessions.ts` | API client for fetching sessions (PA-05) |
| `app/frontend/src/types/session.ts` | TypeScript types for session data (PA-05) |
| `docs/reference/prd.md` (Section 4.7) | Session list UX spec |

---

## Definition of Done

- [ ] Cards render with all metadata (name, date, badges, scores, sparkline, status)
- [ ] Running sessions show "Cycle X/Y" progress
- [ ] Filters work (audience, goal, status)
- [ ] Search filters by session name
- [ ] Sort works (newest, oldest, highest score, most ads, lowest cost)
- [ ] Sparkline renders quality trend
- [ ] Click card navigates to session detail
- [ ] Empty state renders when no sessions
- [ ] Auto-refresh for running sessions (30s polling)
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 60–90 minutes

---

## After This Ticket: What Comes Next

**PA-07 (Background job progress reporting)** adds real-time progress via Celery + Redis pub/sub + SSE, enabling the running session cards to show more granular progress without polling.
