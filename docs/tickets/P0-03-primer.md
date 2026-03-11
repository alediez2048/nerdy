# P0-03 Primer: Per-Ad Seed Chain + Snapshots

**For:** New Cursor Agent session  
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG  
**Date:** March 2026  
**Previous work:** P0-01 (scaffolding), P0-02 (decision ledger) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P0-03 implements **deterministic seed management** so that every ad generation is reproducible. Instead of a global seed that creates order-dependency, each ad gets its own seed derived from its identity: `seed = hash(global_seed + brief_id + cycle_number)`. This means if ad_005 fails and is skipped, ad_006's seed is unchanged.

Additionally, full input-output snapshots of every API call are stored in the decision ledger for forensic reproducibility.

### Why It Matters

- **Reproducibility** is an explicit assignment requirement ("deterministic behavior with seeds")
- Global seeds create cascading failures — one skipped ad shifts every subsequent seed
- Identity-based seeds let you replay any single ad without re-running the entire batch
- I/O snapshots guarantee bit-exact reproducibility even if the API changes behavior

---

## What Was Already Done

- P0-01: Project scaffolding — directory structure, config.yaml
- P0-02: Decision ledger — JSONL event logging with checkpoint_id
- Seed function pattern defined in `.cursor/rules/code-patterns.mdc`

---

## What This Ticket Must Accomplish

### Goal

Implement per-ad deterministic seed generation and API call snapshot utilities that integrate with the decision ledger.

### Deliverables Checklist

#### A. Seed Module (`generate/seeds.py`)

- [ ] `get_ad_seed(global_seed: str, brief_id: str, cycle_number: int) -> int`
  - Uses `hashlib.sha256` to derive a deterministic integer
  - Same inputs always produce the same seed
  - Different cycle_number for same brief produces different seed
  - Skipping an ad does NOT affect other ads' seeds
- [ ] `load_global_seed(config_path: str | None = None) -> str`
  - Reads from `GLOBAL_SEED` env var, falls back to config.yaml, falls back to default

#### B. Snapshot Utility (`iterate/snapshots.py` or similar)

- [ ] `capture_snapshot(prompt: str, response: str, model: str, parameters: dict, seed: int) -> dict`
  - Returns a structured snapshot dict ready to be embedded in ledger events
  - Includes: prompt (full text), response (full text), model_version, timestamp, all parameters, seed
- [ ] Snapshot dict is JSON-serializable
- [ ] Snapshots are stored as part of the ledger event's `inputs` and `outputs` fields

#### C. Tests (`tests/test_pipeline/test_seeds.py`)

- [ ] TDD first: write tests before implementation
- [ ] Test same inputs produce same seed (determinism)
- [ ] Test different cycle_number produces different seed
- [ ] Test different brief_id produces different seed
- [ ] Test seed is independent of other ads (no order-dependency)
- [ ] Test seed is a valid integer (not negative, reasonable range)
- [ ] Test snapshot capture produces JSON-serializable dict
- [ ] Test snapshot contains all required fields
- [ ] Minimum: 7+ tests

#### D. Documentation

- [ ] Add P0-03 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/P0-03-seed-chain-snapshots
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Per-ad seeds | R3-Q4 (Option B) | `seed = hash(global_seed + brief_id + cycle_number)` — identity-derived, not position-derived |
| Snapshots | R3-Q4 (Option C) | Full I/O snapshots for forensic reproducibility regardless of API behavior changes |

### Files to Create

| File | Why |
|------|-----|
| `generate/seeds.py` | Deterministic seed generation |
| Snapshot utility (location TBD) | API call snapshot capture |
| `tests/test_pipeline/test_seeds.py` | Seed + snapshot tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `.cursor/rules/code-patterns.mdc` | Seed function pattern |
| `interviews.md` (R3-Q4) | Full rationale for per-ad seeds + snapshots |
| P0-02 ledger module | Where snapshots get stored |

---

## Suggested Implementation Pattern

```python
import hashlib

def get_ad_seed(global_seed: str, brief_id: str, cycle_number: int) -> int:
    raw = f"{global_seed}:{brief_id}:{cycle_number}"
    return int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16)
```

---

## Definition of Done

- [ ] `get_ad_seed()` implemented — same inputs always produce same seed
- [ ] Snapshot utility captures full I/O for any API call
- [ ] Snapshots are JSON-serializable and integrate with the ledger schema
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 20–30 minutes

---

## After This Ticket: What Comes Next

- **P0-04** (Brand knowledge base) — uses seeds for reproducible brief expansion
- **P0-08** (Checkpoint-resume) — uses seeds + snapshots for exact replay
- Every generation call in P1+ uses `get_ad_seed()`
