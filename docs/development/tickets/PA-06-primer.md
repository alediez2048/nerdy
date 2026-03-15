# PA-06 Primer: Session List UI (React)

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-05 (Brief Configuration Form) must be complete — React project, API client, design tokens. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PA-06 builds the **Session List** — the application's home screen. Flat reverse-chronological card list showing all user sessions with metadata, badges, sparklines, and filters (R5-Q2, Section 4.7.3).

### Why It Matters

- This is the **landing page** after login — the first thing users see
- Cards must convey session status at a glance: running, completed, failed
- Running sessions show live progress badges (polling every 30s)
- Filters let users find sessions quickly across many runs

---

## What Was Already Done

- PA-04: `GET /sessions` API with filtering (audience, campaign_goal, status) and pagination
- PA-05: React project structure, API client (`src/api/sessions.ts`), design tokens, TypeScript types
- `ProgressSummary` schema: `current_cycle`, `ads_generated`, `ads_evaluated`, `ads_published`, `current_score_avg`, `cost_so_far`

---

## What This Ticket Must Accomplish

### Goal

Build the session list view with session cards, status badges, quality sparklines, filters, and live progress polling for running sessions.

### Deliverables Checklist

#### A. Session List Page (`src/views/SessionList.tsx`)

- [ ] Fetch sessions from `GET /sessions` on mount
- [ ] Reverse-chronological order (newest first)
- [ ] "New Session" button → navigates to `NewSessionForm`
- [ ] Empty state when no sessions exist
- [ ] Auto-refresh running sessions every 30 seconds

#### B. Session Card (`src/components/SessionCard.tsx`)

Each card displays:
- [ ] Session name (auto-generated or user-provided)
- [ ] Created date (relative: "2 hours ago")
- [ ] Audience badge (e.g., "Parents" in cyan)
- [ ] Campaign goal badge (e.g., "Conversion" in mint)
- [ ] Status badge: pending (yellow), running (cyan pulse), completed (mint), failed (red)
- [ ] Ad count: "38/50 published"
- [ ] Average score: "7.82"
- [ ] Cost per published ad: "$0.41/ad"
- [ ] Quality sparkline (mini trend chart of scores across cycles)
- [ ] Click → navigate to session detail (PA-09)

For **running sessions**, replace metrics with:
- [ ] Progress summary from `ProgressSummary`: cycle indicator, ads generated, current avg score, cost so far
- [ ] "Watch Live" button → navigates to Watch Live view (PA-08)

#### C. Filter Bar (`src/components/SessionFilters.tsx`)

- [ ] Audience filter: All / Parents / Students
- [ ] Campaign goal filter: All / Awareness / Conversion
- [ ] Status filter: All / Running / Completed / Failed
- [ ] Filters apply via query params to `GET /sessions`
- [ ] Clear all filters button

#### D. Sparkline Component (`src/components/Sparkline.tsx`)

- [ ] Tiny inline chart (< 100px wide) showing score trend per cycle
- [ ] SVG-based, no external charting library needed
- [ ] Color: cyan for improvement, red for regression

#### E. Pagination

- [ ] Load more button or infinite scroll
- [ ] Uses `offset` + `limit` from PA-04 API

#### F. Tests

- [ ] Test session cards render with correct metadata
- [ ] Test status badge shows correct color per status
- [ ] Test filters update the session list
- [ ] Test running session shows progress instead of final metrics
- [ ] Test empty state renders when no sessions
- [ ] Minimum: 5+ tests

#### G. Documentation

- [ ] Add PA-06 entry in `docs/DEVLOG.md`

---

## Important Context

### Session List Spec (PRD Section 4.7.3)

> Flat reverse-chronological card list. Each card: session name, date, audience/goal badges, ad count, avg score, visual score, cost/ad, quality sparkline, status badge. Filters by audience, goal, date range, status. Running sessions show progress badge updated every 30s.

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Flat list, no nesting | R5-Q2 | Simple reverse-chronological. No folders or grouping. |
| 30s polling for running | R5-Q4 | Session list polls; Watch Live uses SSE |
| Card-based layout | Section 4.7.3 | Each session is a card with badges and sparkline |

### Files to Create

| File | Why |
|------|-----|
| `src/views/SessionList.tsx` | Session list page |
| `src/components/SessionCard.tsx` | Individual session card |
| `src/components/SessionFilters.tsx` | Filter bar |
| `src/components/Sparkline.tsx` | Inline quality trend chart |
| `src/components/Badge.tsx` | Reusable badge component |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `docs/reference/prd.md` (Section 4.7.3) | Session list spec |
| `docs/reference/prd.md` (Section 4.7.10) | Component decomposition + design tokens |
| `src/api/sessions.ts` | API client from PA-05 |
| `src/types/session.ts` | TypeScript types from PA-05 |
| `src/design/tokens.ts` | Design system tokens |

---

## Definition of Done

- [ ] Session list renders as reverse-chronological cards
- [ ] Each card shows name, date, badges, score, cost/ad, sparkline, status
- [ ] Running sessions show progress + "Watch Live" button
- [ ] Filters work (audience, goal, status)
- [ ] 30s auto-refresh for running sessions
- [ ] Empty state for no sessions
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time: 90–120 minutes

---

## After This Ticket: What Comes Next

**PA-07 (Background Job Progress Reporting)** handles the SSE infrastructure for real-time progress. The session list's 30s polling from this ticket is the "background" mode; PA-07's SSE is the "Watch Live" mode used by PA-08.
