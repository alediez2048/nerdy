# PA-09 Primer: Session Detail — Dashboard Integration

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-04 (Session CRUD API), PA-06 (Session list UI), P5-01 through P5-06 (dashboard panels) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PA-09 **wraps the existing 5-tab dashboard** (built in Phase 5) inside a session context. When a user clicks a session from the session list, they see that session's dashboard — scoped to that session's ledger data only. This ticket adds breadcrumb navigation, a back button, and ensures all dashboard panels read from the selected session's data rather than a global ledger.

### Why It Matters

- **State Is Sacred** (Pillar 5): Each session is an immutable pipeline run — the dashboard must reflect exactly that session's data, no cross-contamination
- The Phase 5 dashboard was built for a single global pipeline run; this ticket makes it multi-session-aware
- Breadcrumb navigation keeps users oriented: Session List > Session Name > Dashboard Tab
- This is the primary way users review completed (and in-progress) sessions

---

## What Was Already Done

- P5-01: `export_dashboard.py` — generates `dashboard_data.json` from JSONL ledger
- P5-02: Dashboard panels 1-2 (Pipeline Summary + Iteration Cycles)
- P5-03: Dashboard panels 3-4 (Quality Trends + Dimension Deep-Dive)
- P5-04: Dashboard panel 5 (Ad Library)
- P5-05: Dashboard panel 6 (Token Economics)
- P5-06: Dashboard panels 7-8 (System Health + Competitive Intel)
- PA-04: Session CRUD API with `GET /sessions/:id` detail endpoint
- PA-06: Session list UI with clickable cards

---

## What This Ticket Must Accomplish

### Goal

Embed the existing 5-tab dashboard inside a session detail view, scoped to the selected session's ledger data, with breadcrumb navigation and a back button.

### Deliverables Checklist

#### A. Session Detail Page (`frontend/src/pages/SessionDetail.tsx`)

- [ ] Route: `/sessions/{sessionId}`
- [ ] Fetches session metadata from `GET /sessions/:id`
- [ ] Displays session header: name, audience, campaign goal, status badge, date, cost summary
- [ ] Breadcrumb: `Sessions > {Session Name}`
- [ ] Back button returns to session list (preserving filters/scroll position if feasible)
- [ ] Renders the 5-tab dashboard component, passing `sessionId` as context

#### B. Session-Scoped Dashboard Data (`app/api/routes/dashboard.py`)

- [ ] `GET /sessions/{sessionId}/dashboard` — returns dashboard data scoped to session
  - Reads session's ledger path from session record
  - Runs the same aggregation logic as `export_dashboard.py` but filtered to this session's ledger
  - Returns JSON matching the existing `dashboard_data.json` schema
- [ ] Caches dashboard data in Redis with TTL (re-compute only on new data)
- [ ] For running sessions, dashboard data updates as pipeline progresses (cache invalidated on new events)

#### C. Dashboard Shell Adaptation (`frontend/src/components/Dashboard.tsx`)

- [ ] Modify existing dashboard component to accept `sessionId` prop
- [ ] Replace static `dashboard_data.json` fetch with `GET /sessions/{sessionId}/dashboard` API call
- [ ] All 5 existing tabs render identically but with session-scoped data
- [ ] Loading state while dashboard data is fetched
- [ ] Error state if session has no data yet (new session, pipeline not started)

#### D. Tab Navigation

- [ ] Tab 1: Pipeline Summary + Iteration Cycles (P5-02)
- [ ] Tab 2: Quality Trends + Dimension Deep-Dive (P5-03)
- [ ] Tab 3: Ad Library (P5-04)
- [ ] Tab 4: Token Economics (P5-05)
- [ ] Tab 5: System Health + Competitive Intel (P5-06)
- [ ] Active tab persists in URL query param (`?tab=2`) for shareability
- [ ] Tab state preserved when navigating away and back

#### E. Tests (`tests/test_app/test_session_dashboard.py`)

- [ ] TDD first
- [ ] Test dashboard endpoint returns data scoped to correct session
- [ ] Test dashboard endpoint returns 404 for nonexistent session
- [ ] Test dashboard data schema matches existing `dashboard_data.json` format
- [ ] Test cache invalidation when session has new events
- [ ] Test empty session returns appropriate empty state
- [ ] Minimum: 5+ tests

#### F. Frontend Tests (`tests/test_frontend/test_session_detail.test.tsx`)

- [ ] Test breadcrumb renders with session name
- [ ] Test back button navigates to session list
- [ ] Test all 5 tabs render with session data
- [ ] Test tab selection persists in URL
- [ ] Minimum: 4+ tests

#### G. Documentation

- [ ] Add PA-09 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/PA-09-session-dashboard
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Session-scoped dashboard | R5-Q8 | Wrap existing dashboard in session context; all data scoped to selected session's ledger |
| Immutable sessions | R5-Q1 | One session = one pipeline run; dashboard reads from immutable session data only |
| Data storage | R2-Q8 | Append-only JSONL ledger per session is the source of truth for dashboard aggregation |

### Files to Create

| File | Why |
|------|-----|
| `frontend/src/pages/SessionDetail.tsx` | Session detail page with dashboard integration |
| `app/api/routes/dashboard.py` | Session-scoped dashboard data endpoint |
| `tests/test_app/test_session_dashboard.py` | Backend tests |
| `tests/test_frontend/test_session_detail.test.tsx` | Frontend tests |

### Files to Modify

| File | Action |
|------|--------|
| `frontend/src/App.tsx` | Add `/sessions/:id` route |
| `frontend/src/components/Dashboard.tsx` | Accept `sessionId` prop, fetch from API instead of static JSON |
| `frontend/src/components/SessionList.tsx` | Make cards clickable, navigate to session detail |
| `docs/DEVLOG.md` | Add ticket entry |

### Files You Should NOT Modify

- Dashboard panel components (P5-02 through P5-06) — they should work unchanged with session-scoped data
- `export_dashboard.py` — keep the CLI export script as-is; the API endpoint reuses its logic

### Files You Should READ for Context

| File | Why |
|------|-----|
| P5-01 primer | Dashboard data export script and schema |
| P5-02 through P5-06 primers | Dashboard panel structure and data requirements |
| PA-04 primer | Session detail API endpoint |
| PA-06 primer | Session list component structure |
| `interviews.md` (R5-Q8) | Rationale for session-scoped dashboard |

---

## Suggested Implementation Pattern

```python
# app/api/routes/dashboard.py
@router.get("/sessions/{session_id}/dashboard")
async def get_session_dashboard(session_id: str, db: Session = Depends(get_db)):
    session = db.query(PipelineSession).get(session_id)
    if not session:
        raise HTTPException(404)

    # Check Redis cache first
    cached = redis.get(f"session:{session_id}:dashboard")
    if cached:
        return json.loads(cached)

    # Reuse export_dashboard logic scoped to session ledger
    data = aggregate_dashboard_data(session.ledger_path)
    redis.set(f"session:{session_id}:dashboard", json.dumps(data), ex=300)
    return data
```

```tsx
// frontend/src/pages/SessionDetail.tsx
function SessionDetail() {
  const { sessionId } = useParams();
  const { data: session } = useQuery(["session", sessionId], () => fetchSession(sessionId));

  return (
    <div>
      <Breadcrumb items={[
        { label: "Sessions", href: "/sessions" },
        { label: session?.name }
      ]} />
      <SessionHeader session={session} />
      <Dashboard sessionId={sessionId} />
    </div>
  );
}
```

---

## Edge Cases to Handle

1. Session exists but pipeline hasn't started yet — show "Pipeline not started" empty state
2. Session is currently running — dashboard shows partial data, refreshes on new events
3. Session's ledger file is missing or corrupt — show error state with session metadata still visible
4. Deep-linking to a specific tab (`?tab=3`) — tab renders correctly on initial load
5. Session list scroll position lost on back navigation — use `useNavigate` state or session storage

---

## Definition of Done

- [ ] Clicking a session opens the existing dashboard filtered to that session's data
- [ ] Breadcrumb navigation shows Sessions > Session Name
- [ ] Back button returns to session list
- [ ] All 5 dashboard tabs render with session-scoped data
- [ ] Active tab persists in URL
- [ ] Running sessions show updating dashboard data
- [ ] Tests pass (`python -m pytest tests/ -v`)
- [ ] Lint clean (`ruff check . --fix`)
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Dashboard API endpoint + caching | 30 min |
| SessionDetail page + breadcrumb + routing | 25 min |
| Dashboard component adaptation (sessionId prop) | 20 min |
| Tab URL persistence | 10 min |
| Backend tests | 20 min |
| Frontend tests | 20 min |
| DEVLOG update | 5–10 min |

---

## After This Ticket: What Comes Next

**PA-10 (Curation layer + Curated Set tab)** adds a 6th tab to the dashboard for ad curation — select, reorder, annotate, edit, and export ads. PA-09 provides the session-scoped dashboard shell that PA-10 extends.
