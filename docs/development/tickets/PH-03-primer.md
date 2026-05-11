# PH-03 Primer: PipelineOrchestrator — CLI ↔ Celery Convergence

**For:** New Agent session
**Project:** Ad-Ops-Autopilot
**Date:** May 2026
**Phase plan:** [`PH-00-phase-plan.md`](PH-00-phase-plan.md)
**Depends on:** PH-01 (LedgerWriter)
**Branch:** `feature/PH-03-orchestrator`

---

## What Is This Ticket?

`iterate/batch_processor.process_batch` has **two upstream entry points** that each reconstruct the same surrounding orchestration:

| Entry point | File | What it duplicates |
|---|---|---|
| `main()` | `run_pipeline.py` | Config normalization, batch counting, dry-run handling, persona defaults, progress logging (to stdout) |
| `run_pipeline_session()` | `app/workers/tasks/pipeline_task.py` | Same — but progress is published to Redis for SSE consumers, and stages are split into `_run_image_pipeline` / `_run_video_pipeline` branches |

Both paths produce equivalent ledger writes and DB state, but the orchestration code is two parallel implementations. Add a third entry point (e.g. a webhook trigger, or a scheduled job) and it becomes three. GitNexus confirms `process_batch` has both `main` and `run_pipeline_session` as direct callers.

---

## What This Ticket Must Accomplish

### Goal

A single **PipelineOrchestrator** with:
- One public method: `run(session_config, *, progress_sink) -> PipelineResult`
- A `ProgressSink` protocol with two adapters: `StdoutProgressSink` (CLI) and `RedisProgressSink` (Celery)
- All config normalization (persona defaults, format defaults, batch math, dry-run) absorbed inside

The CLI entry point becomes a thin wrapper:
```python
# run_pipeline.py
def main():
    args = parse_args()
    config = load_session_config(args)
    PipelineOrchestrator().run(config, progress_sink=StdoutProgressSink())
```

The Celery task becomes a thin wrapper:
```python
# app/workers/tasks/pipeline_task.py
@celery_app.task
def run_pipeline_session(session_id):
    config = load_session_config_from_db(session_id)
    PipelineOrchestrator().run(config, progress_sink=RedisProgressSink(session_id))
```

### Deliverables Checklist

#### A. Design (grilling session — BEFORE implementation)
- [ ] Read both entry points side-by-side and enumerate every divergence (config keys handled, error handling, retry behavior)
- [ ] Decide the `ProgressSink` interface — event names, payload shape, ordering guarantees
- [ ] Decide where format-specific branches (`_run_image_pipeline` vs `_run_video_pipeline`) live — inside the orchestrator, or as injected strategies?
- [ ] Decide handling of `--resume` (checkpoint) — must work identically from both entry points

#### B. Implementation
- [ ] Create `iterate/pipeline_orchestrator.py` with `PipelineOrchestrator` + `ProgressSink` protocol
- [ ] Create `iterate/progress_sinks.py` with `StdoutProgressSink`, `RedisProgressSink`, `NullProgressSink` (for tests)
- [ ] Migrate `run_pipeline.py:main` to call the orchestrator
- [ ] Migrate `app/workers/tasks/pipeline_task.py:run_pipeline_session` to call the orchestrator
- [ ] Delete duplicated config-normalization helpers from both entry points
- [ ] Wire ledger writes through PH-01's `LedgerWriter` (replace any remaining raw calls inside `process_batch`)

#### C. Testing
- [ ] All existing pytest suites pass
- [ ] New tests: orchestrator with `NullProgressSink` — verifies behavior without Celery/Redis
- [ ] New tests: progress sinks emit the expected events in the expected order
- [ ] Existing `tests/test_pipeline/test_e2e_integration.py` runs the orchestrator directly (no longer needs `_run_image_pipeline` import)
- [ ] CLI smoke: `python run_pipeline.py --dry-run --max-ads 3` produces the same stdout as before
- [ ] API smoke: trigger a session via `POST /api/sessions`, verify SSE progress events match prior format

---

## Acceptance Criteria

- [ ] `run_pipeline.py:main` is ≤ 30 lines (parses args, builds config, calls orchestrator)
- [ ] `app/workers/tasks/pipeline_task.py:run_pipeline_session` is ≤ 30 lines
- [ ] `process_batch` and the orchestration glue around it live in one module
- [ ] Adding a third entry point would be a ~15-line wrapper, not a reimplementation
- [ ] Progress event payloads on the SSE stream are unchanged (existing frontend keeps working)
- [ ] DEVLOG entry committed

---

## Key Files

| File | Action |
|------|--------|
| `iterate/pipeline_orchestrator.py` | **NEW** — public entry + format dispatch |
| `iterate/progress_sinks.py` | **NEW** — Stdout / Redis / Null adapters |
| `iterate/pipeline_runner.py` | Likely absorbed into the orchestrator |
| `iterate/batch_processor.py` | `process_batch` becomes an internal step; its public surface shrinks |
| `run_pipeline.py` | Thinned to ~30 lines |
| `app/workers/tasks/pipeline_task.py` | Thinned; `_run_image_pipeline` / `_run_video_pipeline` become orchestrator strategies |
| `tests/test_pipeline/test_e2e_integration.py` | Update entry point reference |

---

## Out of Scope for PH-03

- New entry points (webhook, scheduler) — those become easy *after* this ticket
- Changing the SSE event schema (frontend depends on it)
- Replacing Redis-based progress with a different mechanism

---

## Verification Before Merge

Standard gate plus:
- Run a session end-to-end via the API (Celery path) and observe SSE events in the frontend dashboard.
- Run a session end-to-end via the CLI (`run_pipeline.py --max-ads 3`) and confirm ledger entries match Celery-run ledger entries for the same brief (modulo timestamps and IDs).
