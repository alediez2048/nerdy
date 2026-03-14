# P2-01 Primer: Inversion Tests

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P1-04 (CoT evaluator), P1-05 (campaign-goal-adaptive weighting), P0-07 (golden set) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P2-01 implements **inversion tests** — the core proof that the evaluator measures 5 independent dimensions, not a "general quality" halo. Take high-scoring ads, systematically degrade ONE dimension at a time, and verify that only the degraded dimension's score drops significantly (≥1.5 points) while all other dimensions remain stable (±0.5).

### Why It Matters

- **The System Knows What It Doesn't Know** (Pillar 4): Without inversion tests, the evaluator's 5-dimensional scores could be decorative — all moving together based on "vibes"
- This is the PRD's primary proof of evaluation independence (R2-Q3)
- Risk Register: "Evaluator halo effect" is rated High Impact, Medium Probability — this ticket is the mitigation
- If dimensions aren't independent, targeted regeneration (P1-07, P1-08) can't work — we'd be fixing the wrong thing
- Success criteria: "5 dimensions, proven independent" (PRD Section 7.1)

---

## What Was Already Done

- P0-07: Golden set of 18 human-scored reference ads in `tests/test_data/golden_ads.json`
- P1-04: Chain-of-thought 5-step evaluator with contrastive rationales, confidence flags
- P1-05: Campaign-goal-adaptive weighting (awareness vs conversion profiles)
- P0-06: Evaluator calibration — 89.5% within ±1.0 of human labels

---

## What This Ticket Must Accomplish

### Goal

Create degraded versions of high-scoring ads (one dimension damaged at a time) and verify the evaluator correctly identifies only the damaged dimension. 10+ inversion tests.

### Deliverables Checklist

#### A. Degraded Test Data (`tests/test_data/degraded_ads.json`)

- [ ] Start from 3-4 high-scoring ads from `golden_ads.json` (quality_label: "excellent")
- [ ] For each ad, create 5 degraded variants — one per dimension:
  - **Clarity degraded:** Replace clear structure with rambling, run-on sentences. Remove logical flow. Keep message but obscure it.
  - **Value Proposition degraded:** Remove all specific benefits. Replace with generic filler ("We're great!"). Keep everything else intact.
  - **CTA degraded:** Remove or weaken the call to action. Replace "Start Your Free Session Today" with "Maybe check us out sometime if you want."
  - **Brand Voice degraded:** Rewrite in completely wrong voice — use fast-food urgency, slang, or corporate jargon. Keep the content factually the same.
  - **Emotional Resonance degraded:** Strip all emotional language. Make it a dry, clinical fact sheet. Remove aspirational framing.
- [ ] Each entry includes: `original_text`, `degraded_text`, `degraded_dimension`, `expected_drop_dimension`
- [ ] Minimum: 15 degraded variants (3 originals × 5 dimensions)

#### B. Inversion Test Suite (`tests/test_evaluation/test_inversion.py`)

- [ ] `test_clarity_inversion`: Degrading clarity drops clarity ≥1.5, others stable ±0.5
- [ ] `test_value_proposition_inversion`: Same pattern for VP
- [ ] `test_cta_inversion`: Same pattern for CTA
- [ ] `test_brand_voice_inversion`: Same pattern for Brand Voice
- [ ] `test_emotional_resonance_inversion`: Same pattern for Emotional Resonance
- [ ] `test_all_inversions_systematic`: Loop through all degraded ads, verify pattern holds for ≥80%
- [ ] `test_degraded_dimension_is_weakest`: Degraded dimension should be the weakest (or second weakest) in evaluation
- [ ] `test_original_scores_above_threshold`: Confirm originals score ≥7.0 before degradation
- [ ] `test_degraded_scores_drop_meaningfully`: Average drop across degraded dim ≥1.5
- [ ] `test_non_degraded_dimensions_stable`: Average stability of non-degraded dims ≤0.5
- [ ] Minimum: 10+ tests

#### C. Documentation

- [ ] Add P2-01 entry in `docs/DEVLOG.md`
- [ ] Document any dimensions that show coupling (if clarity and VP move together, note it)

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Inversion tests | R2-Q3 (Option C) | Core proof of dimension independence. Catches halo effect. |
| CoT decomposition | R3-Q6 | 5-step structured evaluation prevents halo through forced decomposition before scoring |
| Contrastive rationales | R3-Q10 | "+2 version" forces dimension-specific reasoning |

### Files to Create

| File | Why |
|------|-----|
| `tests/test_data/degraded_ads.json` | Degraded test data (originals + 5 variants each) |
| `tests/test_evaluation/test_inversion.py` | Inversion test suite |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `evaluate/evaluator.py` | `evaluate_ad()` function signature and `EvaluationResult` structure |
| `evaluate/dimensions.py` | Weight profiles, floor constraints, 5 dimension names |
| `tests/test_data/golden_ads.json` | Source of high-scoring originals for degradation |
| `tests/test_evaluation/test_golden_set.py` | Existing test patterns and mocking approach |

### Key API Details

```python
from evaluate.evaluator import evaluate_ad

# evaluate_ad signature:
result = evaluate_ad(
    ad_text={
        "ad_id": str,
        "primary_text": str,
        "headline": str,
        "description": str,
        "cta_button": str,
    },
    campaign_goal="conversion",  # or "awareness"
    audience="parents",          # or "students"
    ledger_path=None,            # optional
)

# result.scores[dimension] = {"score": float, "rationale": str, ...}
# Dimensions: "clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance"
```

### Testing Approach

These tests call the real Gemini API — they are NOT mocked. The point is to verify real evaluator behavior. Tests should:
- Use `@pytest.mark.skipif` if `GEMINI_API_KEY` is not set
- Allow ±0.5 tolerance on "stable" dimensions (LLM scoring has natural variance)
- Require ≥1.5 drop on degraded dimension (meaningful, not noise)
- Run on at least 3 different original ads to establish pattern

---

## Definition of Done

- [ ] 15+ degraded ad variants in `tests/test_data/degraded_ads.json`
- [ ] 10+ inversion tests passing
- [ ] Degraded dimension drops ≥1.5 on ≥80% of cases
- [ ] Non-degraded dimensions stable ±0.5 on ≥80% of cases
- [ ] Any dimension coupling documented in decision log
- [ ] DEVLOG updated

---

## After This Ticket: What Comes Next

**P2-02 (Correlation Analysis)** complements inversion tests with a statistical approach — computing pairwise Pearson correlation across all 5 dimensions from the P1-20 production data. Together, P2-01 and P2-02 provide both causal (inversion) and statistical (correlation) evidence of dimension independence.
