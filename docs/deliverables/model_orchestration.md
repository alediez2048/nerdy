# Multi-Model Orchestration Architecture

**Project:** Ad-Ops-Autopilot
**Pillar:** Every Token Is an Investment (Pillar 3)
**Reference:** R1-Q4, PRD Section 4.3

---

## Model Inventory

| Task | Model | API Name | Cost | Rationale |
|------|-------|----------|------|-----------|
| First-draft text generation | Gemini Flash | `gemini-2.0-flash` | ~$0.01/1K tokens | 80% of text work at lowest cost |
| Text regeneration (improvable) | Gemini Pro | `gemini-2.0-pro` | ~$0.05/1K tokens | Quality tokens on borderline ads (5.5-7.0) |
| Text evaluation (CoT scorer) | Gemini Flash | `gemini-2.0-flash` | ~$0.01/1K tokens | Structured evaluation doesn't need Pro |
| Image generation (quality tier) | Nano Banana Pro | `gemini-2.0-flash-preview-image-generation` | ~$0.13/image | High-fidelity output for anchor images |
| Image generation (cost tier) | Nano Banana 2 | `gemini-3.1-flash-image` | ~$0.02-0.05/image | Volume variants, experiments, ratio expansion |
| Image evaluation | Gemini Flash | `gemini-2.0-flash` (multimodal) | ~$0.01/1K tokens | Cheap multimodal for attribute + coherence |
| Video generation | Veo 3.1 Fast | `veo-3.1-fast` | ~$0.15/sec (~$0.90/6s) | Native audio, 1080p, 9:16 for Stories/Reels |
| Video evaluation | Gemini Flash | `gemini-2.0-flash` (multimodal) | ~$0.01/1K tokens | Frame sampling + attribute check |

---

## Routing Logic

### Text Pipeline

```
Brief → Flash (first draft) → Evaluate (Flash)
  ├─ Score < 5.5  → DISCARD (no further tokens)
  ├─ Score 5.5-7.0 → ESCALATE to Pro (regeneration)
  └─ Score >= 7.0  → PUBLISH (no further tokens needed)
```

**Key insight:** Flash handles 80% of text generation. Pro is only invoked for the improvable middle tier (5.5-7.0), where quality tokens have the highest marginal return.

### Image Pipeline

```
Visual Spec → Anchor (Nano Banana Pro) + 2 Variants (Nano Banana 2)
  → Evaluate all (Flash multimodal)
  → Select winner (Pareto)
  → Expand winning image to 3 aspect ratios (Nano Banana 2)
```

**Key insight:** Anchor images use Pro for maximum quality. Exploratory variants and aspect ratio expansion use NB2 at 60-85% lower cost. Same evaluation pipeline regardless of source model.

### Video Pipeline

```
Expanded Brief → Extract Video Spec → Veo 3.1 Fast (2 variants)
  → Evaluate (Flash multimodal) → Select winner
  → FAILURE: graceful degradation to copy + image only
```

**Key insight:** Video is the most expensive format (~$0.90/6s). Spec extraction ensures targeted generation. Graceful degradation means video failure never blocks ad delivery.

---

## Cost Optimization Strategies

### 1. Tiered Routing (Cheap-First)
Flash handles initial generation and all evaluation. Pro/Veo invoked only when the cheaper tier has proven the ad is worth investing in.

### 2. Result Caching
`iterate/cache.py` caches evaluation results. Re-evaluating the same ad text returns cached scores, saving ~$0.01 per duplicate call.

### 3. Budget Caps
- Per-ad budget cap prevents runaway spending on a single ad
- Session-level budget cap limits total API spend per pipeline run
- Budget override forces cost-tier model (NB2) when remaining budget is low

### 4. Early Termination
Ads scoring below 5.5 are discarded immediately — no regeneration tokens wasted on unsalvageable copy.

### 5. Winners-Only Expansion
Aspect ratio expansion (1:1, 4:5, 9:16) only runs on published winners. For 38 published ads, this means ~76 extra images instead of ~450.

### 6. Cost-Tier for Experiments
Style experiments (P3-04) and A/B variant generation use NB2 exclusively, keeping experiment costs at $3-7.50 per 150 images instead of $20.10.

---

## Cost Economics Summary (50-Ad Batch)

| Format | Stage | Model | Calls | Est. Cost |
|--------|-------|-------|-------|-----------|
| Text | First draft | Flash | 50 | ~$0.50 |
| Text | Evaluation | Flash | 50 | ~$0.30 |
| Text | Regeneration | Pro | ~15 | ~$0.75 |
| Image | Anchor gen | Pro | 50 | ~$6.50 |
| Image | Variant gen | NB2 | 100 | ~$3.50 |
| Image | Evaluation | Flash | 150 | ~$1.50 |
| Image | Ratio expansion | NB2 | ~76 | ~$2.66 |
| Video | Generation | Veo | 76 | ~$68.40 |
| Video | Evaluation | Flash | 76 | ~$0.76 |
| **Total** | | | | **~$84.87** |

Text + Image only (no video): **~$15.71**

---

## Cross-Format Cost Attribution

Every API call is tagged in the ledger with:
- `model_used`: Which model handled the call
- `tokens_consumed`: Input + output tokens (or 0 for per-call models)
- `action`: Pipeline stage (generation, evaluation, regeneration, etc.)
- `event_type`: Determines format (text, image, video)

The `evaluate/cost_reporter.py` module aggregates these into a `CrossFormatCostReport` with breakdowns by model, format, and task, with estimated USD costs.
