# P4-02 Primer: Self-Healing Feedback Loop

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P0–P3 complete, P4-01 (agents) should be done first. See `docs/development/DEVLOG.md`.

---

## What Is This Ticket?

P4-02 wires together four concepts into a **self-healing feedback loop**: SPC drift detection → brief mutation → quality ratchet → exploration trigger. When quality drops, the system automatically detects, diagnoses, and corrects.

### Why It Matters

- **Pillar 4: The System Knows What It Doesn't Know** — SPC detects when the evaluator or generator is drifting
- **R1-Q1:** Statistical Process Control monitors score distributions for anomalies
- **R1-Q2:** Brief mutation adjusts generation strategy on failure
- **R1-Q9:** Quality ratchet prevents regression (rolling high-water mark)
- **Bonus:** +7 points for self-healing / automatic quality improvement

---

## What Was Already Done

- `data/config.yaml` — Quality ratchet params already defined: `ratchet_window: 5`, `ratchet_buffer: 0.5`
- `data/config.yaml` — Exploration params already defined: `exploration_plateau_threshold: 0.1`, `exploration_plateau_batches: 3`
- `iterate/ledger.py` — All events logged with scores, timestamps, cycle numbers
- `iterate/token_tracker.py` — `marginal_quality_gain()` tracks score deltas across regen cycles; `get_token_summary()` aggregates
- `evaluate/evaluator.py` — `EvaluationResult` with per-dimension scores (clarity, value_proposition, cta, brand_voice, emotional_resonance), `confidence_flags`, `weakest_dimension`, `meets_threshold`
- `generate/brief_expansion.py` — `expand_brief()` produces `ExpandedBrief` with `emotional_angles`, `value_propositions`, `constraints`
- `iterate/batch_processor.py` — `BatchResult` with per-batch stats, `write_batch_checkpoint()` logs `BatchCompleted` events

---

## What This Ticket Must Accomplish

### Goal

Build a self-healing loop that detects quality drops via SPC, diagnoses the root cause, mutates the brief, and re-generates — all automatically.

### Deliverables Checklist

#### A. SPC Drift Detection

Create `iterate/spc.py`:

- [ ] `SPCResult` dataclass — `in_control: bool`, `mean: float`, `ucl: float`, `lcl: float`, `violations: list[str]`
- [ ] `check_spc(scores: list[float], window: int) -> SPCResult` — Basic SPC with ±2σ control limits
- [ ] Detect: mean shift (3+ consecutive points above/below mean), trend (5+ monotonically increasing/decreasing), single point outside control limits
- [ ] `detect_quality_drift(ledger_path: str, window: int) -> SPCResult` — Read recent batch scores from ledger, run SPC

#### B. Brief Mutation

Create `iterate/brief_mutation.py`:

- [ ] `MutationStrategy` dataclass — `dimension: str`, `action: str`, `reason: str`
- [ ] `diagnose_weakness(eval_result: dict) -> MutationStrategy` — Identify weakest dimension and prescribe mutation
- [ ] `mutate_brief(brief: dict, strategy: MutationStrategy) -> dict` — Apply mutation: strengthen weak dimension's constraints in the brief
- [ ] Mutation types: `boost_emotional_angle`, `strengthen_cta`, `add_proof_point`, `clarify_value_prop`, `adjust_brand_voice`
- [ ] Log mutation event to ledger: `BriefMutated` with original + mutated diff

#### C. Quality Ratchet

Create `iterate/quality_ratchet.py`:

- [ ] `QualityRatchet` dataclass — `current_floor: float`, `rolling_avg: float`, `window_scores: list[float]`
- [ ] `compute_ratchet(ledger_path: str, window: int, buffer: float) -> QualityRatchet`
- [ ] Formula: `floor = max(7.0, rolling_window_avg - buffer)`
- [ ] Ratchet only goes up — never decreases below 7.0 (immutable floor from config)

#### D. Self-Healing Orchestrator

Create `iterate/self_healing.py`:

- [ ] `HealingAction` dataclass — `trigger: str`, `diagnosis: str`, `action_taken: str`, `outcome: str`
- [ ] `run_healing_check(ledger_path: str, config: dict) -> HealingAction | None`
- [ ] Flow: check SPC → if drift detected → diagnose weakest dimension → mutate brief → log outcome
- [ ] Log `SelfHealingTriggered` event to ledger with full diagnostic chain
- [ ] Returns `None` if system is in control (no healing needed)

### Files to Create/Modify

| File | Action |
|------|--------|
| `iterate/spc.py` | **Create** — SPC drift detection |
| `iterate/brief_mutation.py` | **Create** — Brief mutation engine |
| `iterate/quality_ratchet.py` | **Create** — Quality ratchet computation |
| `iterate/self_healing.py` | **Create** — Self-healing orchestrator |
| `tests/test_pipeline/test_self_healing.py` | **Create** — Tests for all components |

### Files to READ for Context

| File | Why |
|------|-----|
| `iterate/ledger.py` | Reading recent scores for SPC |
| `iterate/token_tracker.py` | Marginal gain tracking |
| `iterate/batch_processor.py` | BatchCompleted events for batch-level scoring |
| `evaluate/evaluator.py` | EvaluationResult structure for weakness diagnosis |
| `generate/brief_expansion.py` | ExpandedBrief structure for mutation |
| `data/config.yaml` | Ratchet + exploration params |

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| SPC for drift detection | R1-Q1 | Statistical process control, not ad-hoc thresholds |
| Brief mutation on failure | R1-Q2 | Adjust generation inputs, not just retry with same prompt |
| Quality ratchet | R1-Q9 | Rolling high-water mark — remembers best, refuses regression |
| Explore on plateau | R2-Q9 | Performance-decay triggers exploration (feeds P4-05) |

### Self-Healing Flow

```
check_spc(recent_batch_scores) → drift detected?
  → YES → diagnose_weakness(worst_eval) → mutate_brief(brief, strategy) → log SelfHealingTriggered
  → NO  → compute_ratchet() → update floor if rolling avg improved
```

---

## Definition of Done

- [ ] SPC detects simulated quality drop (inject low scores, verify detection)
- [ ] Brief mutation produces different brief based on weakness diagnosis
- [ ] Quality ratchet correctly computes floor from rolling window
- [ ] Self-healing orchestrator wires all components together
- [ ] Simulated drop → detected → diagnosed → action logged (end-to-end test)
- [ ] All events logged to ledger

---

## Estimated Time: 45–60 minutes
