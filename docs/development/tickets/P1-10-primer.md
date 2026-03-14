# P1-10 Primer: Quality Ratchet

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P0-06 (evaluator calibration), P1-04 (CoT evaluator), P1-07 (Pareto selection), P1-13 (batch processor) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P1-10 implements the **quality ratchet** — a rolling threshold that only goes up, never down. The system remembers its best performance and refuses to regress. The formula:

```
effective_threshold = max(7.0, rolling_N_batch_avg - buffer)
```

Where `N` comes from `data/config.yaml` (`ratchet_window`, default 5) and the buffer from `ratchet_buffer` (default 0.5). The floor of 7.0 is the absolute minimum — the ratchet can only raise the bar above it.

Example: if the last 5 batches averaged 8.2, the effective threshold becomes max(7.0, 8.2 - 0.5) = 7.7. The system now rejects ads that would have passed at 7.0. If the next batch averages 7.5, the rolling average drops but the threshold was already set — it only ratchets up.

### Why It Matters

- **Learning Is Structural** (Pillar 6): The ratchet encodes the system's progress into a hard constraint. Quality gains are permanent, not accidental.
- **Self-healing / automatic quality improvement** earns +7 bonus points — the ratchet is the mechanism that makes improvement irreversible.
- A fixed 7.0 threshold lets the system coast. A ratchet forces continuous improvement: publish quality this batch must be at least as good as recent history.
- The monotonic threshold is a key visualization for the rubric's "quality trend" requirement (+2 bonus points).

---

## What Was Already Done

These modules exist and are tested — do NOT recreate them:

| Module | What It Provides |
|--------|-----------------|
| `iterate/ledger.py` | `log_event()` for ratchet updates; `read_events()` for batch history |
| `iterate/checkpoint.py` | `get_pipeline_state()` — tracks batch boundaries |
| `evaluate/evaluator.py` | `evaluate_ad()` returns `EvaluationResult` with weighted average scores |
| `data/config.yaml` | `ratchet_window` (default 5), `ratchet_buffer` (default 0.5), base threshold 7.0 |
| `data/reference_ads.json` | 42 reference ads with baseline scores for initial calibration |

---

## What This Ticket Must Accomplish

### Goal

Build the quality ratchet that computes a rolling, monotonically-increasing publish threshold from batch history, enforces it on every ad, and logs threshold changes for visualization.

### Deliverables Checklist

#### A. Quality Ratchet Module (`iterate/quality_ratchet.py`)

- [ ] `RatchetState` dataclass:
  - `current_threshold: float` — the effective publish threshold right now
  - `base_threshold: float` — the absolute floor (7.0)
  - `rolling_average: float` — the rolling N-batch average
  - `window_scores: list[float]` — the batch averages in the current window
  - `history: list[dict]` — all threshold changes over time (for plotting)
- [ ] `compute_threshold(batch_averages: list[float], config: dict) -> float`
  - Computes `max(base_threshold, rolling_window_avg - buffer)`
  - Uses `ratchet_window` and `ratchet_buffer` from config
  - If fewer batches than window size, uses all available batches
  - Returns `base_threshold` if no batches exist yet (cold start)
- [ ] `update_ratchet(state: RatchetState, new_batch_avg: float, config: dict) -> RatchetState`
  - Appends new batch average to window
  - Trims window to `ratchet_window` size (FIFO)
  - Computes new threshold via `compute_threshold`
  - **Monotonic enforcement:** new threshold = max(old threshold, computed threshold)
  - Logs `RatchetUpdated` event to ledger with old threshold, new threshold, batch average
  - Returns updated state
- [ ] `meets_threshold(score: float, state: RatchetState) -> bool`
  - Returns True if score >= current_threshold
- [ ] `get_ratchet_state(ledger_path: str, config: dict) -> RatchetState`
  - Reconstructs ratchet state from ledger history
  - Reads all batch completion events, extracts averages, replays threshold computation
  - Used on pipeline resume to restore the ratchet to its correct position
- [ ] `get_ratchet_history(state: RatchetState) -> list[dict]`
  - Returns time-series data for visualization: batch_index, batch_avg, threshold
  - Suitable for plotting a monotonic bar chart

#### B. Tests (`tests/test_pipeline/test_quality_ratchet.py`)

- [ ] TDD first
- [ ] Test `compute_threshold` with no batches returns base threshold (7.0)
- [ ] Test `compute_threshold` with batches below window size uses all available
- [ ] Test `compute_threshold` returns max(7.0, avg - buffer) correctly
- [ ] Test `update_ratchet` monotonic enforcement: threshold never decreases
- [ ] Test `update_ratchet` with declining batch averages keeps threshold at peak
- [ ] Test `update_ratchet` with improving batch averages ratchets threshold up
- [ ] Test `meets_threshold` correctly compares against current threshold
- [ ] Test window trimming keeps only last N batches
- [ ] Test `get_ratchet_state` reconstructs from ledger correctly
- [ ] Test ratchet history produces plottable time-series data
- [ ] Minimum: 8+ tests

#### C. Documentation

- [ ] Add P1-10 entry in `docs/DEVLOG.md`

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
| Rolling high-water mark | R1-Q9 | Effective threshold = max(7.0, rolling_5batch_avg - 0.5). True ratchet: remembers best performance, refuses regression. 0.5 buffer prevents over-aggressiveness. |
| State is sacred | Pillar 5 | Ratchet state is reconstructable from ledger. Pipeline resume restores exact threshold. |
| Visible reasoning | Pillar 7 | Threshold history is a first-class visualization output for the demo. |

### Monotonic Enforcement — The Key Invariant

The ratchet MUST be monotonically non-decreasing. This means:

```python
new_threshold = max(current_state.current_threshold, computed_threshold)
```

Even if the rolling average drops (bad batch), the threshold stays at its peak. The system never lowers its standards. This is the "ratchet" behavior — like a mechanical ratchet that only turns one direction.

### Files to Create

| File | Why |
|------|-----|
| `iterate/quality_ratchet.py` | Threshold computation, monotonic enforcement, state management |
| `tests/test_pipeline/test_quality_ratchet.py` | Ratchet + monotonicity tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `iterate/ledger.py` | How to log ratchet update events and read batch history |
| `data/config.yaml` | `ratchet_window`, `ratchet_buffer`, base threshold |
| `evaluate/evaluator.py` | Weighted average scores that feed into batch averages |
| `docs/reference/prd.md` (R1-Q9) | Full rationale for rolling high-water mark |

---

## Definition of Done

- [ ] `compute_threshold()` correctly applies `max(7.0, rolling_avg - buffer)` formula
- [ ] `update_ratchet()` enforces monotonic non-decreasing threshold
- [ ] Threshold never decreases even when batch averages decline
- [ ] Cold start (no batches) returns base threshold of 7.0
- [ ] `get_ratchet_state()` reconstructs correct state from ledger on resume
- [ ] `get_ratchet_history()` produces plottable monotonic time-series
- [ ] All config values (`ratchet_window`, `ratchet_buffer`) read from config — no hardcoded numbers
- [ ] `RatchetUpdated` events logged to ledger
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Committed on `develop`

---

## Estimated Time: 30-45 minutes

---

## After This Ticket: What Comes Next

**Next P1 tickets:**
- **P1-11** (Token attribution engine) — Tracks cost-per-publishable-ad using the ratcheted threshold
- **P1-14** (50+ ad batch run) — The ratchet is active during the full production run, proving quality improves over time

**P2 tickets that depend on the ratchet:**
- **P2-04** (SPC monitoring) — Statistical process control uses ratchet history as baseline
- **P5-03** (Quality trend visualization) — Plots the monotonic threshold bar chart for the demo

The quality ratchet is the system's long-term memory of quality standards. It transforms the pipeline from "generate ads that meet 7.0" to "generate ads that meet the best we have ever done." This is the mechanism behind the +7 self-healing bonus and the +2 visualization bonus.
