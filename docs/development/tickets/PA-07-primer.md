# PA-07 Primer: Background Job Progress Reporting

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-04 (Session CRUD) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PA-07 completes the **progress reporting infrastructure** — Celery worker publishes events to Redis pub/sub, FastAPI streams them via SSE, and the frontend hooks into the stream. The backend is largely built; this ticket closes the remaining gaps.

### Why It Matters

- **Visible Reasoning Is a First-Class Output** (Pillar 7): Users must see the pipeline working in real time
- The hybrid progress model (Section 4.7.5): background polling (30s) for the session list + SSE for Watch Live
- Without progress reporting, users stare at a loading spinner for minutes with no feedback

---

## What Was Already Done

- `app/workers/progress.py`: `publish_progress()` publishes to Redis pub/sub + caches summary. Event types: `CYCLE_START`, `BATCH_START`, `AD_GENERATED`, `AD_EVALUATED`, `AD_PUBLISHED`, `BATCH_COMPLETE`, `CYCLE_COMPLETE`, `PIPELINE_COMPLETE`, `PIPELINE_ERROR`
- `app/api/routes/progress.py`: SSE endpoint `GET /sessions/{session_id}/progress` — streams events from Redis with 15s heartbeat
- `app/workers/tasks/pipeline_task.py`: Simulated pipeline task publishes progress at every stage boundary
- `app/api/schemas/session.py`: `ProgressSummary` schema for running session cards
- `app/api/routes/sessions.py`: Session list includes `ProgressSummary` for running sessions (from Redis cache)

---

## What This Ticket Must Accomplish

### Goal

Close the remaining gaps: frontend SSE hook, Last-Event-ID reconnection support, and integration test coverage.

### Deliverables Checklist

#### A. Frontend SSE Hook (`src/hooks/useSessionProgress.ts`)

- [ ] `useSessionProgress(sessionId: string)` custom React hook
- [ ] Connects to `GET /sessions/{session_id}/progress` via `EventSource`
- [ ] Parses incoming `progress` events into typed `ProgressEvent` objects
- [ ] Handles `heartbeat` events (no-op, keeps connection alive)
- [ ] Auto-reconnects on connection drop (exponential backoff, max 3 retries)
- [ ] Returns: `{ progress: ProgressEvent | null, connected: boolean, error: string | null }`
- [ ] Cleans up EventSource on unmount

#### B. SSE API Helper (`src/api/sse.ts`)

- [ ] `createProgressStream(sessionId: string): EventSource`
- [ ] Attaches JWT token via query param (EventSource doesn't support headers): `?token=<jwt>`
- [ ] Backend must accept token from query param for SSE endpoint (update `app/api/routes/progress.py`)

#### C. Last-Event-ID Support (Backend)

- [ ] `app/api/routes/progress.py`: Read `Last-Event-ID` header on reconnection
- [ ] Buffer recent events in Redis (last 50 per session, TTL 5 min)
- [ ] On reconnect, replay missed events from buffer before streaming live

#### D. Wire Pipeline Task to Real Pipeline

- [ ] Update `app/workers/tasks/pipeline_task.py` to call the real `iterate/pipeline_runner.py` (or at least structure progress events to match real pipeline stages)
- [ ] Map pipeline stages to progress event types
- [ ] Capture real metrics (scores, costs, ads counts) from pipeline output
- [ ] On completion: update `session.results_summary` with real metrics

#### E. Tests (`tests/test_app/test_progress.py`)

- [ ] TDD first
- [ ] Test SSE endpoint streams events for valid session
- [ ] Test SSE endpoint returns 404 for non-existent session
- [ ] Test heartbeat is sent when no events for 15s
- [ ] Test progress summary cached in Redis
- [ ] Test `publish_progress()` publishes to correct channel
- [ ] Test pipeline task updates session status to "completed" with results_summary
- [ ] Minimum: 6+ tests

#### F. Documentation

- [ ] Add PA-07 entry in `docs/DEVLOG.md`

---

## Important Context

### Progress Event Schema

```json
{
  "type": "ad_evaluated",
  "cycle": 2,
  "batch": 3,
  "ads_generated": 25,
  "ads_evaluated": 24,
  "ads_published": 15,
  "current_score_avg": 7.65,
  "cost_so_far": 3.42,
  "timestamp": 1710345600.123
}
```

### Hybrid Progress Model (PRD Section 4.7.5)

| Mode | Mechanism | Where Used |
|------|-----------|------------|
| Background | Session list polls `GET /sessions` every 30s. Progress from Redis cache. | PA-06 Session List |
| Watch Live | SSE stream from `GET /sessions/{id}/progress`. Real-time. | PA-08 Watch Live |
| On completion | Status flips to "completed". Session card updates with final metrics. | Both |

### Files to Modify/Create

| File | Action |
|------|--------|
| `src/hooks/useSessionProgress.ts` | Create — React SSE hook |
| `src/api/sse.ts` | Create — SSE connection helper |
| `app/api/routes/progress.py` | Modify — add Last-Event-ID, token-from-query-param |
| `app/workers/tasks/pipeline_task.py` | Modify — wire to real pipeline |
| `tests/test_app/test_progress.py` | Create — progress tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `docs/reference/prd.md` (Section 4.7.5) | Progress monitoring spec |
| `app/workers/progress.py` | Existing progress publisher |
| `app/api/routes/progress.py` | Existing SSE endpoint |
| `app/workers/tasks/pipeline_task.py` | Existing pipeline task |
| `iterate/pipeline_runner.py` | Real pipeline to integrate |

---

## Definition of Done

- [ ] Frontend `useSessionProgress` hook connects to SSE, parses events, auto-reconnects
- [ ] SSE endpoint supports JWT via query param (for EventSource)
- [ ] Last-Event-ID reconnection replays missed events
- [ ] Pipeline task wired to real pipeline (or realistic simulation)
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time: 60–90 minutes

---

## After This Ticket: What Comes Next

**PA-08 (Watch Live Progress View)** builds the real-time dashboard that consumes the `useSessionProgress` hook from this ticket. It renders cycle indicators, score feeds, and cost accumulators from the SSE stream.
