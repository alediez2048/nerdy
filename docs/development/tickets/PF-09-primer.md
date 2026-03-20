# PF-09 Primer: Production Readiness — Performance & Monitoring

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PF-08 (environment & config). See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PF-09 audits the app for performance issues, ensures proper logging/error tracking, and adds any missing monitoring infrastructure. The focus is on observable, debuggable production behavior — not optimization.

### Why It Matters

- Silent failures in pipeline execution waste API credits without producing results
- Missing logging makes debugging production issues impossible
- Memory leaks in long-running workers cause gradual degradation
- Rate limiting prevents abuse and API key exhaustion
- Error tracking surfaces issues before users report them

---

## What This Ticket Must Accomplish

### Goal

The app logs errors visibly, handles failures gracefully, and performs acceptably for its intended workload.

### Deliverables Checklist

#### A. Logging Audit

- [ ] All pipeline stages log start/end with timing: brief expansion, ad generation, evaluation, image/video generation
- [ ] Errors logged with full context (ad_id, session_id, error type, traceback)
- [ ] No `except: pass` or `except Exception: pass` that silently swallow errors
- [ ] Log levels appropriate: DEBUG for internals, INFO for milestones, ERROR for failures
- [ ] Celery worker logs visible in Docker Compose output

#### B. Error Recovery

- [ ] Pipeline crash → session status set to "failed" (not stuck on "running")
- [ ] Individual ad failure → pipeline continues with remaining ads
- [ ] API key invalid → clear error message, pipeline stops early
- [ ] Database connection lost → graceful error, not crash
- [ ] Redis unavailable → Celery task retries or fails with message

#### C. Performance Checks

- [ ] Pipeline execution time reasonable for intended workload (3 ads in <5 min, 50 ads in <60 min)
- [ ] No obvious memory leaks in worker process (check with `resource` or manual observation)
- [ ] Dashboard data export completes in <5s for typical session
- [ ] Frontend build size reasonable (no massive unused deps)
- [ ] API response times acceptable (<500ms for list endpoints, <100ms for detail)

#### D. Rate Limiting

- [ ] Gemini API calls respect rate limits (delay between calls)
- [ ] Fal.ai API calls respect rate limits
- [ ] Retry with exponential backoff on 429 responses
- [ ] API endpoint rate limiting on FastAPI (optional — document if not implemented)

#### E. Debug Instrumentation Cleanup

- [ ] Remove `_debug_log()` function from `pipeline_task.py` (debug-specific)
- [ ] Remove `logVideoRenderDebug()` from `AdLibrary.tsx` (debug-specific)
- [ ] Remove any fetch calls to debug endpoints (e.g. `127.0.0.1:7469/ingest`)
- [ ] Remove any hardcoded session IDs or debug constants

---

## Branch & Merge Workflow

Work on `video-implementation-2.0` branch (current branch).

---

## Important Context

### Files to Modify

| File | Likely Issues |
|------|--------|
| `app/workers/tasks/pipeline_task.py` | Remove debug instrumentation, verify error handling |
| `app/frontend/src/tabs/AdLibrary.tsx` | Remove debug logging function |
| `generate_video/orchestrator.py` | Verify logging, error recovery |
| `iterate/batch_processor.py` | Verify logging, error recovery |
| `app/api/main.py` | Add request logging if missing |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `app/workers/tasks/pipeline_task.py` | Main pipeline execution |
| `generate_video/orchestrator.py` | Video pipeline execution |
| `iterate/batch_processor.py` | Image pipeline execution |
| `app/workers/celery_app.py` | Celery configuration |

### Files You Should NOT Modify

- Frontend views (unless removing debug code)
- Test files
- Documentation (documentation is PF-07)

---

## Definition of Done

- [ ] No `except: pass` patterns in pipeline code
- [ ] All pipeline stages logged with timing
- [ ] Debug instrumentation removed
- [ ] Pipeline failures set session status to "failed"
- [ ] Rate limiting in place for API calls
- [ ] Performance acceptable for intended workload
- [ ] DEVLOG updated

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Logging audit | 15 min |
| Error recovery verification | 10 min |
| Debug cleanup | 10 min |
| Performance spot-checks | 10 min |
| Rate limiting verification | 5 min |
| DEVLOG | 5 min |

---

## After This Ticket: What Comes Next

- **PF-10:** Final verification & demo preparation
