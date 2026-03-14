# P1-11 Primer: Token Attribution Engine

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P0-02 (decision ledger), P0-08 (checkpoint-resume), P1-01 through P1-10 must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P1-11 implements the **token attribution engine** — the system that tags every API call with its purpose and computes cost-per-publishable-ad plus marginal quality gain per regeneration attempt. This is the "Performance Per Token" north star metric made concrete. Every token spent must be traceable to a pipeline stage (generation, evaluation, regeneration, distillation) so the system can answer: "Where is my budget going, and is it worth it?"

### Why It Matters

- **Every Token Is an Investment** (Pillar 3): Without attribution, you cannot optimize spend. The system must know which stages consume the most tokens and whether regeneration attempts yield diminishing returns.
- **Performance Per Token** is the project's north star metric — this ticket makes it measurable.
- Feeds the P5-05 Token Economics dashboard panel (cost attribution, cost-per-ad trend, marginal analysis).
- Enables P4-06 (Full marginal analysis engine) to cap low-return regeneration automatically.
- On Gemini's free tier, every wasted token is a wasted rate-limit slot.

---

## What Was Already Done

- **P0-02** (`iterate/ledger.py`): Append-only JSONL ledger with `log_event()`, `read_events()`, `get_ad_lifecycle()`. Every event already carries a `tokens_consumed` field.
- **P0-03** (`generate/seeds.py`): `get_ad_seed()`, `load_global_seed()` — deterministic identity for every ad.
- **P0-03** (`iterate/snapshots.py`): `capture_snapshot()` — state preservation.
- **P0-08** (`iterate/checkpoint.py`): `get_pipeline_state()`, `should_skip_ad()`, `get_last_checkpoint()` — pipeline state detection.
- **P0-08** (`iterate/retry.py`): `retry_with_backoff()` — exponential backoff on API failures.
- **P0-06** (`evaluate/evaluator.py`): `evaluate_ad()`, `EvaluationResult` dataclass — evaluation with scores.
- **P0-10** (`generate/competitive.py`): `load_patterns()`, `query_patterns()`, `get_landscape_context()` — competitive intelligence.
- **data/config.yaml**: All tunable parameters including `ledger_path`, `cache_path`, `batch_size: 10`.

---

## What This Ticket Must Accomplish

### Goal

Build a token tracking module that reads ledger events, categorizes token spend by pipeline stage, and computes the key cost metrics: cost-per-publishable-ad and marginal quality gain per regeneration attempt.

### Deliverables Checklist

#### A. Token Tracker Module (`iterate/token_tracker.py`)

- [ ] `TokenRecord` dataclass
  - Fields: `ad_id`, `stage` (generation | evaluation | regeneration | distillation), `model` (flash | pro), `tokens_input`, `tokens_output`, `tokens_total`, `timestamp`, `checkpoint_id`
- [ ] `get_stage_from_event(event: dict) -> str`
  - Maps ledger event types to pipeline stages:
    - `AdGenerated` / `BriefExpanded` → generation
    - `AdEvaluated` → evaluation
    - `AdRegenerated` → regeneration
    - `ContextDistilled` → distillation
  - Returns stage string; unknown event types → "other"
- [ ] `aggregate_by_stage(ledger_path: str) -> dict[str, int]`
  - Reads all ledger events via `read_events()`
  - Returns `{stage: total_tokens}` dictionary
  - This is the data behind "spend by stage" in the dashboard
- [ ] `aggregate_by_model(ledger_path: str) -> dict[str, int]`
  - Returns `{model_name: total_tokens}` — tracks Flash vs. Pro spend separately
- [ ] `cost_per_publishable_ad(ledger_path: str) -> float`
  - Total tokens consumed across all stages / count of ads reaching "published" terminal state
  - Returns tokens-per-published-ad (caller converts to dollars using model pricing)
  - Returns `float('inf')` if zero ads published (no division by zero)
- [ ] `marginal_quality_gain(ledger_path: str, ad_id: str) -> list[float]`
  - For a given ad, compute the quality delta between each regeneration attempt
  - Uses `get_ad_lifecycle()` to get ordered events for the ad
  - Returns list of score deltas: `[delta_after_regen_1, delta_after_regen_2, ...]`
  - Empty list if no regeneration occurred
- [ ] `get_token_summary(ledger_path: str) -> TokenSummary`
  - `TokenSummary` dataclass: `total_tokens`, `by_stage`, `by_model`, `cost_per_published`, `avg_marginal_gain`, `ads_published`, `ads_discarded`
  - Single call for dashboard consumption

#### B. Ledger Integration

- [ ] Token tracker reads from the ledger only — no separate storage. The ledger is the single source of truth (Pillar 5: State Is Sacred).
- [ ] Verify that existing pipeline stages log `tokens_consumed` and `model` fields in their ledger events. If any are missing, add them at the call site — do not retroactively patch the ledger.

#### C. Tests (`tests/test_pipeline/test_token_tracker.py`)

- [ ] TDD first
- [ ] Test `get_stage_from_event` maps all known event types correctly
- [ ] Test `get_stage_from_event` returns "other" for unknown types
- [ ] Test `aggregate_by_stage` sums tokens correctly across a mock ledger
- [ ] Test `aggregate_by_model` separates Flash vs. Pro spend
- [ ] Test `cost_per_publishable_ad` computes correct ratio
- [ ] Test `cost_per_publishable_ad` returns inf when zero ads published (no crash)
- [ ] Test `marginal_quality_gain` returns correct deltas for an ad with 2 regen cycles
- [ ] Test `marginal_quality_gain` returns empty list for a first-pass publish
- [ ] Test `get_token_summary` aggregates all metrics into a single summary
- [ ] Minimum: 9+ tests

#### D. Documentation

- [ ] Add P1-11 entry in `docs/DEVLOG.md`

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
| Full token attribution | R1-Q7 | Tag every API call with purpose. Marginal analysis: quality gain per regen attempt. Self-tuning cost envelope. |
| Token-aware routing | R1-Q4 | Tiered model routing — Flash default, Pro for 5.5-7.0 range. Attribution tracks cost per tier. |
| Token budget overrun | Risk Register | Mitigated by attribution (P1-11) + marginal analysis (P4-06) + caching (P1-12) + tiered routing. |

### Files to Create

| File | Why |
|------|-----|
| `iterate/token_tracker.py` | Token attribution and cost metrics |
| `tests/test_pipeline/test_token_tracker.py` | Token tracker tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `iterate/ledger.py` | How events are stored; `tokens_consumed` field structure; `get_ad_lifecycle()` |
| `evaluate/evaluator.py` | How evaluation results include scores (needed for marginal gain deltas) |
| `data/config.yaml` | `ledger_path` and other config values |
| `docs/reference/prd.md` (R1-Q7) | Full rationale for token attribution design |
| `docs/reference/prd.md` (Section 4.5) | Dashboard panels that consume token data |

---

## Definition of Done

- [ ] `aggregate_by_stage()` correctly categorizes all token spend from the ledger
- [ ] `aggregate_by_model()` separates Flash vs. Pro token spend
- [ ] `cost_per_publishable_ad()` computes tokens / published count
- [ ] `marginal_quality_gain()` shows score deltas across regen attempts for any ad
- [ ] `get_token_summary()` returns a complete summary for dashboard consumption
- [ ] No separate storage — reads only from the JSONL ledger
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Committed on `develop`

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

- **P1-12** (Result-level cache) — Avoid re-evaluating identical ads. Uses `cache_path` from config.yaml.
- **P1-13** (Batch-sequential processor) — Orchestrator that ties all P1 modules together into the main pipeline entry point.
- Token attribution data feeds **P4-06** (Full marginal analysis engine) and **P5-05** (Token Economics dashboard panel).
