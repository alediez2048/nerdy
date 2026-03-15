# P3-01 Primer: Nano Banana 2 Integration (Cost Tier)

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P1-14 (Nano Banana Pro integration), P1-19 (image cost tracking) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P3-01 adds **Nano Banana 2** (Gemini 3.1 Flash Image) as a cost-tier alternative to Nano Banana Pro (Gemini 3 Pro Image) for image generation. Both models produce images; model routing decides which to use based on the brief's budget and quality needs. Cost is tracked separately per model.

### Why It Matters

- **Every Token Is an Investment** (Pillar 3): Nano Banana 2 costs ~$0.02–0.05/image vs ~$0.13/image for Pro — 60–85% savings for variant volume
- Enables higher variant counts without budget explosion (150 images at $3–7.50 vs $20.10)
- Cost-tier routing lets the pipeline use Pro for anchors (quality-critical) and Flash for exploratory variants
- Separate cost tracking per model enables accurate ROI analysis

---

## What Was Already Done

- P1-14: Nano Banana Pro integration (`generate/image_generator.py`) — image generation pipeline with 3 variants per ad
- P1-15: Visual attribute evaluator (`evaluate/image_evaluator.py`) — evaluates images regardless of source model
- P1-19: Image cost tracking (`evaluate/image_cost_tracker.py`) — tracks generation/eval/regen tokens per ad
- P0-04: Model router (`generate/model_router.py`) — tiered routing between Flash and Pro for text

---

## What This Ticket Must Accomplish

### Goal

Add Nano Banana 2 as a second image generation model and implement routing logic that decides which model to use per variant.

### Deliverables Checklist

#### A. Nano Banana 2 Client (`generate/image_generator.py` — extend)

- [ ] Add `MODEL_NANO_BANANA_2 = "gemini-3.1-flash-image"` constant alongside existing Pro constant
- [ ] `generate_image_nb2(visual_spec: dict, seed: int, aspect_ratio: str) -> ImageResult`
  - Same interface as existing `generate_image()` but routes to Flash Image model
  - Returns same `ImageResult` dataclass (image_path, model_used, tokens_consumed, metadata)
  - Cheaper model — fewer tokens consumed per call
- [ ] Both `generate_image()` (Pro) and `generate_image_nb2()` (Flash) share the same retry/error handling

#### B. Image Model Router (`generate/image_generator.py` — extend)

- [ ] `select_image_model(variant_type: str, budget_remaining: float | None) -> str`
  - Default routing: anchor → Pro, tone_shift/composition_shift → Nano Banana 2
  - Budget override: if budget_remaining < threshold, all variants → Nano Banana 2
  - Returns model identifier string
- [ ] `generate_image_routed(visual_spec: dict, seed: int, aspect_ratio: str, variant_type: str, budget_remaining: float | None) -> ImageResult`
  - Selects model via `select_image_model()`, then calls appropriate generator
  - Logs model_used in result for cost attribution

#### C. Cost Tracking Updates (`evaluate/image_cost_tracker.py` — extend)

- [ ] `get_image_cost_breakdown()` must separate costs by model_used
  - Add `pro_tokens` and `flash_tokens` fields to `ImageCostBreakdown`
  - Existing `generation_tokens` remains as total
- [ ] `get_cost_per_model(ledger_path: str) -> dict[str, int]`
  - Returns token counts grouped by model_used for all image events

#### D. Tests (`tests/test_pipeline/test_image_model_routing.py`)

- [ ] TDD first
- [ ] Test anchor variant routes to Pro by default
- [ ] Test non-anchor variants route to Nano Banana 2 by default
- [ ] Test budget override forces all to Nano Banana 2
- [ ] Test `generate_image_routed()` returns correct model_used in result
- [ ] Test cost breakdown separates Pro vs Flash tokens
- [ ] Test `get_cost_per_model()` aggregates correctly
- [ ] Test both models produce valid `ImageResult` (mock API)
- [ ] Test fallback to Pro if Flash unavailable
- [ ] Minimum: 8+ tests

#### E. Documentation

- [ ] Add P3-01 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

Work on `develop` branch per project convention.

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Tiered model routing | R1-Q4, Section 4.3 | Flash for volume, Pro for quality-critical — same pattern as text model routing |
| Cost attribution | Pillar 3 | Every token tracked per model, per variant, per ad |
| Same evaluation pipeline | P1-15 | Both models' outputs evaluated by same attribute checklist — quality is quality regardless of source |

### Cost Economics

| Model | Cost/Image | 150 Images | 256 Images (with regens + ratios) |
|-------|-----------|------------|-----------------------------------|
| Nano Banana Pro | ~$0.13 | ~$20.10 | ~$34.30 |
| Nano Banana 2 | ~$0.02–0.05 | ~$3.00–7.50 | ~$5.12–12.80 |

### Files to Modify

| File | Why |
|------|-----|
| `generate/image_generator.py` | Add NB2 client + model routing |
| `evaluate/image_cost_tracker.py` | Per-model cost breakdown |
| `tests/test_pipeline/test_image_model_routing.py` | New test file |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `generate/image_generator.py` | Existing Pro integration to mirror |
| `generate/model_router.py` | Text model routing pattern to follow |
| `evaluate/image_cost_tracker.py` | Current cost tracking to extend |
| `docs/reference/prd.md` (Section 4.3) | Model routing architecture |

---

## Definition of Done

- [ ] Nano Banana 2 generates images via Gemini 3.1 Flash Image API
- [ ] Model router selects Pro for anchors, Flash for variants
- [ ] Budget override routes all to cheaper model
- [ ] Cost tracked separately per model
- [ ] All existing image tests still pass
- [ ] New tests pass (8+)
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**P3-02 (Single-variable A/B variants — copy)** uses the cost-tier model to generate higher variant volumes affordably. Without P3-01, variant scaling is cost-prohibitive.
