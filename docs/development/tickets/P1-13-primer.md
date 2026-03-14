# P1-13 Primer: Batch-Sequential Processor

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** ALL P0 tickets and P1-01 through P1-12 must be complete. This is the orchestrator — it wires everything together. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P1-13 implements the **batch-sequential processor** — the main pipeline orchestrator (`run_pipeline.py`). It processes ads in batches of 10 (configurable via `data/config.yaml`). Within each batch: all generation runs in parallel, then all evaluation runs in parallel, then regeneration decisions are made, then all regeneration runs in parallel. Batches are processed sequentially. Batch boundaries are natural checkpoints — if the pipeline crashes mid-batch, it resumes from the last completed batch boundary.

### Why It Matters

- **This is the main entry point.** `python run_pipeline.py` is how 50+ ads get produced. Without this, all the individual modules (brief expansion, generator, evaluator, regen, ratchet, cache, token tracker) are isolated pieces that cannot produce output.
- **10x throughput** over sequential processing (R3-Q9) — parallel within stage, sequential across stages.
- **Natural checkpoints** at batch boundaries integrate with P0-08 checkpoint-resume. A crash at ad 37 means resuming from ad 31 (batch 4 start), not ad 1.
- **State Is Sacred** (Pillar 5): Batch boundaries write checkpoints to the ledger. Every completed batch is a recoverable state.
- **Visible Reasoning** (Pillar 7): The orchestrator logs the full pipeline flow — which ads were generated, evaluated, regenerated, published, or discarded — creating the narrative that the P4-07 narrated replay will consume.

---

## What Was Already Done

- **P0-02** (`iterate/ledger.py`): `log_event()`, `read_events()`, `get_ad_lifecycle()` — event storage for every pipeline action.
- **P0-03** (`generate/seeds.py`): `get_ad_seed()`, `load_global_seed()` — deterministic seed chains for reproducibility.
- **P0-03** (`iterate/snapshots.py`): `capture_snapshot()` — state preservation at batch boundaries.
- **P0-06** (`evaluate/evaluator.py`): `evaluate_ad()`, `EvaluationResult` dataclass — ad scoring.
- **P0-08** (`iterate/checkpoint.py`): `get_pipeline_state()`, `should_skip_ad()`, `get_last_checkpoint()` — resume from last checkpoint.
- **P0-08** (`iterate/retry.py`): `retry_with_backoff()` — exponential backoff on API failures.
- **P0-10** (`generate/competitive.py`): `load_patterns()`, `query_patterns()`, `get_landscape_context()` — competitive context injection.
- **P1-01** (`generate/brief_expansion.py`): Brief expansion with grounding constraints + competitive context.
- **P1-02** (`generate/ad_generator.py`): Reference-decompose-recombine ad copy generation.
- **P1-03** (`generate/brand_voice.py`): Audience-specific brand voice profiles (parent-facing, student-facing).
- **P1-04** (`evaluate/evaluator.py` updates): Chain-of-thought evaluation with contrastive rationales.
- **P1-05** (`evaluate/weighting.py`): Campaign-goal-adaptive dimension weighting with floor constraints.
- **P1-06** (`iterate/routing.py`): Tiered model routing — Flash default, Pro for 5.5-7.0, discard below 5.5.
- **P1-07** (`iterate/pareto.py`): Pareto-optimal regeneration — no dimension regression.
- **P1-08** (`iterate/mutation.py`): Brief mutation after 2 failures, escalation after 3.
- **P1-09** (`iterate/distillation.py`): Distilled context objects — compact cycle summaries.
- **P1-10** (`iterate/ratchet.py`): Quality ratchet — rolling high-water mark `max(7.0, rolling_5batch_avg - 0.5)`.
- **P1-11** (`iterate/token_tracker.py`): Token attribution — spend by stage, cost-per-published-ad.
- **P1-12** (`iterate/cache.py`): Result-level cache — skip re-evaluation of identical ad + prompt version pairs.
- **data/config.yaml**: `batch_size: 10`, `ledger_path`, `cache_path`, and all other tunable parameters.

---

## What This Ticket Must Accomplish

### Goal

Build the pipeline orchestrator that wires all P1 modules into a batch-sequential flow, processes 50+ ads across multiple batches and iteration cycles, and writes checkpoints at batch boundaries for crash recovery.

### Deliverables Checklist

#### A. Pipeline Orchestrator (`run_pipeline.py`)

- [ ] `run_pipeline(config_path: str = "data/config.yaml", resume: bool = False) -> PipelineResult`
  - Main entry point. Reads config, initializes state, runs batches.
  - If `resume=True`: calls `get_pipeline_state()` and `get_last_checkpoint()` to determine where to pick up.
  - If `resume=False`: starts from scratch (but respects `should_skip_ad()` as a safety net).
- [ ] `process_batch(batch: list[Brief], batch_num: int, cycle: int, state: PipelineState) -> BatchResult`
  - Processes a single batch through all stages:
    1. **Expand** — Brief expansion for all ads in batch (parallel via `asyncio.gather` or `concurrent.futures`)
    2. **Generate** — Ad copy generation for all expanded briefs (parallel)
    3. **Evaluate** — Evaluation with cache check for all generated ads (parallel). Cache hits skip API call.
    4. **Route** — Tiered routing: publish (>7.0), regenerate (5.5-7.0), discard (<5.5)
    5. **Regenerate** — Pareto-optimal regeneration for routed ads (parallel). Brief mutation after 2 failures.
    6. **Re-evaluate** — Evaluate regenerated ads (parallel, cache-aware)
    7. **Finalize** — Apply quality ratchet. Log terminal states (published/discarded).
  - Each step wrapped in `retry_with_backoff()` for individual API calls.
  - Returns `BatchResult` with counts: generated, published, discarded, regenerated, escalated.
- [ ] `write_batch_checkpoint(batch_num: int, cycle: int, ledger_path: str) -> str`
  - Logs a `BatchCheckpoint` event to the ledger after each batch completes
  - Returns the `checkpoint_id`
  - Calls `capture_snapshot()` for full state preservation
- [ ] CLI interface via `argparse`:
  - `python run_pipeline.py` — full run from scratch
  - `python run_pipeline.py --resume` — resume from last checkpoint
  - `python run_pipeline.py --config path/to/config.yaml` — custom config
  - `python run_pipeline.py --batches N` — limit number of batches (for testing)
  - `python run_pipeline.py --cycles N` — limit iteration cycles

#### B. Batch Logic

- [ ] Batch size from `config.yaml` (`batch_size: 10`)
- [ ] Briefs divided into batches of N. Last batch may be smaller.
- [ ] Within each batch: stages run in parallel (all generation, then all evaluation, etc.)
- [ ] Between batches: sequential. Shared state (quality ratchet, token totals, distilled context) updated only at batch boundaries.
- [ ] Iteration cycles: after all batches complete one pass, check if more regeneration cycles are needed. Cycle count configurable.

#### C. Pipeline Result (`PipelineResult` dataclass)

- [ ] Fields: `total_generated`, `total_published`, `total_discarded`, `total_regenerated`, `total_escalated`, `batches_completed`, `cycles_completed`, `token_summary` (from P1-11), `final_ratchet_threshold`, `elapsed_time`
- [ ] Printed as a summary table at pipeline completion

#### D. Error Handling

- [ ] Individual ad failures do NOT crash the batch. Log the error, mark the ad as "errored", continue.
- [ ] Batch failures (e.g., total API outage) write a partial checkpoint and exit gracefully.
- [ ] `--resume` picks up from the last successful batch checkpoint.
- [ ] All errors logged to ledger with full context (ad_id, stage, error message, retry count).

#### E. Tests (`tests/test_pipeline/test_batch_processor.py`)

- [ ] TDD first
- [ ] Test batch division: 25 briefs with batch_size=10 yields batches of [10, 10, 5]
- [ ] Test `should_skip_ad` integration: already-completed ads in a batch are skipped
- [ ] Test checkpoint written after each batch
- [ ] Test resume skips completed batches
- [ ] Test individual ad error does not crash batch (remaining ads still processed)
- [ ] Test quality ratchet updates between batches (not within)
- [ ] Test token attribution accumulates across batches
- [ ] Test pipeline result contains correct totals
- [ ] Minimum: 8+ tests

#### F. Documentation

- [ ] Add P1-13 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

All work is done directly on `develop`. No feature branches.

```bash
git switch develop && git pull
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Batch-sequential processing | R3-Q9 | Batches of 10. Parallel within stage, sequential across stages. 10x throughput over sequential. Natural checkpoints at batch boundaries. |
| Checkpoint-resume | R3-Q2 | Batch boundaries = checkpoints. Resume from last completed batch. |
| Quality ratchet | R1-Q9 | Rolling high-water mark updated between batches only. `max(7.0, rolling_5batch_avg - 0.5)`. |
| Brief mutation + escalation | R1-Q2 | After 2 failures: mutate brief. After 3: escalate with diagnostics. |
| Tiered routing | R1-Q4 | <5.5 discarded, >7.0 published, 5.5-7.0 escalated to Pro. |

### Files to Create

| File | Why |
|------|-----|
| `run_pipeline.py` | Main pipeline entry point — the orchestrator |
| `tests/test_pipeline/test_batch_processor.py` | Batch processor tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `iterate/checkpoint.py` | Resume logic: `get_pipeline_state()`, `should_skip_ad()` |
| `iterate/ledger.py` | Event logging for every pipeline action |
| `iterate/retry.py` | `retry_with_backoff()` wraps every API call |
| `iterate/cache.py` | Cache-aware evaluation (P1-12) |
| `iterate/token_tracker.py` | Token attribution (P1-11) |
| `iterate/ratchet.py` | Quality ratchet (P1-10) |
| `iterate/routing.py` | Tiered model routing (P1-06) |
| `iterate/pareto.py` | Pareto-optimal regeneration (P1-07) |
| `iterate/mutation.py` | Brief mutation + escalation (P1-08) |
| `iterate/distillation.py` | Distilled context objects (P1-09) |
| `generate/brief_expansion.py` | Brief expansion (P1-01) |
| `generate/ad_generator.py` | Ad copy generation (P1-02) |
| `generate/brand_voice.py` | Brand voice profiles (P1-03) |
| `evaluate/evaluator.py` | Ad evaluation (P0-06, P1-04) |
| `evaluate/weighting.py` | Dimension weighting (P1-05) |
| `data/config.yaml` | `batch_size`, `ledger_path`, `cache_path`, all params |

---

## Definition of Done

- [ ] `python run_pipeline.py` processes 50+ ads across 5+ batches
- [ ] Parallel within stage, sequential across stages
- [ ] Batch boundaries write checkpoints to ledger
- [ ] `python run_pipeline.py --resume` picks up from last completed batch
- [ ] Individual ad errors do not crash the pipeline
- [ ] Quality ratchet threshold only increases across batches
- [ ] Token attribution summary printed at completion
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Committed on `develop`

---

## Estimated Time: 90–120 minutes

---

## After This Ticket: What Comes Next

- **P1-14** (Nano Banana Pro integration) — Image generation, visual spec extraction, multi-variant generation. Extends the pipeline with an image stage.
- **P2-07** (End-to-end integration test) — Full pipeline with checkpoint-resume: start, kill, resume = identical output.
- **P1-20** (50+ full ad generation run) — Uses this orchestrator to produce the final corpus of 50+ ads meeting quality thresholds.
