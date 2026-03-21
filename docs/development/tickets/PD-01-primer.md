# PD-01 Primer: Critical Bug Fixes

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P0-P5, PA, PB, PC phases complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

Three bugs in the pipeline produce incorrect data or will crash at runtime. Two are in `pipeline_task.py` where score averages are hardcoded to `7.0` instead of computed from real evaluation results. One is in `evaluator.py` where a ledger log references an undefined variable (`tokens_estimate`) instead of the defined `tokens_actual`, which will raise a `NameError` when `evaluate_ad()` writes to the ledger.

These are not cosmetic issues. Hardcoded scores mean the progress WebSocket stream and the final session result both report fake quality metrics, undermining the dashboard and any downstream decisions. The evaluator crash blocks the entire evaluation pipeline.

### Why It Matters
- A `NameError` in the evaluator halts ad evaluation entirely — no ads get scored or published.
- Hardcoded `avg_score: 7.0` in session results means the session detail view displays fabricated quality data.
- Hardcoded `current_score_avg: 7.0` in progress events means the real-time progress bar and batch status show fake scores to the user.
- All three violate Pillar 5 (State Is Sacred) — the system records data it did not compute.

---

## What Was Already Done

- The evaluator (`evaluate/evaluator.py`) correctly computes `tokens_actual` at line 521 and uses it in the metadata dict. The bug is specifically in the ledger `log_event` call further down where `tokens_estimate` is referenced instead.
- `pipeline_task.py` already tracks `total_generated`, `total_published`, `total_discarded`, and `total_regenerated` from real `batch_result` data — only `current_score_avg` and the final `avg_score` are hardcoded.
- `BatchResult` (in `iterate/batch_processor.py`) tracks `generated`, `published`, `discarded`, `regenerated`, `escalated` counts but does not carry score averages — scores must be read from ledger events.

---

## What This Ticket Must Accomplish

### Goal
Fix three bugs so the pipeline reports real computed data instead of hardcoded values or undefined variables.

### Deliverables Checklist

#### A. Implementation
- [ ] **Bug 1 — evaluator.py line 561:** Replace `tokens_estimate` with `tokens_actual` in the `log_event` call inside `evaluate_ad()`.
- [ ] **Bug 2 — pipeline_task.py ~line 197:** Replace hardcoded `"avg_score": 7.0` in the return dict with a real average computed from `AdPublished` events in the session ledger (read events, filter for `AdPublished`, extract `aggregate_score`, compute mean).
- [ ] **Bug 3 — pipeline_task.py ~lines 132-188:** Replace hardcoded `"current_score_avg": 7.0` in `BATCH_START`, `BATCH_COMPLETE`, and `PIPELINE_COMPLETE` progress events with a running average computed from evaluation results so far. Track a running score accumulator across the batch loop.

#### B. Tests
- [ ] Add/update test in `tests/test_pipeline/test_evaluator.py` confirming `evaluate_ad()` does not raise `NameError` and the logged event contains `tokens_consumed` matching `tokens_actual`.
- [ ] Add/update test in `tests/test_app/test_sessions.py` confirming session results contain a computed `avg_score` that differs from 7.0 when evaluation scores differ from 7.0.
- [ ] Add test verifying progress events (`BATCH_START`, `BATCH_COMPLETE`) carry a `current_score_avg` derived from real batch scores.

#### C. Integration Expectations
- [ ] Existing test suite passes with no regressions.
- [ ] Progress WebSocket events reflect real scores during a pipeline run.
- [ ] Session result `avg_score` matches the mean of published ad scores in the ledger.

#### D. Documentation
- [ ] Add PD-01 entry to `docs/development/DEVLOG.md`.

---

## Important Context

### Files to Modify

| File | Action |
|------|--------|
| `evaluate/evaluator.py` | Fix `tokens_estimate` -> `tokens_actual` in `log_event` call (~line 561) |
| `app/workers/tasks/pipeline_task.py` | Compute real `current_score_avg` in progress events (~lines 132-188) and real `avg_score` in return dict (~line 197) |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `iterate/batch_processor.py` | Understand `BatchResult` dataclass — what data is available after each batch |
| `app/workers/progress.py` | Event type constants (`BATCH_START`, `BATCH_COMPLETE`, `PIPELINE_COMPLETE`) and `publish_progress` signature |
| `iterate/ledger.py` | `read_events()` function for reading back ledger events to compute averages |
| `output/export_dashboard.py` lines 112-162 | See how `_build_pipeline_summary` computes `avg_score` from `AdPublished` events — follow the same pattern |

---

## Definition of Done

- [ ] `evaluate_ad()` logs `tokens_actual` (not `tokens_estimate`) — no `NameError` at runtime.
- [ ] Progress events carry `current_score_avg` computed from real evaluation scores seen so far in the session.
- [ ] Final session result `avg_score` is the mean of published ad aggregate scores (or 0.0 if none published).
- [ ] All existing tests pass; new tests cover all three bug fixes.
- [ ] DEVLOG updated.

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Bug 1: Fix `tokens_estimate` reference | 5 min |
| Bug 2: Compute real `avg_score` in return dict | 10 min |
| Bug 3: Compute real `current_score_avg` in progress events | 10 min |
| Tests | 5 min |
| **Total** | **30 min** |
