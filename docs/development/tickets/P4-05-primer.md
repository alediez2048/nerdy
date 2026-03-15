# P4-05 Primer: Performance-Decay Exploration Trigger

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P0–P3 complete, P4-02 (self-healing) should be done first. See `docs/development/DEVLOG.md`.

---

## What Is This Ticket?

P4-05 implements **exploit-by-default, explore-on-plateau** logic. The system exploits proven patterns until quality plateaus (<0.1 improvement over 3 batches), then automatically triggers exploration of new approaches. Successful explorations are promoted to the proven library.

### Why It Matters

- **R2-Q9:** Performance-Decay-Triggered Exploration — explores only when exploitation is provably exhausted
- Prevents creative stagnation without wasting tokens on unnecessary exploration
- Successful patterns promoted to proven library feed future campaigns (connects to P4-04 cross-campaign transfer)
- Token-efficient: explore only when needed

---

## What Was Already Done

- `data/config.yaml` — Already has: `exploration_plateau_threshold: 0.1`, `exploration_plateau_batches: 3`
- `iterate/token_tracker.py` — `marginal_quality_gain()` tracks score deltas across regen cycles
- `iterate/ledger.py` — All batch scores logged; `BatchCompleted` events contain per-batch stats
- `iterate/batch_processor.py` — `write_batch_checkpoint()` logs batch-level results
- `generate/ab_variants.py` — `VARIANT_ELEMENTS` (hook_type, emotional_angle, cta_style) + `generate_copy_variants()` for exploration
- `generate/style_library.py` — `STYLE_PRESETS` (5 presets), `get_styles_for_audience()` for style exploration
- `generate/competitive.py` — `query_patterns()` for discovering untested hook types from competitors

---

## What This Ticket Must Accomplish

### Goal

Build an explore-exploit engine that detects quality plateaus and automatically switches to exploration mode, promoting successful experiments.

### Deliverables Checklist

#### A. Plateau Detection

Create `iterate/explore_exploit.py`:

- [ ] `PlateauStatus` dataclass — `is_plateau: bool`, `batches_flat: int`, `rolling_avg: float`, `improvement: float`
- [ ] `detect_plateau(ledger_path: str, threshold: float, min_batches: int) -> PlateauStatus`
- [ ] Read `BatchCompleted` events from ledger, extract batch average scores
- [ ] Plateau = improvement < threshold for min_batches consecutive batches

#### B. Exploration Strategy

- [ ] `ExplorationStrategy` dataclass — `strategy_type: str`, `parameters: dict`, `reason: str`
- [ ] `select_exploration_strategy(plateau: PlateauStatus, current_patterns: list) -> ExplorationStrategy`
- [ ] Strategy types:
  - `new_hook_type` — Try hook types not in the current top-3 (from competitive patterns)
  - `new_emotional_angle` — Switch emotional angle (e.g., aspiration → urgency)
  - `new_style_preset` — Try untested style from `STYLE_PRESETS`
  - `cross_audience` — Apply a pattern that works for one audience to another
- [ ] Strategy selection: prioritize untested combinations first, then low-sample-size patterns

#### C. Exploration Execution

- [ ] `ExplorationResult` dataclass — `strategy: ExplorationStrategy`, `score: float`, `baseline_score: float`, `improvement: float`, `promoted: bool`
- [ ] `run_exploration(strategy: ExplorationStrategy, brief: dict, config: dict) -> ExplorationResult`
- [ ] Generate ad with exploration strategy applied → evaluate → compare to baseline
- [ ] Log `ExplorationTriggered` and `ExplorationCompleted` events to ledger

#### D. Pattern Promotion

- [ ] `promote_pattern(result: ExplorationResult, pattern_library_path: str) -> bool` — If score > baseline + threshold, add pattern to proven library
- [ ] Promoted patterns get `campaign_scope: "universal"` tag (connects to P4-04)
- [ ] Log `PatternPromoted` event to ledger

#### E. Explore-Exploit Orchestrator

- [ ] `check_and_explore(ledger_path: str, config: dict) -> ExplorationResult | None` — Full flow: detect plateau → select strategy → execute → promote if successful
- [ ] Returns `None` if no plateau detected (exploit mode continues)

### Files to Create/Modify

| File | Action |
|------|--------|
| `iterate/explore_exploit.py` | **Create** — Full explore-exploit engine |
| `tests/test_pipeline/test_explore_exploit.py` | **Create** — Tests |

### Files to READ for Context

| File | Why |
|------|-----|
| `data/config.yaml` | Plateau threshold + batch count params |
| `iterate/token_tracker.py` | Marginal gain computation |
| `iterate/ledger.py` | Reading BatchCompleted events |
| `iterate/batch_processor.py` | Batch checkpoint format |
| `generate/ab_variants.py` | VARIANT_ELEMENTS for copy exploration |
| `generate/style_library.py` | STYLE_PRESETS for style exploration |
| `generate/competitive.py` | query_patterns for hook type discovery |

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Exploit by default | R2-Q9 | Don't waste tokens exploring when exploitation works |
| Plateau = <0.1 over 3 batches | R2-Q9, config.yaml | Conservative trigger — explore only when stuck |
| Promote on success | R2-Q9 | Successful explorations become proven patterns |
| Token-efficient | Pillar 3 | Exploration budget capped |

### Explore-Exploit Flow

```
After each batch:
  detect_plateau(ledger) → plateau?
    → NO:  continue exploit (use proven patterns)
    → YES: select_exploration_strategy()
           → run_exploration()
           → score > baseline + threshold?
              → YES: promote_pattern() → return to exploit with new pattern
              → NO:  log failure → try different strategy next batch
```

---

## Definition of Done

- [ ] Plateau detection correctly identifies <0.1 improvement over 3+ batches
- [ ] Exploration strategy selects untested approaches
- [ ] Successful exploration promotes pattern to library
- [ ] Failed exploration logged but does not pollute proven patterns
- [ ] Orchestrator wires detect → explore → promote flow
- [ ] Tests verify: plateau detection, strategy selection, promotion threshold

---

## Estimated Time: 45–60 minutes
