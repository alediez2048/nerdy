# PA-04 Primer: Session CRUD API

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-01 (FastAPI scaffold), PA-02 (database schema), PA-03 (Google SSO) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PA-04 implements the **REST API endpoints** for creating, listing, and viewing ad generation sessions. Creating a session triggers a Celery background job to execute the pipeline. This is the bridge between the frontend brief config form and the backend pipeline.

### Why It Matters

- **The Tool Is the Product** (Pillar 9): Sessions are the primary unit of work — every interaction starts with creating or viewing a session
- Session creation must be fast (return immediately, run pipeline in background) (R5-Q1)
- List endpoint must support filtering and sorting for power users (R5-Q2)
- Detail endpoint must return full results for the dashboard integration (R5-Q8)
- Per-user isolation (R5-Q5) enforced on every query

---

## What Was Already Done

- PA-01: FastAPI scaffold with Celery worker
- PA-02: Sessions model with config JSONB, status enum, results_summary
- PA-03: `get_current_user` dependency for authentication

---

## What This Ticket Must Accomplish

### Goal

Build three REST endpoints for session management: create (with Celery pipeline trigger), list (with filters/sort), and detail (with full results).

### Deliverables Checklist

#### A. Session Routes (`app/api/routes/sessions.py`)

- [ ] `POST /sessions` — Create a new session
  - Requires authentication (`get_current_user`)
  - Accepts brief config JSON body (audience, campaign_goal, ad_count + optional advanced fields)
  - Validates required fields; rejects invalid config
  - Creates session record with status `pending`
  - Generates unique ledger path: `output/sessions/{session_id}/ledger.jsonl`
  - Dispatches Celery task to execute pipeline
  - Stores `celery_task_id` on session record
  - Updates status to `running`
  - Returns session object with 201 Created (does NOT wait for pipeline to finish)

- [ ] `GET /sessions` — List user's sessions
  - Requires authentication; returns only current user's sessions
  - Default sort: reverse chronological (`created_at` DESC)
  - Query parameters for filtering:
    - `audience` — filter by audience segment
    - `campaign_goal` — filter by awareness/conversion
    - `status` — filter by session status
    - `search` — search by session name (case-insensitive LIKE)
  - Query parameters for sorting:
    - `sort_by` — `created_at`, `avg_score`, `ad_count`, `cost_total` (default: `created_at`)
    - `sort_order` — `asc` or `desc` (default: `desc`)
  - Pagination: `offset` + `limit` (default limit: 20)
  - Returns list of session summaries (not full results — keep payload light)

- [ ] `GET /sessions/{session_id}` — Session detail
  - Requires authentication; 404 if session belongs to different user
  - Returns full session object including:
    - Complete config
    - Full results_summary
    - Status + timestamps
    - Celery task status (if running)

#### B. Pydantic Schemas (`app/api/schemas/session.py`)

- [ ] `SessionCreate` — request body for POST
  - `audience: str` (required)
  - `campaign_goal: Literal["awareness", "conversion"]` (required)
  - `ad_count: int` (required, min 1, max 100)
  - `name: str | None` (optional, auto-generated if not provided)
  - `threshold: float | None` (optional, default 7.0)
  - `weights: dict | None` (optional)
  - `model_tier: Literal["flash", "pro"] | None` (optional)
  - `budget_cap: float | None` (optional)
  - `image_settings: dict | None` (optional)
- [ ] `SessionSummary` — response for list endpoint (lightweight)
- [ ] `SessionDetail` — response for detail endpoint (full data)
- [ ] `SessionListResponse` — paginated list wrapper with total count

#### C. Celery Pipeline Task (`app/workers/tasks/pipeline.py`)

- [ ] `run_pipeline_session(session_id: str)` — Celery task
  - Loads session config from database
  - Sets up session-specific ledger path
  - Calls the existing pipeline with the session's config
  - Updates session status to `completed` or `failed` on finish
  - Populates `results_summary` from ledger data on completion
  - Catches exceptions and updates status to `failed` with error info
- [ ] Task registered with Celery autodiscovery

#### D. Tests (`tests/test_app/test_sessions.py`)

- [ ] TDD first
- [ ] Test POST /sessions creates session with status `pending` → `running`
- [ ] Test POST /sessions returns 201 immediately (does not block)
- [ ] Test POST /sessions validates required fields (400 on missing audience)
- [ ] Test GET /sessions returns only current user's sessions
- [ ] Test GET /sessions filters by audience
- [ ] Test GET /sessions filters by campaign_goal
- [ ] Test GET /sessions filters by status
- [ ] Test GET /sessions search by name
- [ ] Test GET /sessions sorts by created_at desc (default)
- [ ] Test GET /sessions/{id} returns full detail
- [ ] Test GET /sessions/{id} returns 404 for other user's session
- [ ] Test session creation triggers Celery task
- [ ] Minimum: 10+ tests

#### E. Documentation

- [ ] Add PA-04 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/PA-04-session-crud
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Session = one pipeline run | R5-Q1 | Immutable config. Create session → run pipeline → results accumulate. |
| Flat list, not folders | R5-Q2 | Reverse-chronological card list. Filters + sort + search instead of hierarchy. |
| Background execution | R5-Q1, R5-Q4 | POST returns immediately. Pipeline runs in Celery worker. Status tracked via DB. |
| Per-user isolation | R5-Q5 | Every query filters by user_id. 404 (not 403) for other users' sessions. |

### Files to Create

| File | Why |
|------|-----|
| `app/api/routes/sessions.py` | Session CRUD endpoints |
| `app/api/schemas/session.py` | Pydantic request/response schemas |
| `app/workers/tasks/pipeline.py` | Celery pipeline execution task |
| `tests/test_app/test_sessions.py` | Session API tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `app/models/session.py` | Session model from PA-02 |
| `app/api/auth.py` | `get_current_user` dependency from PA-03 |
| `app/workers/celery_app.py` | Celery configuration from PA-01 |
| `docs/reference/prd.md` (Section 4.7) | Session model spec and application architecture |

---

## Definition of Done

- [ ] Session creation triggers Celery pipeline job
- [ ] List supports filter by audience, goal, status
- [ ] List supports search by name
- [ ] List supports sort by created_at, avg_score, ad_count, cost_total
- [ ] Detail returns full config + results_summary
- [ ] Per-user isolation enforced (404 for other users' sessions)
- [ ] Pydantic schemas validate all inputs
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 60–90 minutes

---

## After This Ticket: What Comes Next

**PA-05 (Brief configuration form)** builds the React frontend form that submits to `POST /sessions`. It depends on these API endpoints being functional.
