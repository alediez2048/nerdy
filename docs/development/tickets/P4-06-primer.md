# P4-06 Primer: Full Marginal Analysis Engine

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P0–P3 complete. Token tracker exists. See `docs/development/DEVLOG.md`.

---

## What Is This Ticket?

P4-06 builds a **marginal analysis engine** that measures quality gain per regeneration attempt, per model, and per dimension. If the 3rd regen attempt rarely improves by >0.2 points, the system auto-caps at 2 attempts — a self-tuning cost envelope.

### Why It Matters

- **Pillar 3: Every Token Is an Investment** — Stop spending tokens when marginal return is negligible
- **R1-Q7:** Full Token Attribution + Marginal Analysis = Performance Per Token (the project's North Star metric)
- The 3rd regeneration attempt typically costs the same tokens but yields diminishing returns
- Auto-caps reduce waste without human tuning
- Dashboard Panel 6 (Token Economics) will consume this data in P5
- **Bonus:** +2 points for performance-per-token tracking (shared with P1-11)

---

## What Was Already Done

- `iterate/token_tracker.py` — Already has:
  - `marginal_quality_gain(ledger_path, ad_id) -> list[float]` — Score deltas between regen cycles for one ad
  - `aggregate_by_stage(ledger_path) -> dict[str, int]` — Token totals by pipeline stage
  - `aggregate_by_model(ledger_path) -> dict[str, int]` — Token totals by model
  - `cost_per_publishable_ad(ledger_path) -> float` — Tokens per published ad
  - `get_token_summary(ledger_path) -> TokenSummary` — Full aggregate
- `iterate/ledger.py` — All regen events logged with `cycle_number`, `scores`, `tokens_consumed`, `model_used`
- `data/config.yaml` — `max_regeneration_cycles: 3`
- `evaluate/cost_reporter.py` — `MODEL_COST_RATES` dict with per-model USD rates

---

## What This Ticket Must Accomplish

### Goal

Build a marginal analysis engine that computes quality-per-token at each regen attempt and auto-adjusts the regeneration budget.

### Deliverables Checklist

#### A. Marginal Analysis Core

Create `iterate/marginal_analysis.py`:

- [ ] `MarginalGain` dataclass — `cycle: int`, `score_before: float`, `score_after: float`, `gain: float`, `tokens_spent: int`, `gain_per_token: float`
- [ ] `RegenEfficiency` dataclass — `ad_id: str`, `gains: list[MarginalGain]`, `total_tokens: int`, `total_gain: float`, `diminishing_at: int | None` (cycle where gain drops below threshold)
- [ ] `compute_marginal_gains(ledger_path: str, ad_id: str) -> RegenEfficiency` — Extract regen cycle scores and tokens from ledger, compute per-cycle gain and gain-per-token

#### B. Aggregate Analysis

- [ ] `AggregateMarginals` dataclass — `avg_gain_by_cycle: dict[int, float]`, `avg_tokens_by_cycle: dict[int, int]`, `recommended_max_cycles: int`, `by_model: dict[str, dict]`, `by_dimension: dict[str, dict]`
- [ ] `compute_aggregate_marginals(ledger_path: str) -> AggregateMarginals` — Across ALL ads, compute average gain per cycle
- [ ] Break down by model (Flash vs Pro) and by dimension (which dimensions improve most on regen?)
- [ ] `recommended_max_cycles` = highest cycle where avg_gain > threshold (default 0.2)

#### C. Per-Dimension Analysis

- [ ] `DimensionMarginal` dataclass — `dimension: str`, `avg_gain_cycle_1: float`, `avg_gain_cycle_2: float`, `avg_gain_cycle_3: float`, `most_improved_by_regen: bool`
- [ ] `compute_dimension_marginals(ledger_path: str) -> list[DimensionMarginal]` — Which dimensions benefit most from regeneration?
- [ ] Insight example: "Brand Voice improves +1.2 on regen 1, but only +0.1 on regen 2"

#### D. Auto-Cap Logic

- [ ] `RegenBudget` dataclass — `max_cycles: int`, `reason: str`, `savings_estimate_tokens: int`
- [ ] `compute_regen_budget(aggregate: AggregateMarginals, min_gain: float) -> RegenBudget`
- [ ] Default `min_gain` threshold: 0.2 (configurable)
- [ ] If cycle N avg gain < min_gain → recommend max_cycles = N-1
- [ ] Estimate token savings: (ads_that_would_regen_Nx) * (avg_tokens_per_regen)

#### E. Dashboard Data

- [ ] `get_marginal_dashboard_data(ledger_path: str) -> dict` — Structured data for Panel 6 (Token Economics):
  - `gain_curve`: per-cycle average gain (line chart data)
  - `token_spend`: per-cycle average tokens (bar chart data)
  - `dimension_breakdown`: per-dimension gain at each cycle
  - `recommendation`: max_cycles + reasoning string

### Files to Create/Modify

| File | Action |
|------|--------|
| `iterate/marginal_analysis.py` | **Create** — Marginal analysis engine |
| `tests/test_pipeline/test_marginal_analysis.py` | **Create** — Tests |

### Files to READ for Context

| File | Why |
|------|-----|
| `iterate/token_tracker.py` | Existing `marginal_quality_gain()` — build on, don't duplicate |
| `iterate/ledger.py` | Source of regen cycle data |
| `evaluate/cost_reporter.py` | `MODEL_COST_RATES` for cost estimation |
| `data/config.yaml` | Current `max_regeneration_cycles` setting |

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Full token attribution | R1-Q7 | Every token traced to purpose + outcome |
| Marginal analysis | R1-Q7 | Quality gain per attempt — caps diminishing returns |
| Self-tuning cost envelope | R1-Q7 | System adjusts its own regen budget based on data |
| Performance Per Token | North Star | Quality per dollar of API spend |

### Expected Insight

From the PRD: "3rd regeneration attempt rarely improves by >0.2 points" — the marginal analysis should confirm this empirically and auto-cap.

```
Cycle 1 → 2: avg gain +0.8 (worth it)
Cycle 2 → 3: avg gain +0.3 (marginal)
Cycle 3 → 4: avg gain +0.1 (not worth it → cap at 3)
```

---

## Definition of Done

- [ ] Per-ad marginal gains computed from ledger
- [ ] Aggregate analysis across all ads, by model, by dimension
- [ ] Auto-cap recommends max_cycles based on min_gain threshold
- [ ] Token savings estimate calculated
- [ ] Dashboard data structured for Panel 6
- [ ] Tests verify: gain computation, aggregate rollup, auto-cap logic, edge cases (0 regens, 1 regen)

---

## Estimated Time: 40–50 minutes
