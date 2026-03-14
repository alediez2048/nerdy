# P1-15 Primer: Visual Attribute Evaluator + Pareto Image Selection

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P1-14 (Nano Banana Pro integration + multi-variant generation) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P1-15 implements the **visual attribute evaluator** and **Pareto image selection** system. Each of the 3 image variants generated in P1-14 is evaluated via a multimodal Gemini Flash call against a binary attribute checklist (age-appropriate subjects, warm lighting, diversity, brand consistency, no artifacts). Variants must pass 80% of attributes. The best variant is selected using a composite Pareto score: `(attribute_pass_pct x 0.4) + (coherence_avg x 0.6)`. All 3 variants are logged for learning.

### Why It Matters

- **Decomposition Is the Architecture** (Pillar 1): Visual brand consistency is decomposed into binary attributes, just like text quality is decomposed into 5 dimensions
- Without structured evaluation, image selection is random — not learnable
- The attribute checklist provides actionable feedback for targeted regen (P1-17)
- Pareto selection ensures the winning image is strong on both visual quality AND text-image coherence
- Losing variant data feeds continuous improvement of visual spec generation

---

## What Was Already Done

- P1-14: Nano Banana Pro integration generates 3 image variants per ad (anchor, tone shift, composition shift)
- P1-14: Visual spec extraction from expanded briefs
- P1-14: All variants + visual specs logged to ledger
- P0-06: Evaluator calibration patterns (text side — same decomposition philosophy applies to images)
- R2-Q7: Architectural decision — attribute checklist evaluation over holistic LLM rating or CLIP similarity

---

## What This Ticket Must Accomplish

### Goal

Build the visual attribute evaluator that scores each image variant against a structured checklist, then select the best variant using a composite Pareto score that balances attribute quality (40%) and text-image coherence (60%).

### Deliverables Checklist

#### A. Visual Attribute Evaluator (`evaluate/image_evaluator.py`)

- [ ] `evaluate_image_attributes(image_path: str, visual_spec: dict) -> ImageAttributeResult`
  - Multimodal Gemini Flash call: image + visual spec as input
  - Binary attribute checklist:
    - `age_appropriate`: Subjects appear student-age (16-18) or parent-age
    - `lighting`: Warm, inviting lighting consistent with educational context
    - `diversity`: Inclusive representation
    - `brand_consistent`: Matches Varsity Tutors visual identity (no competitor branding)
    - `no_artifacts`: No AI artifacts (extra fingers, warped text, distorted faces)
  - Returns per-attribute pass/fail + overall `attribute_pass_pct`
  - 80% pass threshold (4 of 5 attributes must pass)
- [ ] Structured JSON output matching ledger schema

#### B. Pareto Image Selection (`evaluate/image_selector.py`)

- [ ] `select_best_variant(variants: list[ImageVariantResult]) -> ImageSelectionResult`
  - Composite score: `(attribute_pass_pct x 0.4) + (coherence_avg x 0.6)`
  - Coherence score comes from P1-16 (text-image coherence checker)
  - Select variant with highest composite score
  - Log all 3 variants with scores, selection rationale, and losing variant reasons
- [ ] `log_variant_results(results: list[ImageVariantResult], winner_id: str, ledger_path: str)`
  - Append `ImageEvaluated` event for each variant
  - Append `ImageSelected` event for the winner with composite breakdown

#### C. Tests (`tests/test_pipeline/test_image_evaluator.py`)

- [ ] TDD first
- [ ] Test attribute evaluation returns correct structure
- [ ] Test 80% threshold logic (4/5 pass = pass, 3/5 = fail)
- [ ] Test Pareto composite score calculation
- [ ] Test variant selection picks highest composite
- [ ] Test all variants logged (not just winner)
- [ ] Test edge case: tie-breaking (first variant wins ties)
- [ ] Test edge case: all variants fail attributes
- [ ] Minimum: 7+ tests

#### D. Documentation

- [ ] Add P1-15 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/P1-15-visual-attribute-evaluator
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Attribute checklist evaluation | R2-Q7 | Binary attributes are easy for multimodal models to assess; aggregate is interpretable; feedback loop can target specific attributes |
| Pareto selection | R1-Q5 | Composite score prevents single-dimension dominance; no dimension ignored |
| Decomposition | Pillar 1 | Visual consistency decomposed into checkable attributes, same philosophy as text dimensions |

### Files to Create

| File | Why |
|------|-----|
| `evaluate/image_evaluator.py` | Multimodal attribute checklist evaluation |
| `evaluate/image_selector.py` | Pareto composite scoring and variant selection |
| `tests/test_pipeline/test_image_evaluator.py` | Attribute + selection tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| P1-14 image generation module | How variants are generated and stored |
| `evaluate/` existing evaluator modules | Pattern for structured evaluation output |
| `interviews.md` (R2-Q7) | Full rationale for attribute checklist approach |
| `.cursor/rules/pipeline-patterns.mdc` | Evaluation architecture spec |

---

## Definition of Done

- [ ] Each of 3 image variants scored against 5-attribute binary checklist
- [ ] 80% pass threshold correctly enforced
- [ ] Composite Pareto score calculated: `(attribute_pass_pct x 0.4) + (coherence_avg x 0.6)`
- [ ] Best variant selected by highest composite score
- [ ] All 3 variants logged to ledger (winners and losers)
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**P1-16 (Text-image coherence checker)** builds the coherence scoring that feeds into this ticket's Pareto selection (the 60% weight). P1-15 and P1-16 work together — attribute quality is 40% of the composite, coherence is 60%. After both are complete, P1-17 adds targeted regen for failed variants.
