# PH-01 Primer: LedgerWriter + LedgerReader Seam

**For:** New Agent session
**Project:** Ad-Ops-Autopilot
**Date:** May 2026
**Phase plan:** [`PH-00-phase-plan.md`](PH-00-phase-plan.md)
**Previous work:** P0–PG complete.
**Branch:** `feature/PH-01-ledger-seam`

---

## What Is This Ticket?

The append-only JSONL ledger (`data/ledger.jsonl`) is the system's source of truth — decisionlog.md §9 calls it sacred. But every module that produces events constructs raw dicts and calls `log_event(...)` directly, and every consumer parses JSONL inline. There is one file format and zero abstraction.

GitNexus blast-radius numbers for `iterate/ledger.py:log_event`:
- **CRITICAL** risk
- **22** direct callers
- **7** processes affected at earliest_broken_step=1
- **9** modules touched

This means a single field rename or a schema tightening today is a 22-file change with no compile-time safety net.

### What Is Already Done

- `iterate/ledger.py` contains the raw `log_event(event: dict)` writer (append-only JSONL, atomic-write semantics).
- Snapshot capture for full I/O exists alongside it.
- Some readers exist (`scripts/check_ledger.py`, `scripts/show_published_ads.py`) — each one parses JSONL and filters by event_type by hand.

---

## What This Ticket Must Accomplish

### Goal

Introduce a **LedgerWriter** and **LedgerReader** seam so that:
- Every event written goes through one typed method per event type (e.g. `record_ad_generated(...)`, `record_ad_evaluated(...)`, `record_ad_published(...)`).
- Every read goes through typed query methods (e.g. `events_by_type(...)`, `ad_lifecycle(ad_id)`, `costs_by_format(...)`).
- The on-disk JSONL format is **unchanged** — bytes-for-bytes identical for the same inputs.
- No `log_event(` call or `open(... ledger.jsonl ...)` exists outside the seam module (except in legacy backfill scripts that are explicitly flagged for follow-up).

### Deliverables Checklist

#### A. Design (grilling session — happens BEFORE implementation)
- [ ] Run `gitnexus_context({name: "log_event"})` and review the full caller list with the user
- [ ] Decide the event-type catalogue (one writer method per event_type currently in use)
- [ ] Decide the reader query surface (driven by the actual reads in `cost_reporter.py`, `output/export_dashboard.py`, scripts/, app/api/routes/)
- [ ] Decide handling of optional/legacy fields in old ledgers
- [ ] Confirm append-only invariant preserved

#### B. Implementation
- [ ] Create `iterate/ledger_writer.py` with `LedgerWriter` class
- [ ] Create `iterate/ledger_reader.py` with `LedgerReader` class
- [ ] Migrate all 22 `log_event` call sites to the writer's typed methods
- [ ] Migrate inline-parser call sites (~8 files) to the reader's query methods
- [ ] Keep `log_event` as a deprecated thin shim that calls the writer (avoid a flag-day if practical) — OR delete it once all callers are migrated, whichever the grilling concludes
- [ ] Confirm JSONL output is byte-identical for a fixture run (diff old-format vs. new-format ledger for the same input)

#### C. Testing
- [ ] All existing pytest suites pass (~670 tests)
- [ ] New tests: one per writer method confirming the JSONL output schema
- [ ] New tests: one per reader query confirming behavior against a fixture ledger
- [ ] Existing `tests/test_pipeline/test_e2e_integration.py` `_read_ledger` helper migrates to use the new reader

---

## Acceptance Criteria

- [ ] `git grep "log_event("` returns ZERO hits outside `iterate/ledger_writer.py` and the deprecated shim (if kept)
- [ ] `git grep "json.loads.*ledger\|open.*ledger\.jsonl"` returns ZERO hits outside `iterate/ledger_reader.py` (test fixtures excluded)
- [ ] JSONL diff between a pre-PH-01 fixture run and a post-PH-01 fixture run is **empty** (byte-identical)
- [ ] `gitnexus_impact({target: "LedgerWriter"})` shows callers in the expected modules only
- [ ] DEVLOG entry committed

---

## Key Files

| File | Action |
|------|--------|
| `iterate/ledger.py` | Source of `log_event` — becomes shim or is deleted |
| `iterate/ledger_writer.py` | **NEW** — typed writer |
| `iterate/ledger_reader.py` | **NEW** — typed reader |
| `generate/ad_generator.py` | Migrate `log_event(` calls |
| `generate/brief_expansion.py` | Migrate `log_event(` calls |
| `generate/image_generator.py` (via `_call_image_api`) | Migrate `log_event(` calls |
| `generate/ab_image_variants.py` | Migrate `log_event(` calls |
| `generate/ab_variants.py` | Migrate `log_event(` calls |
| `generate/aspect_ratio_batch.py` | Migrate `log_event(` calls |
| `generate/model_router.py` | Migrate `log_event(` calls |
| `evaluate/evaluator.py` | Migrate `log_event(` calls |
| `evaluate/weight_recalibrator.py` | Migrate `log_event(` calls |
| `evaluate/image_cost_tracker.py` | Migrate `log_event(` calls |
| `evaluate/performance_schema.py` | Migrate `log_event(` calls |
| `iterate/batch_processor.py` | Migrate ~9 `log_event(` calls |
| `iterate/image_regen.py` | Migrate `log_event(` calls |
| `iterate/brief_mutation.py` | Migrate `log_event(` calls |
| `generate_video/orchestrator.py` | Migrate `log_event(` calls |
| `generate_video/degradation.py` | Migrate `log_event(` calls |
| `app/workers/tasks/pipeline_task.py` | Migrate `log_event(` calls |
| `scripts/backfill_*.py` (3 files) | Migrate `log_event(` and inline parsers |
| `scripts/check_ledger.py` | Migrate to LedgerReader |
| `scripts/show_published_ads.py` | Migrate to LedgerReader |
| `tests/test_pipeline/test_e2e_integration.py` | Migrate `_read_ledger` helper |

---

## Out of Scope for PH-01

- Cost attribution logic (PH-02 — depends on the new Reader)
- Schema validation beyond what already exists (could be a follow-up)
- Migration to a different on-disk format (explicitly disallowed by phase decision #1)
- Backfilling fields into historical ledger entries

---

## Verification Before Merge

Per PH-00 §"Verification Gate Strategy":
1. `npx gitnexus impact <each_new_module>`
2. `python -m pytest tests/ -v`
3. `python run_pipeline.py --dry-run --max-ads 3`
4. `ruff check .`
5. JSONL byte-equality check on fixture run
6. DEVLOG entry
