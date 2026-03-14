# P0-06 Primer: Evaluator Cold-Start Calibration

**For:** New Cursor Agent session  
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG  
**Date:** March 2026  
**Previous work:** P0-05 (reference ad collection with labels) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P0-06 **calibrates the LLM-as-Judge evaluator** against the labeled reference ads before the system generates a single ad. This is the most critical calibration step: if the evaluator can't reliably score the best reference ads high and the worst ones low, the entire feedback loop is worthless.

### Why It Matters

- **The taste problem** (assignment spec): "The hardest part isn't generation — it's evaluation"
- **Cold-start** (R1-Q8): Calibrate the evaluator before trusting the feedback loop
- If the evaluator scores garbage at 7.5, the system will publish garbage
- This is where the chain-of-thought evaluation prompt (R3-Q6) gets its first real test

---

## What Was Already Done

- P0-05: Reference ads collected with 5–10 labeled "excellent" and 5–10 labeled "poor"
- Assignment spec defines the 5 quality dimensions and scoring rubric
- `.claude/skills/adops-evaluation/SKILL.md` defines the 5-step CoT evaluation prompt

---

## What This Ticket Must Accomplish

### Goal

Build the first draft of the chain-of-thought evaluation prompt, run it against all labeled reference ads, and tune until excellent ads score ≥7.5 and poor ads score ≤5.0.

### Deliverables Checklist

#### A. Evaluator Module (`evaluate/evaluator.py`)

- [ ] `evaluate_ad(ad_text: dict, campaign_goal: str = "conversion") -> EvaluationResult`
- [ ] Implements the 5-step CoT prompt sequence (R3-Q6):
  1. Read ad
  2. Decompose (identify hook, value prop, CTA, emotional angle)
  3. Compare against rubric calibration examples
  4. Score with contrastive rationale per dimension
  5. Flag confidence per dimension
- [ ] Returns structured JSON matching the evaluation output schema
- [ ] Campaign-goal-adaptive weighting (R1-Q3)
- [ ] Floor constraint enforcement (Clarity ≥ 6.0, Brand Voice ≥ 5.0)
- [ ] Uses Gemini API for evaluation calls

#### B. Calibration Run

- [ ] Run evaluator against ALL labeled reference ads (excellent + poor)
- [ ] Compare evaluator scores against human-assigned labels
- [ ] Success criteria: evaluator within ±1.0 of human labels on 80%+ of scores
- [ ] Excellent ads average ≥7.5, poor ads average ≤5.0
- [ ] If calibration fails: iterate on the evaluation prompt (adjust rubric examples, add few-shot calibration ads)
- [ ] Document calibration iterations in decision log

#### C. Tests (`tests/test_evaluation/test_golden_set.py`)

- [ ] TDD first
- [ ] Test evaluator returns valid EvaluationResult schema
- [ ] Test all 5 dimensions scored independently
- [ ] Test contrastive rationale present for each dimension
- [ ] Test confidence flag present for each dimension
- [ ] Test aggregate score uses correct campaign-goal weights
- [ ] Test floor constraint enforcement
- [ ] Minimum: 6+ tests

#### D. Documentation

- [ ] Add P0-06 entry in `docs/DEVLOG.md`
- [ ] Document calibration results: which ads scored well/poorly, prompt iterations attempted

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/P0-06-evaluator-calibration
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Cold-start | R1-Q8 | Competitor-bootstrapped calibration — calibrate evaluator before trusting loop |
| Evaluation prompt | R3-Q6 | Chain-of-thought 5-step with forced decomposition before scoring |
| Contrastive rationales | R3-Q10 | "What would +2 look like?" — actionable feedback for regeneration |
| Dimension weighting | R1-Q3 | Campaign-goal-adaptive with floor constraints |

### Files to Create

| File | Why |
|------|-----|
| `evaluate/evaluator.py` | Core evaluation module |
| `tests/test_evaluation/test_golden_set.py` | Calibration tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `data/reference_ads.json` | Labeled reference ads for calibration |
| `.claude/skills/adops-evaluation/SKILL.md` | Full evaluation framework spec |
| `.claude/skills/adops-evaluation/references/evaluation-sample.json` | Expected output format |
| `interviews.md` (R3-Q6) | CoT evaluation prompt design rationale |
| `.cursor/rules/evaluation-framework.mdc` | Dimension definitions, weighting, ratchet |

---

## Definition of Done

- [ ] Evaluator module implemented with 5-step CoT prompt
- [ ] Calibration run complete: scores within ±1.0 of human labels on 80%+
- [ ] Excellent reference ads average ≥7.5, poor ads average ≤5.0
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated with calibration results
- [ ] Feature branch pushed

---

## Estimated Time: 60–90 minutes

---

## After This Ticket: What Comes Next

- **P0-07** (Golden set regression tests) — uses the calibrated evaluator as the test target
- **P1-04** (Chain-of-thought evaluator) — extends this with full pipeline integration
- The evaluator is now trusted — the feedback loop can begin
