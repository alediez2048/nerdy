# P2-04 Primer: SPC Drift Detection

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P1-10 (quality ratchet), P1-20 (50+ ad run with evaluation data), P0-07 (golden set) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P2-04 implements **Statistical Process Control (SPC)** for evaluator drift detection. Track evaluator score distributions across batches using control charts with ±2σ limits. When a batch breaches the limits, inject **canary ads** (known-score reference ads from the golden set) to diagnose whether the drift is real quality change or evaluator instability.

### Why It Matters

- **The System Knows What It Doesn't Know** (Pillar 4): If the evaluator silently drifts, the 7.0 threshold becomes meaningless
- R1-Q1 selected SPC as the best drift detection approach — cheapest signal with most targeted intervention
- Risk Register: "Evaluator drift over long runs" is Medium Impact, Low-Medium Probability
- The quality ratchet (P1-10) depends on stable scoring — drift corrupts the rolling average
- SPC catches gradual drift that individual batch checks would miss

---

## What Was Already Done

- P1-10: Quality ratchet tracks rolling 5-batch averages and computes thresholds
- P1-20: 50+ ads evaluated across multiple batches — provides baseline distribution data
- P0-07: Golden set of 18 human-scored ads — serves as canary source
- P1-04: CoT evaluator with confidence flags (low confidence may correlate with drift)
- P1-13: Batch processor with checkpoint events marking batch boundaries

---

## What This Ticket Must Accomplish

### Goal

Build SPC monitoring that computes control limits from evaluation data, detects out-of-control batches, and triggers canary injection to diagnose the cause.

### Deliverables Checklist

#### A. SPC Monitor (`evaluate/spc_monitor.py`)

- [ ] `ControlLimits` dataclass: `mean`, `ucl` (upper control limit), `lcl` (lower control limit), `sigma`
- [ ] `compute_control_limits(batch_averages: list[float], sigma_multiplier: float = 2.0) -> ControlLimits`
  - Uses rolling 5-batch mean and standard deviation
  - UCL = mean + 2σ, LCL = mean - 2σ
  - Requires minimum 5 data points to establish limits
- [ ] `is_in_control(batch_avg: float, limits: ControlLimits) -> bool`
  - Returns True if LCL ≤ batch_avg ≤ UCL
- [ ] `detect_drift(ledger_path: str) -> DriftReport`
  - Reads BatchCompleted events from ledger
  - Extracts per-batch average scores
  - Computes control limits from first N batches (baseline)
  - Checks each subsequent batch against limits
  - Returns list of out-of-control batches with direction (high/low)
- [ ] `get_control_chart_data(ledger_path: str) -> ControlChartData`
  - Returns batch averages, UCL, LCL, mean line, and breach points
  - Dashboard-ready format for P5-05 visualization

#### B. Canary Injection (`evaluate/spc_monitor.py`)

- [ ] `inject_canary(golden_ads_path: str, count: int = 3) -> list[dict]`
  - Selects `count` reference ads from golden set (1 excellent, 1 good, 1 poor)
  - Returns them formatted for `evaluate_ad()` input
- [ ] `diagnose_drift(canary_results: list, golden_ads: list) -> DriftDiagnosis`
  - Compares canary evaluation scores against known human scores
  - If canary scores match humans (±1.0): drift is real quality change → no action
  - If canary scores diverge from humans: evaluator drift → flag for recalibration
  - Returns: `is_evaluator_drift: bool`, `affected_dimensions: list`, `recommendation: str`

#### C. Tests (`tests/test_pipeline/test_spc_monitor.py`)

- [ ] `test_control_limits_calculation`: Known data → correct mean, UCL, LCL
- [ ] `test_in_control_within_limits`: Score between UCL and LCL → True
- [ ] `test_out_of_control_above_ucl`: Score above UCL → False
- [ ] `test_out_of_control_below_lcl`: Score below LCL → False
- [ ] `test_drift_report_stable_data`: All batches within limits → no breaches
- [ ] `test_drift_report_detects_shift`: Inject a batch 3σ above mean → detected
- [ ] `test_canary_injection_selects_diverse`: Returns 1 excellent, 1 good, 1 poor
- [ ] `test_diagnose_drift_evaluator_stable`: Canary matches humans → not evaluator drift
- [ ] `test_diagnose_drift_evaluator_shifted`: Canary diverges → evaluator drift detected
- [ ] `test_insufficient_data_returns_no_limits`: < 5 batches → no control limits computed
- [ ] Minimum: 10+ tests

#### D. Documentation

- [ ] Add P2-04 entry in `docs/DEVLOG.md`

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| SPC monitoring | R1-Q1 (Option B) | Continuous monitoring with minimal overhead; cheapest signal |
| Canary injection | R1-Q1 | Only fires when SPC flags an issue; diagnoses drift vs. real change |
| ±2σ limits | R1-Q1 | Standard SPC practice; tighter than ±3σ for early warning |
| Golden set as canaries | P0-07 | 18 human-scored ads serve double duty as calibration and canary |

### SPC Basics

```
UCL (Upper Control Limit) = μ + 2σ
Mean = μ (rolling 5-batch average)
LCL (Lower Control Limit) = μ - 2σ

Batch average outside [LCL, UCL] = out of control → investigate
```

### Integration Points

- `iterate/quality_ratchet.py`: `get_ratchet_history()` provides batch averages for SPC
- `iterate/ledger.py`: `read_events_filtered(event_type="BatchCompleted")` for batch data
- `tests/test_data/golden_ads.json`: Canary source with human scores

### Files to Create

| File | Why |
|------|-----|
| `evaluate/spc_monitor.py` | SPC monitoring + canary injection |
| `tests/test_pipeline/test_spc_monitor.py` | SPC tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `iterate/quality_ratchet.py` | `get_ratchet_history()` for batch averages |
| `iterate/ledger.py` | Ledger read functions |
| `tests/test_data/golden_ads.json` | Canary source data |
| `evaluate/evaluator.py` | `evaluate_ad()` for canary re-evaluation |

---

## Definition of Done

- [ ] Control limits computed from batch averages (±2σ)
- [ ] Out-of-control batches detected correctly
- [ ] Canary injection selects diverse ads from golden set
- [ ] Drift diagnosis distinguishes evaluator drift from real quality change
- [ ] Control chart data format ready for dashboard (P5-05)
- [ ] 10+ tests passing
- [ ] Lint clean
- [ ] DEVLOG updated

---

## After This Ticket: What Comes Next

**P2-05 (Confidence-Gated Autonomy)** uses the evaluator's self-rated confidence to route ads: high confidence → autonomous, medium → flagged, low → human required. While SPC monitors the evaluator's reliability over time, confidence gating monitors reliability per-ad.
