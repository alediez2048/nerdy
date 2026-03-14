# P1-19 Primer: Image Cost Tracking

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P1-11 (token attribution engine), P1-14 (Nano Banana Pro integration), P1-15 (visual attribute evaluator) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P1-19 extends the **token attribution engine** (P1-11) to track image generation costs alongside text costs. Every image generation call — per-image, per-variant, per-regen attempt, per-aspect-ratio — is attributed and logged. Variant selection win rates are tracked to identify which variant strategies (anchor, tone shift, composition shift) are most cost-effective. The result is a unified cost-per-publishable-ad metric that spans both text and image pipelines.

### Why It Matters

- **Every Token Is an Investment** (Pillar 3): Image generation costs (~$0.13/image via Nano Banana Pro) can exceed text costs — tracking them is essential for ROI awareness
- Without image cost tracking, cost-per-publishable-ad is incomplete and misleading
- Variant win rate data reveals whether 3-variant generation is worth 3x the image cost
- Per-regen cost tracking exposes whether targeted regen (P1-17) is cost-effective or if the budget cap should be tightened
- Feeds the dashboard (P5-05) with complete cost attribution data

---

## What Was Already Done

- P1-11: Token attribution engine tracks text pipeline costs (per-API-call, per-stage, per-model)
- P1-14: Image generation via Nano Banana Pro with 3 variants per ad
- P1-15: Visual attribute evaluation (each evaluation = a Gemini Flash call with cost)
- P1-16: Coherence checking (each check = a Gemini Flash call with cost)
- P1-17: Regen loop generates additional images (up to 5 total per ad)

---

## What This Ticket Must Accomplish

### Goal

Extend the token attribution engine to comprehensively track image pipeline costs, compute unified cost-per-publishable-ad across text + image, and log variant strategy win rates for continuous improvement.

### Deliverables Checklist

#### A. Image Cost Attribution (`evaluate/image_cost_tracker.py`)

- [ ] `track_image_generation(ad_id: str, variant_type: str, aspect_ratio: str, cost: float, model: str, is_regen: bool)`
  - Records cost per image generation call
  - Tags: `variant_type` (anchor, tone_shift, composition_shift, regen), `aspect_ratio` (1:1, 4:5, 9:16), `is_regen` (True/False), `model` (nano_banana_pro)
- [ ] `track_image_evaluation(ad_id: str, eval_type: str, cost: float)`
  - Records cost per evaluation call (attribute check or coherence check)
  - Tags: `eval_type` (attribute_eval, coherence_eval)
- [ ] `get_image_cost_breakdown(ad_id: str) -> ImageCostBreakdown`
  - Returns: generation cost, evaluation cost, regen cost, total image cost
  - Broken down by variant type and aspect ratio

#### B. Unified Cost Metrics (`evaluate/cost_aggregator.py` or extend P1-11)

- [ ] `get_unified_cost(ad_id: str) -> UnifiedCost`
  - Combines text pipeline cost (from P1-11) + image pipeline cost
  - Returns: `text_cost`, `image_cost`, `total_cost`, `cost_per_publishable_ad`
- [ ] `get_batch_cost_summary(batch_id: str) -> BatchCostSummary`
  - Aggregate costs across a batch: total text, total image, total regen, average cost per ad
  - Publishable vs. discarded ad cost comparison

#### C. Variant Win Rate Tracking

- [ ] `track_variant_selection(ad_id: str, winner_type: str, all_types: list[str])`
  - Records which variant strategy won Pareto selection
- [ ] `get_variant_win_rates() -> dict[str, float]`
  - Returns win rate per variant type: e.g., `{"anchor": 0.55, "tone_shift": 0.30, "composition_shift": 0.15}`
  - Flags if one strategy dominates >80% (indicates potential for reducing to 2 variants)

#### D. Tests (`tests/test_pipeline/test_image_cost_tracker.py`)

- [ ] TDD first
- [ ] Test image generation cost tracked with correct tags
- [ ] Test image evaluation cost tracked separately
- [ ] Test cost breakdown returns correct per-variant totals
- [ ] Test unified cost combines text + image correctly
- [ ] Test regen costs attributed separately from initial generation
- [ ] Test variant win rate calculation
- [ ] Test >80% dominance flag triggers
- [ ] Minimum: 7+ tests

#### E. Documentation

- [ ] Add P1-19 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/P1-19-image-cost-tracking
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Full token attribution | R1-Q7 | Every API call tagged with cost, model, purpose — now extended to image pipeline |
| Marginal quality analysis | R1-Q7 | Cost-per-publishable-ad enables ROI calculation for image variants vs. single-image |
| Variant selection bias | Risk Register | Track win rates; if one strategy dominates >80%, reduce to 2 variants |
| Image cost mitigation | Risk Register | Generate extra aspect ratios only for published winners; budget tier falls back to single-image |

### Files to Create

| File | Why |
|------|-----|
| `evaluate/image_cost_tracker.py` | Image-specific cost attribution |
| `tests/test_pipeline/test_image_cost_tracker.py` | Cost tracking tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| P1-11 token attribution module | Existing cost tracking patterns to extend |
| P1-14 image generation module | Where generation costs originate |
| P1-15 image evaluator | Where evaluation costs originate |
| P1-17 image regen loop | Where regen costs originate |

---

## Definition of Done

- [ ] Image generation costs tracked per-image, per-variant, per-regen, per-aspect-ratio
- [ ] Image evaluation costs tracked (attribute checks + coherence checks)
- [ ] Unified cost-per-publishable-ad combines text + image pipeline costs
- [ ] Variant win rates tracked; >80% dominance flagged
- [ ] Dashboard-ready cost data (feeds P5-05)
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**P1-20 (50+ full ad generation run)** is the capstone of Phase 1. With image cost tracking in place, the full run will produce comprehensive cost attribution across text and image pipelines. The dashboard will show exactly what each publishable ad cost, which variant strategies won, and whether the multi-variant approach is cost-effective.
