# PF-05 Primer: Bug Fix Sprint — Backend Issues

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PF-02 (session QA), PF-03 (dashboard QA) — bug reports produced. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PF-05 fixes all backend bugs identified in PF-02 and PF-03: API endpoints, pipeline execution, progress reporting, ledger handling, and error recovery. Work through the bug report by severity.

### Why It Matters

- Backend bugs cause data loss, incorrect results, or pipeline crashes
- Progress reporting gaps leave users staring at a stuck screen
- Ledger corruption or missing events break dashboard data
- Silent API failures are worse than visible frontend errors

---

## What This Ticket Must Accomplish

### Goal

Fix all P0/P1 backend bugs. Ensure pipeline execution, API endpoints, and data flows are robust.

### Common Backend Bug Categories

#### A. Session & Pipeline Execution

- [ ] Session creation fails silently (Celery task not triggered)
- [ ] Pipeline crashes mid-run without updating session status to "failed"
- [ ] Video pipeline not routing correctly for certain config combinations
- [ ] Image pipeline regressions from video pipeline changes
- [ ] Checkpoint-resume not working after crash

#### B. API Endpoint Issues

- [ ] `GET /sessions` returning incorrect data
- [ ] `GET /sessions/{id}` not including all required fields
- [ ] `DELETE /sessions/{id}` not cleaning up resources
- [ ] Ad preview (`_get_session_ad_preview`) returning stale/wrong data
- [ ] Share token endpoint generating invalid tokens

#### C. Progress Reporting

- [ ] SSE events not published for certain pipeline stages
- [ ] Progress summary showing stale data after completion
- [ ] Video-specific progress stages not emitting
- [ ] Progress percentages incorrect or stuck at 0/100

#### D. Data Integrity

- [ ] Ledger events missing required fields
- [ ] Results summary not updated on session completion
- [ ] Score calculations incorrect (weighted avg vs simple mean)
- [ ] Token consumption not logged for all API calls
- [ ] Video events (`VideoSelected`, `VideoBlocked`) not written correctly

#### E. Error Handling

- [ ] API calls returning 500 without useful error messages
- [ ] Pipeline silently swallowing exceptions
- [ ] Missing API key detection (FAL_KEY, GEMINI_API_KEY)
- [ ] Rate limit errors not handled with retry
- [ ] Database connection errors not handled gracefully

### Process

1. Read `docs/development/PF-02-bug-report.md` for backend bugs
2. Sort by severity
3. For each bug:
   - Reproduce (via test or manual API call)
   - Fix the root cause
   - Add regression test if practical
   - Verify fix
4. Run `ruff check . --fix` — lint clean
5. Run `pytest tests/ -v` — all tests pass

---

## Branch & Merge Workflow

Work on `video-implementation-2.0` branch (current branch).

---

## Important Context

### Files to Modify

Depends on bugs found. Common files:

| File | Likely Issues |
|------|--------|
| `app/workers/tasks/pipeline_task.py` | Pipeline execution, status updates |
| `app/api/routes/sessions.py` | Session CRUD, ad preview |
| `app/workers/progress.py` | SSE progress reporting |
| `output/export_dashboard.py` | Dashboard data assembly |
| `generate_video/orchestrator.py` | Video pipeline |
| `iterate/batch_processor.py` | Image pipeline |
| `iterate/ledger.py` | Event logging |

### Files You Should NOT Modify

- Frontend code (frontend bugs are PF-04)
- Test data files
- Documentation (unless fixing doc bugs)

---

## Definition of Done

- [ ] All P0 (blocking) backend bugs fixed
- [ ] All P1 (major) backend bugs fixed
- [ ] Regression tests added for critical fixes
- [ ] `ruff check .` clean
- [ ] `pytest tests/` passes
- [ ] Bug report updated with resolution status
- [ ] DEVLOG updated

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Read bug report + prioritize | 5 min |
| Fix P0 bugs | 20–40 min |
| Fix P1 bugs | 20–40 min |
| Add regression tests | 10–20 min |
| Verify all fixes | 10 min |
| DEVLOG | 5 min |

---

## After This Ticket: What Comes Next

- **PF-06:** Test coverage audit
- **PF-08:** Production readiness
