# PA-07 Primer: Background Job Progress Reporting

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-04 (Session CRUD API), PA-01 (FastAPI + Celery + Redis scaffold) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PA-07 implements **real-time progress reporting** from the Celery background worker to the frontend. During a pipeline run, the Celery worker publishes structured progress events to a Redis pub/sub channel. A FastAPI SSE (Server-Sent Events) endpoint subscribes to that channel and streams updates to connected browser clients. The session list (PA-06) also polls every 30 seconds so users can see progress without clicking into a session.

### Why It Matters

- **Visible Reasoning Is a First-Class Output** (Pillar 7): Users must see what the system is doing, not just the final result
- Pipeline runs take minutes — without live progress, users assume the system is broken
- SSE is lightweight and unidirectional — perfect for progress streaming without WebSocket complexity
- Polling fallback on the session list ensures progress is visible even if SSE drops

---

## What Was Already Done

- PA-01: FastAPI backend with Celery + Redis running via Docker Compose
- PA-04: Session CRUD API with Celery pipeline job trigger
- PA-06: Session list UI with card layout and status badges
- P0-08: Checkpoint-resume infrastructure (pipeline state detection)

---

## What This Ticket Must Accomplish

### Goal

Wire Celery worker progress events through Redis pub/sub to a FastAPI SSE endpoint, and update the session list UI with real-time status via polling.

### Deliverables Checklist

#### A. Celery Progress Publisher (`app/workers/progress.py`)

- [ ] `publish_progress(session_id: str, event: ProgressEvent) -> None`
  - Publishes structured JSON to Redis channel `session:{session_id}:progress`
  - Event schema: `{ type, cycle, batch, ads_generated, ads_evaluated, ads_published, current_score_avg, cost_so_far, timestamp }`
- [ ] Event types: `cycle_start`, `batch_start`, `ad_generated`, `ad_evaluated`, `ad_published`, `batch_complete`, `cycle_complete`, `pipeline_complete`, `pipeline_error`
- [ ] Integrate progress calls into the Celery pipeline task at each stage boundary
- [ ] On pipeline error, publish `pipeline_error` event with diagnostics before raising

#### B. FastAPI SSE Endpoint (`app/api/routes/progress.py`)

- [ ] `GET /sessions/{session_id}/progress` — SSE endpoint
  - Subscribes to Redis channel `session:{session_id}:progress`
  - Streams events as `text/event-stream` with proper SSE formatting (`data:`, `event:`, `id:`)
  - Sends heartbeat every 15 seconds to keep connection alive
  - Returns 404 if session does not exist
  - Gracefully closes on client disconnect
- [ ] Include `Last-Event-ID` support for reconnection (client can resume from missed events)

#### C. Session List Polling (`app/api/routes/sessions.py`)

- [ ] `GET /sessions` response includes `progress_summary` for running sessions
  - Fields: `current_cycle`, `ads_generated`, `ads_published`, `current_score_avg`, `cost_so_far`
- [ ] Summary is read from Redis (latest cached progress), not computed on every request
- [ ] Frontend session list polls this endpoint every 30 seconds for running sessions

#### D. Frontend Integration (`frontend/src/hooks/useSessionProgress.ts`)

- [ ] `useSessionProgress(sessionId)` hook that opens EventSource to SSE endpoint
- [ ] Auto-reconnect with exponential backoff on connection drop
- [ ] Parse incoming events and expose structured progress state to components
- [ ] Session list component uses 30-second polling interval for card status updates

#### E. Tests (`tests/test_app/test_progress.py`)

- [ ] TDD first
- [ ] Test progress publisher writes correct JSON to Redis channel
- [ ] Test SSE endpoint streams events to connected client
- [ ] Test SSE endpoint sends heartbeat within timeout
- [ ] Test SSE endpoint returns 404 for nonexistent session
- [ ] Test session list includes progress_summary for running sessions
- [ ] Test reconnection with Last-Event-ID resumes correctly
- [ ] Minimum: 6+ tests

#### F. Documentation

- [ ] Add PA-07 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/PA-07-progress-reporting
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Progress reporting | R5-Q4 | Celery worker writes progress to Redis pub/sub; FastAPI SSE streams to frontend; session list polls every 30s |
| Checkpoint-resume | R3-Q2 | Progress events align with checkpoint boundaries — every stage that writes a checkpoint also publishes progress |

### Files to Create

| File | Why |
|------|-----|
| `app/workers/progress.py` | Redis pub/sub progress publisher for Celery tasks |
| `app/api/routes/progress.py` | FastAPI SSE endpoint for streaming progress |
| `frontend/src/hooks/useSessionProgress.ts` | React hook for consuming SSE progress stream |
| `tests/test_app/test_progress.py` | Progress reporting tests |

### Files to Modify

| File | Action |
|------|--------|
| `app/workers/pipeline_task.py` | Add progress publishing calls at each stage boundary |
| `app/api/routes/sessions.py` | Add `progress_summary` to session list response for running sessions |
| `frontend/src/components/SessionList.tsx` | Add 30-second polling for running session status |
| `docs/DEVLOG.md` | Add ticket entry |

### Files You Should READ for Context

| File | Why |
|------|-----|
| PA-01 primer | FastAPI + Celery + Redis scaffold structure |
| PA-04 primer | Session CRUD API and Celery job trigger |
| PA-06 primer | Session list UI component structure |
| `interviews.md` (R5-Q4) | Full rationale for progress reporting design |

---

## Suggested Implementation Pattern

```python
# app/workers/progress.py
import redis, json, time

def publish_progress(session_id: str, event: dict) -> None:
    r = redis.from_url(settings.REDIS_URL)
    event["timestamp"] = time.time()
    r.publish(f"session:{session_id}:progress", json.dumps(event))
    # Cache latest summary for polling
    r.set(f"session:{session_id}:progress_summary", json.dumps(event), ex=3600)
```

```python
# app/api/routes/progress.py
from sse_starlette.sse import EventSourceResponse

@router.get("/sessions/{session_id}/progress")
async def stream_progress(session_id: str):
    async def event_generator():
        pubsub = redis.pubsub()
        pubsub.subscribe(f"session:{session_id}:progress")
        while True:
            message = pubsub.get_message(timeout=15)
            if message and message["type"] == "message":
                yield {"data": message["data"]}
            else:
                yield {"event": "heartbeat", "data": ""}
    return EventSourceResponse(event_generator())
```

---

## Edge Cases to Handle

1. SSE connection drops mid-pipeline — frontend must auto-reconnect and not miss events
2. Multiple browser tabs open to the same session — each gets its own SSE subscription
3. Pipeline completes while no client is connected — session list polling still shows final state
4. Redis pub/sub message lost — cached summary provides fallback; no critical data lost (ledger is source of truth)
5. Session does not exist or is already complete — SSE endpoint should return appropriate status

---

## Definition of Done

- [ ] Running sessions update in real time via SSE
- [ ] Progress visible in session list without clicking in (30-second polling)
- [ ] SSE heartbeat keeps connection alive
- [ ] Auto-reconnect on connection drop
- [ ] Tests pass (`python -m pytest tests/ -v`)
- [ ] Lint clean (`ruff check . --fix`)
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Redis pub/sub publisher + Celery integration | 30 min |
| FastAPI SSE endpoint | 30 min |
| Session list polling + progress summary | 20 min |
| Frontend hook + reconnect logic | 30 min |
| Tests | 30 min |
| DEVLOG update | 5–10 min |

---

## After This Ticket: What Comes Next

**PA-08 (Watch Live progress view)** builds the dedicated progress dashboard that consumes the SSE stream established here. PA-07 provides the data transport layer; PA-08 provides the rich visualization.
