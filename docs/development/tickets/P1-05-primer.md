# P1-05 Primer: Campaign-Goal-Adaptive Weighting

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P0-06 (evaluator calibration) must be complete. P1-04 (CoT evaluator) should be complete — it produces the per-dimension scores this ticket weights. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P1-05 implements **campaign-goal-adaptive dimension weighting** with hard floor constraints. Instead of weighting all 5 quality dimensions equally, the system applies different weight profiles based on the campaign goal. An awareness campaign values Emotional Resonance and Brand Voice more heavily (you want people to feel something and remember the brand). A conversion campaign values Call to Action and Value Proposition more heavily (you want people to click and buy). Regardless of weights, Clarity must score >= 6.0 and Brand Voice must score >= 5.0 — violations trigger automatic rejection.

### Why It Matters

- **Decomposition Is the Architecture** (Pillar 1): Equal weighting treats confusing ads with great resonance the same as clear, emotionless ads. Goal-adaptive weights make the system goal-aware.
- Floor constraints are a structural guarantee: no ad with a confusing message (Clarity < 6.0) or off-brand voice (Brand Voice < 5.0) ever gets published, regardless of how high other dimensions score.
- The weighting strategy is defined in the PRD (Section 5.2) with exact weight tables. This is not a design decision — it is a specification to implement.
- This module sits between the evaluator (P1-04) and the publish/reject decision. It transforms raw dimension scores into a weighted average and a pass/reject determination.

---

## What Was Already Done

- P0-06: Evaluator calibration (`evaluate/evaluator.py`) — `evaluate_ad()` produces `EvaluationResult` with per-dimension scores
- P1-04: CoT evaluator extends this with contrastive rationales and confidence flags
- P0-02: Decision ledger (`iterate/ledger.py`) — `log_event()` for tracking weighting and rejection events
- P0-01: Config (`data/config.yaml`) — contains evaluation parameters and thresholds

---

## What This Ticket Must Accomplish

### Goal

Build the dimension weighting module that applies campaign-goal-specific weight profiles to per-dimension scores, enforces hard floor constraints, and produces a weighted average with a pass/reject determination.

### Deliverables Checklist

#### A. Dimensions Module (`evaluate/dimensions.py`)

- [ ] `WeightProfile` dataclass:
  - `campaign_goal`: str (awareness/conversion)
  - `weights`: dict mapping dimension name to weight (float, must sum to 1.0)
  - `floors`: dict mapping dimension name to minimum score (only Clarity and Brand Voice have floors)
- [ ] `AWARENESS_WEIGHTS` constant — the awareness weight profile from PRD Section 5.2:
  - Clarity: 0.25
  - Value Proposition: 0.20
  - Call to Action: 0.10
  - Brand Voice: 0.20
  - Emotional Resonance: 0.25
- [ ] `CONVERSION_WEIGHTS` constant — the conversion weight profile from PRD Section 5.2:
  - Clarity: 0.25
  - Value Proposition: 0.25
  - Call to Action: 0.30
  - Brand Voice: 0.10
  - Emotional Resonance: 0.10
- [ ] `FLOOR_CONSTRAINTS` constant:
  - Clarity: 6.0 (hard minimum)
  - Brand Voice: 5.0 (hard minimum)
- [ ] `get_weight_profile(campaign_goal: str) -> WeightProfile`
  - Returns the appropriate weight profile for the campaign goal
  - Defaults to awareness weights for unknown campaign goals (with logged warning)
- [ ] `compute_weighted_score(scores: dict[str, float], profile: WeightProfile) -> float`
  - Applies weights to per-dimension scores
  - Returns weighted average (float, 1-10 range)
  - Validates that all 5 dimensions are present in scores
- [ ] `check_floor_violations(scores: dict[str, float]) -> list[FloorViolation]`
  - Checks each dimension against its floor constraint
  - Returns list of `FloorViolation` objects (empty list = no violations)
- [ ] `FloorViolation` dataclass:
  - `dimension`: str
  - `score`: float (the actual score)
  - `floor`: float (the minimum required)
  - `deficit`: float (floor - score)
- [ ] `evaluate_with_weights(scores: dict[str, float], campaign_goal: str) -> WeightedResult`
  - Convenience function that combines weighting + floor checking
  - Returns `WeightedResult` with weighted_average, floor_violations, and pass/reject decision
- [ ] `WeightedResult` dataclass:
  - `weighted_average`: float
  - `campaign_goal`: str
  - `weight_profile`: WeightProfile used
  - `floor_violations`: list[FloorViolation]
  - `passes_threshold`: bool — True if weighted_average >= 7.0 AND no floor violations
  - `rejection_reasons`: list[str] — human-readable reasons for rejection (if any)

#### B. Extend Evaluator (`evaluate/evaluator.py`)

- [ ] Update `evaluate_ad()` or add a wrapper that accepts `campaign_goal` and applies weighting
- [ ] `EvaluationResult` should include or be paired with `WeightedResult`
- [ ] Floor violations logged as rejection events to the decision ledger
- [ ] Maintain backward compatibility with P0-06 and P1-04 tests

#### C. Tests (`tests/test_evaluation/test_dimensions.py`)

- [ ] TDD first
- [ ] Test awareness weights sum to 1.0
- [ ] Test conversion weights sum to 1.0
- [ ] Test correct weight profile selected for "awareness" goal
- [ ] Test correct weight profile selected for "conversion" goal
- [ ] Test unknown campaign goal falls back to awareness (not crash)
- [ ] Test weighted score computation is mathematically correct (hand-calculated expected value)
- [ ] Test Clarity floor violation detected (score 5.5 < floor 6.0)
- [ ] Test Brand Voice floor violation detected (score 4.5 < floor 5.0)
- [ ] Test no floor violations when scores are above floors
- [ ] Test ad with good weighted average but floor violation is rejected
- [ ] Test ad with no floor violations and weighted average >= 7.0 passes
- [ ] Test ad with no floor violations but weighted average < 7.0 is rejected
- [ ] Test rejection reasons are populated with clear human-readable messages
- [ ] Minimum: 10+ tests

#### D. Documentation

- [ ] Add P1-05 entry in `docs/DEVLOG.md`

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
| Campaign-goal-adaptive weights | R1-Q3 | Two profiles: awareness (ER/BV heavy) and conversion (CTA/VP heavy). Predictable and explainable. |
| Floor constraints | R1-Q3 | Clarity >= 6.0, Brand Voice >= 5.0 — hard minimums regardless of weighted average. |
| Quality threshold | PRD Section 5.2 | 7.0/10 weighted average to be considered publishable. |
| Quality ratchet | R1-Q9 | `effective_threshold = max(7.0, rolling_5batch_avg - 0.5)`. The 7.0 is the absolute floor; the ratchet (P1-10) only raises it. |

### Exact Weight Table (from PRD Section 5.2)

| Dimension | Awareness Weight | Conversion Weight | Floor Score |
|-----------|-----------------|-------------------|-------------|
| Clarity | 25% | 25% | 6.0 |
| Value Proposition | 20% | 25% | None |
| Call to Action | 10% | 30% | None |
| Brand Voice | 20% | 10% | 5.0 |
| Emotional Resonance | 25% | 10% | None |

### Files to Create

| File | Why |
|------|-----|
| `evaluate/dimensions.py` | Weight profiles, floor constraints, weighted scoring |
| `tests/test_evaluation/test_dimensions.py` | Weighting and floor constraint tests |

### Files to Modify

| File | Why |
|------|-----|
| `evaluate/evaluator.py` | Integrate weighting into the evaluation flow |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `evaluate/evaluator.py` | `EvaluationResult` — the per-dimension scores you are weighting |
| `iterate/ledger.py` | `log_event()` for logging rejection events |
| `data/config.yaml` | Threshold parameters |
| `docs/reference/prd.md` (R1-Q3, Section 5.2, R1-Q9) | Full weight table, floor constraints, quality ratchet spec |

---

## Definition of Done

- [ ] Awareness and conversion weight profiles implemented with exact weights from PRD
- [ ] `compute_weighted_score()` produces correct weighted averages
- [ ] Clarity >= 6.0 and Brand Voice >= 5.0 floor constraints enforced
- [ ] Floor violations trigger rejection regardless of weighted average
- [ ] Weighted average < 7.0 triggers rejection
- [ ] Rejection reasons are clear and human-readable
- [ ] Unknown campaign goals fall back gracefully
- [ ] Existing evaluator tests still pass
- [ ] New tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Committed on `develop`

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**P1-06 (Tiered model routing)** uses the weighted score to route ads into tiers: < 5.5 discarded cheaply (Flash only), > 7.0 published (Flash only), 5.5-7.0 escalated to Pro for regeneration. The weighting module determines which tier an ad falls into.

**P1-07 (Pareto-optimal regeneration)** uses the per-dimension scores (before weighting) to generate variants that improve the weakest dimension without regressing others.

**P1-10 (Quality ratchet)** builds on top of the 7.0 threshold from this ticket, implementing the rolling high-water mark: `effective_threshold = max(7.0, rolling_5batch_avg - 0.5)`.
