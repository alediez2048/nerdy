# P0-08 Primer: Checkpoint-Resume Infrastructure

**For:** New Cursor Agent session  
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG  
**Date:** March 2026  
**Previous work:** P0-02 (decision ledger), P0-03 (seeds + snapshots) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P0-08 implements the **checkpoint-and-resume architecture** so the pipeline can survive API failures, rate limits, and crashes without losing work. On Gemini's free tier (15 RPM Flash, 2 RPM Pro), 429 errors aren't exceptions — they're the steady state. The pipeline must handle interruptions gracefully.

### Why It Matters

- **State is Sacred** (Pillar 5): No work is ever lost. Every run is recoverable.
- Gemini free tier rate limits guarantee frequent interruptions
- `python run_pipeline.py --resume` must pick up from the last checkpoint — no duplicated work
- Without this, every API error means re-running the entire batch from scratch

---

## What Was Already Done

- P0-02: Decision ledger with `checkpoint_id` on every event
- P0-03: Per-ad seed chains (identity-derived, order-independent)
- P0-01: Config.yaml with pipeline parameters

---

## What This Ticket Must Accomplish

### Goal

Build the checkpoint-resume layer that reads the ledger to determine pipeline state and resumes from the last successful checkpoint.

### Deliverables Checklist

#### A. Checkpoint Module (`iterate/checkpoint.py`)

- [ ] `get_pipeline_state(ledger_path: str) -> PipelineState`
  - Reads the ledger and determines:
    - Which ads have been generated (ad_ids with AdGenerated events)
    - Which ads have been evaluated (ad_ids with AdEvaluated events)
    - Which ads are in regeneration (ad_ids with AdRegenerated events)
    - Which ads are published/discarded (terminal states)
    - Which briefs have NOT been started yet
  - Returns a structured state object
- [ ] `get_last_checkpoint(ledger_path: str) -> str | None`
  - Returns the most recent checkpoint_id, or None if ledger is empty
- [ ] `should_skip_ad(state: PipelineState, ad_id: str, stage: str) -> bool`
  - Returns True if the ad has already completed this stage (prevents double-processing)

#### B. Retry Logic (`iterate/retry.py`)

- [ ] `retry_with_backoff(func, max_retries: int = 3, base_delay: float = 2.0) -> Any`
  - Exponential backoff: 2^n seconds, capped at 60s
  - Catches 429 (rate limit), 500, 503 (server errors)
  - Logs each retry attempt
  - After max_retries: raises typed exception, does NOT crash the pipeline
- [ ] Fixed inter-call delay (configurable, default 1–2 seconds) to respect rate limits proactively

#### C. Tests (`tests/test_pipeline/test_checkpoint.py`)

- [ ] TDD first
- [ ] Test `get_pipeline_state` correctly identifies completed/pending ads from ledger
- [ ] Test `should_skip_ad` returns True for already-completed stages
- [ ] Test `should_skip_ad` returns False for pending stages
- [ ] Test resume produces no duplicate ad_ids in the ledger
- [ ] Test retry with backoff retries the correct number of times
- [ ] Test retry raises after max_retries exceeded
- [ ] Test empty ledger returns clean initial state
- [ ] Minimum: 7+ tests

#### D. Documentation

- [ ] Add P0-08 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/P0-08-checkpoint-resume
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Checkpoint-resume | R3-Q2 | After every successful API call, write to ledger with checkpoint_id. Resume from last checkpoint. |
| API resilience | R3-Q2 | Exponential backoff on 429/500/503. Fixed delay between calls. 3 retries max. |

### Files to Create

| File | Why |
|------|-----|
| `iterate/checkpoint.py` | Pipeline state detection and skip logic |
| `iterate/retry.py` | Retry with exponential backoff |
| `tests/test_pipeline/test_checkpoint.py` | Checkpoint + retry tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| P0-02 ledger module | How events are stored |
| `.cursor/rules/pipeline-patterns.mdc` | Checkpoint-resume architecture spec |
| `interviews.md` (R3-Q2) | Full rationale for checkpoint-resume design |

---

## Definition of Done

- [ ] `get_pipeline_state()` correctly reconstructs state from ledger
- [ ] `should_skip_ad()` prevents double-processing
- [ ] Retry with exponential backoff handles 429/500/503
- [ ] `--resume` flag concept is testable (start, stop, resume = same output)
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**P0 is now complete.** The foundation is ready:
- Decision ledger (P0-02) ✅
- Deterministic seeds (P0-03) ✅
- Brand knowledge base (P0-04) ✅
- Reference ads + patterns (P0-05) ✅
- Calibrated evaluator (P0-06) ✅
- Golden set regression tests (P0-07) ✅
- Checkpoint-resume (P0-08) ✅

**Phase 1 begins:** P1-01 (Brief expansion engine) is the first ticket.
