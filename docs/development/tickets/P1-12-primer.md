# P1-12 Primer: Result-Level Cache

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P0-02 (decision ledger), P0-06 (evaluator calibration), P0-08 (checkpoint-resume), P1-04 (chain-of-thought evaluator) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P1-12 implements **result-level caching** for evaluation scores. The cache key is `hash(ad_text + evaluator_prompt_version)`, so identical ad text evaluated by the same prompt version returns instantly from cache instead of burning an API call. When the evaluator prompt is recalibrated (version changes), all cached scores are automatically invalidated — version-based TTL, not time-based.

### Why It Matters

- **Every Token Is an Investment** (Pillar 3): Re-evaluating identical text with an unchanged prompt is pure waste. On Gemini's free tier (15 RPM Flash, 2 RPM Pro), a cache hit saves a rate-limit slot.
- **State Is Sacred** (Pillar 5): Pipeline resume via checkpoint-resume (P0-08) will re-encounter previously evaluated ads. Without caching, resume means re-spending tokens on already-known results.
- Directly mitigates the "Token budget overrun" risk (Risk Register) alongside P1-11 (attribution) and tiered routing.
- Cache invalidation on recalibration ensures scores never go stale after prompt changes — correctness over speed.

---

## What Was Already Done

- **P0-02** (`iterate/ledger.py`): Append-only JSONL ledger with `log_event()`, `read_events()`, `get_ad_lifecycle()`.
- **P0-03** (`generate/seeds.py`): `get_ad_seed()`, `load_global_seed()` — deterministic identity for every ad.
- **P0-06** (`evaluate/evaluator.py`): `evaluate_ad()`, `EvaluationResult` dataclass — the function whose results get cached.
- **P0-08** (`iterate/checkpoint.py`): `get_pipeline_state()`, `should_skip_ad()`, `get_last_checkpoint()` — resume logic that benefits from cache hits.
- **P0-08** (`iterate/retry.py`): `retry_with_backoff()` — retry on API errors (cache hits skip this entirely).
- **P0-10** (`generate/competitive.py`): `load_patterns()`, `query_patterns()`, `get_landscape_context()`.
- **data/config.yaml**: Contains `cache_path` (where cache file lives) and `ledger_path`.

---

## What This Ticket Must Accomplish

### Goal

Build a result-level cache that stores evaluation results keyed by content hash + prompt version, supports instant lookups on pipeline resume, and invalidates cleanly when the evaluator prompt changes.

### Deliverables Checklist

#### A. Cache Module (`iterate/cache.py`)

- [ ] `CacheEntry` dataclass
  - Fields: `cache_key` (str), `ad_text_hash` (str), `prompt_version` (str), `result` (EvaluationResult), `created_at` (ISO timestamp)
- [ ] `compute_cache_key(ad_text: str, prompt_version: str) -> str`
  - Returns `sha256(ad_text + prompt_version)` hex digest
  - Deterministic: same inputs always produce same key
- [ ] `get_cached_result(cache_path: str, ad_text: str, prompt_version: str) -> EvaluationResult | None`
  - Looks up the cache by computed key
  - Returns `None` on miss (not an error — misses are expected)
  - Returns the stored `EvaluationResult` on hit
- [ ] `store_result(cache_path: str, ad_text: str, prompt_version: str, result: EvaluationResult) -> None`
  - Writes the result to cache keyed by `compute_cache_key()`
  - Appends to the cache file (JSONL format, consistent with ledger pattern)
- [ ] `invalidate_cache(cache_path: str) -> int`
  - Deletes or truncates the entire cache file
  - Returns the number of entries cleared (for logging)
  - Called when evaluator prompt version changes (recalibration event)
- [ ] `get_cache_stats(cache_path: str) -> dict`
  - Returns `{"total_entries": int, "prompt_versions": list[str], "oldest_entry": str, "newest_entry": str}`
  - Useful for debugging and dashboard

#### B. Cache Storage Format

- [ ] JSONL file at `cache_path` from config.yaml (consistent with ledger's append-only pattern)
- [ ] Each line: `{"cache_key": "...", "ad_text_hash": "...", "prompt_version": "...", "result": {...}, "created_at": "..."}`
- [ ] On lookup, scan for matching key (last match wins if duplicates exist — append-only means newer entries override)
- [ ] For performance at scale: consider loading into a dict on first access, then serving from memory. Reload on cache miss to catch concurrent writes.

#### C. Evaluator Integration

- [ ] Wrap `evaluate_ad()` with cache-aware logic:
  - Before calling the API: check cache via `get_cached_result()`
  - On cache hit: return cached result, log a `CacheHit` event to ledger (zero tokens consumed)
  - On cache miss: call `evaluate_ad()`, store result via `store_result()`, log `CacheMiss` event
- [ ] Track cache hit/miss ratio in ledger events for token attribution (P1-11)

#### D. Recalibration Hook

- [ ] When evaluator prompt version changes (detected by comparing current version to cached versions), call `invalidate_cache()`
- [ ] Log a `CacheInvalidated` event to the ledger with the old version and new version
- [ ] This ensures no stale scores survive a recalibration

#### E. Tests (`tests/test_pipeline/test_cache.py`)

- [ ] TDD first
- [ ] Test `compute_cache_key` is deterministic (same inputs = same key)
- [ ] Test `compute_cache_key` differs when ad_text changes
- [ ] Test `compute_cache_key` differs when prompt_version changes
- [ ] Test `store_result` then `get_cached_result` returns the stored result (round-trip)
- [ ] Test `get_cached_result` returns None on cache miss
- [ ] Test `invalidate_cache` clears all entries; subsequent lookup returns None
- [ ] Test `invalidate_cache` returns correct count of cleared entries
- [ ] Test cache hit with wrong prompt_version returns None (version mismatch)
- [ ] Test `get_cache_stats` returns correct counts
- [ ] Test empty cache file does not crash any function
- [ ] Minimum: 10+ tests

#### F. Documentation

- [ ] Add P1-12 entry in `docs/DEVLOG.md`

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
| Result-level caching | R3-Q7 | Cache keyed by hash(ad_text + evaluator_prompt_version). Recalibration invalidates all cached scores. Version-based TTL, not time-based. |
| Append-only storage | R2-Q8 | Cache follows the same JSONL append-only pattern as the ledger. No in-place mutations. |
| Checkpoint-resume | R3-Q2 | Cache hits on resume prevent re-spending tokens. Cache + checkpoints = zero wasted work. |

### Files to Create

| File | Why |
|------|-----|
| `iterate/cache.py` | Result-level cache with version-based invalidation |
| `tests/test_pipeline/test_cache.py` | Cache tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `evaluate/evaluator.py` | The function whose results get cached; `EvaluationResult` dataclass structure |
| `iterate/ledger.py` | JSONL append-only pattern to follow; event logging for cache hits/misses |
| `data/config.yaml` | `cache_path` — where the cache file lives |
| `iterate/checkpoint.py` | Resume logic that benefits from cache hits |
| `docs/reference/prd.md` (R3-Q7) | Full rationale for result-level caching design |

---

## Definition of Done

- [ ] `compute_cache_key()` produces deterministic, version-aware keys
- [ ] `get_cached_result()` returns hits; returns None on misses
- [ ] `store_result()` persists results in JSONL format
- [ ] `invalidate_cache()` clears all entries on recalibration
- [ ] Cache integrates with `evaluate_ad()` — hits skip the API call entirely
- [ ] Cache hit/miss events logged to the ledger (feeds P1-11 token attribution)
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Committed on `develop`

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

- **P1-13** (Batch-sequential processor) — Orchestrator that integrates all P1 modules (including this cache) into the main pipeline entry point.
- Cache hit/miss data feeds **P1-11** (Token attribution engine) for cost analysis.
- Cache invalidation is triggered by **P2-04** (SPC drift detection) when evaluator recalibration occurs.
