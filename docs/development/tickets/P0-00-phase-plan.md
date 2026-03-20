# Phase P0: Foundation & Calibration

## Context

P0 builds the infrastructure that every subsequent phase depends on: the append-only decision ledger, deterministic seed chains, brand knowledge base, competitive pattern database, evaluator calibration, and checkpoint-resume. Without these, the pipeline has no state management, no reproducibility, no ground truth, and no resilience.

## Tickets (10)

### P0-01: Project Scaffolding
- Directory structure (generate/, evaluate/, iterate/, output/, data/, tests/)
- requirements.txt with pinned versions, config.yaml, .env.example, README.md
- **AC:** All dirs exist, pip install works, config loads

### P0-02: Append-Only Decision Ledger
- `iterate/ledger.py` — `log_event()`, `read_events()`, `read_events_filtered()`, `get_ad_lifecycle()`
- Auto-injected timestamp + checkpoint_id, fcntl file locking, schema validation
- **AC:** 8+ tests, append-only guarantees, JSONL valid

### P0-03: Per-Ad Seed Chain + Snapshots
- `generate/seeds.py` — `get_ad_seed(global_seed, brief_id, cycle_number)` → deterministic hash
- `iterate/snapshots.py` — `capture_snapshot()` for full API I/O capture
- **AC:** 10+ tests, same inputs → same seed always, snapshots JSON-serializable

### P0-04: Brand Knowledge Base
- `data/brand_knowledge.json` — verified facts only, every fact has a source citation
- Covers: brand identity, products, audiences, proof points, competitors, CTAs, compliance
- **AC:** 10 validation tests, no invented statistics/testimonials

### P0-05: Reference Ad Collection
- `data/reference_ads.json` — 40+ ads from Meta Ad Library
- `data/pattern_database.json` — structural atoms (hook type, body pattern, CTA style, tone)
- **AC:** Quality labels assigned, atoms decomposed

### P0-06: Evaluator Cold-Start Calibration
- `evaluate/evaluator.py` — `evaluate_ad()` with 5-step CoT prompt
- Calibrated against labeled reference ads: excellent avg ≥7.5, poor avg ≤5.0
- **AC:** 89.5% within ±1.0 of human labels

### P0-07: Golden Set Regression Tests
- `tests/test_data/golden_ads.json` — 18 ads with human-assigned scores (6 excellent, 6 good, 6 poor)
- `tests/test_evaluation/test_golden_set.py` — 6 regression tests
- **AC:** Evaluator accuracy stable across runs

### P0-08: Checkpoint-Resume Infrastructure
- `iterate/checkpoint.py` — `get_pipeline_state()`, `should_skip_ad()`
- `iterate/retry.py` — exponential backoff (2^n seconds, max 60s, 3 retries)
- **AC:** 10+ tests, no duplicated work on resume

### P0-09: Competitive Pattern Database — Initial Scan
- 42 real ads from Meta Ad Library (Varsity Tutors, Chegg, Wyzant, Kaplan)
- LLM-assisted labeling via Gemini Flash, `data/competitive/patterns.json` with 40 pattern records
- **AC:** Pattern records validate, competitor summaries written

### P0-10: Competitive Pattern Query Interface
- `generate/competitive.py` — `query_patterns()`, `get_competitor_summary()`, `get_landscape_context()`
- Filters by audience, campaign_goal, hook_type, competitor, tags
- **AC:** 12+ tests, ranked results, prompt-injectable context

## Dependency Graph

```
P0-01 (Scaffolding)
  │
  ├─→ P0-02 (Ledger)
  │     │
  │     ├─→ P0-03 (Seeds + Snapshots)
  │     └─→ P0-08 (Checkpoint-Resume)
  │
  ├─→ P0-04 (Brand KB)
  │     │
  │     └─→ P0-05 (Reference Ads)
  │           │
  │           ├─→ P0-06 (Calibration)
  │           │     │
  │           │     └─→ P0-07 (Golden Set)
  │           │
  │           └─→ P0-09 (Competitive Scan)
  │                 │
  │                 └─→ P0-10 (Query Interface)
```

## Key Decisions Made

1. **JSONL over SQLite** — grep/jq instant, immutable audit trail, no ORM overhead
2. **Identity-derived seeds over position-derived** — removing one brief doesn't cascade to others
3. **Evaluator-first** — calibrate before generating; if you can't measure quality, you can't improve it
4. **Real ads over synthetic** — P0-09 replaced P0-05's synthetic data with Meta Ad Library ads

## Status: ✅ COMPLETE (all 10 tickets, 84+ tests)
