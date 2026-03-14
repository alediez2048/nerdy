# P2-07 Primer: End-to-End Integration Test

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P1-20 (full pipeline run), P0-08 (checkpoint-resume), P1-13 (batch processor) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P2-07 implements the **end-to-end integration test** — the ultimate validation that the pipeline works as a complete system. Start the pipeline, interrupt it mid-batch, resume from checkpoint, and verify the resumed run produces identical output with no duplicated work, no lost work, and no corrupted state.

### Why It Matters

- **State Is Sacred** (Pillar 5): Checkpoint-resume must preserve the complete pipeline state across interruptions
- R3-Q2 selected checkpoint-and-resume as the resilience strategy — this ticket proves it works
- On free-tier Gemini (2 RPM), 429 rate limits are steady state — the pipeline WILL be interrupted
- Without integration testing, individual components may pass unit tests but fail when combined
- This is the confidence gate before Phase 3 adds more complexity (A/B variants, UGC video)

---

## What Was Already Done

- P0-08: Checkpoint-resume infrastructure (`iterate/checkpoint.py`) with `get_pipeline_state()`, `should_skip_ad()`
- P1-13: Batch processor with `write_batch_checkpoint()` at batch boundaries
- P1-20: Pipeline runner with `run_pipeline()` orchestrating full end-to-end flow
- P0-02: Append-only ledger — all state persisted in JSONL

---

## What This Ticket Must Accomplish

### Goal

Build integration tests that validate the full pipeline under realistic conditions: normal completion, interrupted-and-resumed completion, and edge cases like empty batches and duplicate prevention.

### Deliverables Checklist

#### A. Integration Test Suite (`tests/test_pipeline/test_e2e_integration.py`)

- [ ] `test_full_pipeline_dry_run_completes`: Pipeline with dry_run=True completes all batches
- [ ] `test_pipeline_produces_ledger_events`: After dry_run, ledger contains expected event types (BatchCompleted at minimum)
- [ ] `test_checkpoint_resume_no_duplicates`: Run 2 batches, stop. Resume. Verify no duplicate ad_ids in ledger.
  - Simulate by running pipeline with 2 batches, then running again with resume=True
  - Count ad_ids: each should appear exactly once per event type
- [ ] `test_checkpoint_resume_completes_remaining`: Start with 5 batches, complete 2, resume. All 5 batches completed in total.
- [ ] `test_ledger_append_only_after_resume`: Ledger after resume contains all events from before + new events. No events from the first run are missing.
- [ ] `test_empty_brief_list_handles_gracefully`: Pipeline with 0 briefs completes without error
- [ ] `test_single_batch_pipeline`: Pipeline with 1 batch, 1 brief completes correctly
- [ ] `test_batch_checkpoint_events_sequential`: BatchCompleted events have sequential batch_num values
- [ ] `test_pipeline_config_propagates_to_batches`: Verify config values (threshold, ledger_path) reach batch processing
- [ ] `test_generate_briefs_deterministic`: Same config produces same brief IDs (reproducible)
- [ ] Minimum: 10+ tests

#### B. Checkpoint-Resume Validation Helpers

- [ ] `simulate_interruption(ledger_path: str, stop_after_batch: int) -> int`
  - Runs pipeline, stops after N batches, returns count of events written
  - Uses dry_run mode (no API calls needed)
- [ ] `count_unique_ad_ids(ledger_path: str, event_type: str) -> int`
  - Helper to verify no duplicate processing
- [ ] `verify_ledger_integrity(ledger_path: str) -> bool`
  - Every line is valid JSON
  - Required fields present on every event
  - Timestamps monotonically non-decreasing

#### C. Tests Use dry_run Mode

All integration tests use `dry_run=True` in PipelineConfig — no API calls needed. The point is testing orchestration, checkpointing, and state management, not LLM output quality.

#### D. Documentation

- [ ] Add P2-07 entry in `docs/DEVLOG.md`

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Checkpoint-and-resume | R3-Q2 (Option B) | Every successful API call checkpointed; resume from last checkpoint |
| Append-only ledger | Pillar 5 | State persisted in JSONL; never modify/delete existing entries |
| Batch boundaries = checkpoints | R3-Q9 | Natural checkpoint at each batch completion |

### Checkpoint-Resume Flow

```
run_pipeline(config)
  ↓
for batch in batches:
  process_batch(briefs, batch_num, config)
  write_batch_checkpoint(batch_num, result, ledger_path)  ← checkpoint
  ↓
[INTERRUPT HERE]
  ↓
run_pipeline(config)  ← resume
  ↓
get_pipeline_state(ledger_path)  ← reads existing checkpoints
  ↓
skip completed batches, continue from next
```

### Key Functions

```python
# From iterate/checkpoint.py
get_pipeline_state(ledger_path) → PipelineState  # What's been done
should_skip_ad(ad_id, stage, state) → bool        # Skip if already done

# From iterate/pipeline_runner.py
run_pipeline(config: PipelineConfig) → RunSummary
generate_briefs(config) → list[dict]

# From iterate/batch_processor.py
create_batches(briefs, batch_size) → list[list[dict]]
process_batch(briefs, batch_num, config, dry_run) → BatchResult
write_batch_checkpoint(batch_num, result, ledger_path) → str
```

### Files to Create

| File | Why |
|------|-----|
| `tests/test_pipeline/test_e2e_integration.py` | End-to-end integration tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `iterate/pipeline_runner.py` | `run_pipeline()`, `PipelineConfig`, `generate_briefs()` |
| `iterate/batch_processor.py` | `process_batch()`, `write_batch_checkpoint()` |
| `iterate/checkpoint.py` | `get_pipeline_state()`, `should_skip_ad()` |
| `iterate/ledger.py` | `log_event()`, `read_events()`, schema validation |

---

## Definition of Done

- [ ] Full pipeline completes end-to-end in dry_run mode
- [ ] Interrupted pipeline resumes correctly with no duplicated work
- [ ] Ledger integrity maintained across interruptions
- [ ] No duplicate ad_ids for same event type after resume
- [ ] All batch checkpoints written and readable
- [ ] 10+ integration tests passing
- [ ] Lint clean
- [ ] DEVLOG updated

---

## After This Ticket: What Comes Next

**Phase 2 is now complete.** The evaluation framework is validated:
- Dimension independence: proven causally (P2-01) and statistically (P2-02)
- Adversarial robustness: edge cases handled correctly (P2-03)
- Drift detection: SPC monitoring with canary injection (P2-04)
- Confidence routing: autonomous/flagged/human/brand-safety (P2-05)
- Compliance: three-layer defense-in-depth (P2-06)
- Pipeline resilience: checkpoint-resume validated end-to-end (P2-07)

**Phase 3 begins:** P3-01 (A/B variant engine) extends the pipeline from single-ad generation to multi-variant A/B testing with structured variation strategies.
