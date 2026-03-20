# Phase P1: Full-Ad Pipeline — Copy + Image

## Context

P1 builds the complete ad generation pipeline end-to-end: brief expansion → copy generation → evaluation → routing → regeneration → image generation → evaluation → assembly. This is the core product — everything the rubric evaluates (quality measurement, iteration, speed, documentation) depends on P1 producing 50+ scored ads with visible improvement.

## Tickets (20)

### P1-01: Brief Expansion Engine
- `generate/brief_expansion.py` — `expand_brief()` → ExpandedBrief
- Loads brand_knowledge.json + competitive context, "use ONLY verified facts" constraint
- **AC:** 13 tests, no hallucinated claims, competitive context included

### P1-02: Ad Copy Generator
- `generate/ad_generator.py` — `generate_ad()` → GeneratedAd (primary_text, headline, description, cta_button)
- Reference-decompose-recombine: selects structural atoms, builds recombination prompt
- **AC:** 15 tests, all 4 components generated, deterministic seeds

### P1-03: Audience-Specific Brand Voice Profiles
- `generate/brand_voice.py` — `get_voice_profile()` → VoiceProfile (parent/student)
- Few-shot examples from reference_ads.json, anti-examples, brand constants
- **AC:** 10 tests, correct profile per audience

### P1-04: Chain-of-Thought Evaluator
- Extended `evaluate/evaluator.py` with 5-step CoT, contrastive rationales, confidence flags
- `DimensionRationale` with current_assessment, plus_two_description, specific_gap
- **AC:** 21 tests, structural elements extracted, confidence flags present

### P1-05: Campaign-Goal-Adaptive Weighting
- `evaluate/dimensions.py` — WeightProfile, AWARENESS_WEIGHTS, CONVERSION_WEIGHTS
- Floors: Clarity ≥ 6.0, Brand Voice ≥ 5.0 (violations = reject regardless of aggregate)
- **AC:** Weights sum to 1.0, floor violations trigger rejection

### P1-06: Tiered Model Routing
- `generate/model_router.py` — route by score: <5.5 discard, 5.5–7.0 escalate to Pro, ≥7.0 publish
- Token spend concentrated on improvable range
- **AC:** Correct triage, routing decisions logged

### P1-07: Pareto-Optimal Regeneration
- `iterate/pareto_selection.py` — `is_pareto_dominant()`, `filter_regressions()`, `select_best()`
- No dimension regresses vs. prior cycle
- **AC:** 8+ tests, dimension collapse prevented

### P1-08: Brief Mutation + Escalation
- `iterate/brief_mutation.py` — diagnose weakest dimension, mutate brief (cycle 2), escalate (cycle 3)
- **AC:** 8+ tests, mutation logged, escalation triggers on third failure

### P1-09: Distilled Context Objects
- `iterate/context_distiller.py` — compress iteration history into fixed-size context
- **AC:** Prompt stays compact regardless of cycle depth

### P1-10: Quality Ratchet
- `iterate/quality_ratchet.py` — `max(7.0, rolling_5batch_avg - 0.5)`, monotonically non-decreasing
- **AC:** 8+ tests, threshold never decreases

### P1-11: Token Attribution Engine
- `iterate/token_tracker.py` — `aggregate_by_stage()`, `cost_per_publishable_ad()`, `marginal_quality_gain()`
- **AC:** 9+ tests, cost-per-ad computed, marginal gain shows deltas

### P1-12: Result-Level Cache
- `iterate/cache.py` — `compute_cache_key()`, version-based invalidation on recalibration
- **AC:** 10+ tests, cache hits on resume, recalibration clears all

### P1-13: Batch-Sequential Processor
- `iterate/batch_processor.py` — batches of 10, sequential across stages
- `iterate/pipeline_runner.py` — main orchestrator
- **AC:** 8+ tests, 50+ ads processed, batch boundaries = checkpoints

### P1-14: Nano Banana Pro Integration + Multi-Variant Image Generation
- `generate/visual_spec.py` — `VisualSpec`, `extract_visual_spec()`, `build_image_prompt()`
- `generate/image_generator.py` — `ImageVariant`, 3 variants per ad (anchor, tone_shift, composition_shift)
- **AC:** 10+ tests, deterministic seeds, all events logged

### P1-15: Visual Attribute Evaluator + Pareto Image Selection
- `evaluate/image_evaluator.py` — 5 binary attributes, 80% pass threshold
- `evaluate/image_selector.py` — composite score = 0.4 × attribute_pct + 0.6 × coherence_avg
- **AC:** 7+ tests, 80% threshold enforced

### P1-16: Text-Image Coherence Checker
- `evaluate/coherence_checker.py` — 4 dimensions (message_alignment, audience_match, emotional_consistency, visual_narrative)
- Threshold: below 6.0 = incoherent
- **AC:** 7+ tests, coherence feeds Pareto selection at 60% weight

### P1-17: Image Targeted Regen Loop
- `iterate/image_regen.py` — diagnose failure, build regen spec, cap at 5 images/ad
- **AC:** 8+ tests, diagnostic-guided regen, budget enforced

### P1-18: Full Ad Assembly + Export
- `output/assembler.py` — `AssembledAd`, `assemble_ad()`, `is_publishable()`
- `output/exporter.py` — JSON/CSV export
- **AC:** 8+ tests, Meta-ready file structure

### P1-19: Image Cost Tracking
- `evaluate/image_cost_tracker.py` — per-image, per-variant, per-regen costs, variant win rates
- **AC:** 7+ tests, unified text + image cost breakdown

### P1-20: 50+ Full Ad Generation Run
- Full pipeline: 5+ batches, 3+ cycles, 50+ full ads (copy + image)
- Quality trend shows improvement, cost attribution complete
- **AC:** 50+ ads evaluated, quality trend improves, output folder assembled

## Dependency Graph

```
P1-01 (Brief Expansion) → P1-02 (Copy Gen) → P1-03 (Brand Voice)
                                                      │
P1-04 (CoT Eval) → P1-05 (Weighting) → P1-06 (Routing)
                                              │
P1-07 (Pareto) → P1-08 (Mutation) → P1-09 (Context) → P1-10 (Ratchet)
                                                              │
P1-11 (Tokens) → P1-12 (Cache) → P1-13 (Batch Processor)
                                        │
P1-14 (Image Gen) → P1-15 (Image Eval) → P1-16 (Coherence) → P1-17 (Image Regen)
                                                                      │
P1-18 (Assembly) → P1-19 (Image Cost) → P1-20 (50-Ad Run)
```

## Key Decisions Made

1. **Reference-decompose-recombine over persona prompting** — structural atoms are learnable and transferable
2. **Pareto selection over constraint prompting** — model ignores constraints; generate variants and select mathematically
3. **Brief mutation after 2 failed cycles** — problem is the brief, not the generator
4. **Distilled context over raw history** — prevents prompt bloat at cycle 5+
5. **3 image variants per ad** — anchor + tone shift + composition shift enables selection without brute force

## Status: ✅ COMPLETE (all 20 tickets, 240+ tests cumulative)
