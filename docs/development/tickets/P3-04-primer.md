# P3-04 Primer: Image Style Transfer Experiments

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P1-14 (image generator), P1-15 (image evaluator), P3-01 (cost-tier model), P3-03 (image A/B variants) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P3-04 experiments with **audience-specific image styles** for ad creatives. Different visual styles (photorealistic, illustrated, flat-design, lifestyle) are tested per audience segment (parents vs students) to discover which styles resonate best. The style-audience mapping is documented for future generation guidance.

### Why It Matters

- **Learning Is Structural** (Pillar 6): Style preferences differ by audience — parents may prefer polished/professional while students prefer authentic/casual
- Style transfer is cheaper than content regen — same scene rendered in different styles
- Results feed back into visual spec defaults per audience
- Documented style-audience mapping becomes institutional knowledge

---

## What Was Already Done

- P1-03: Brand voice profiles (`generate/brand_voice.py`) — audience-specific voice (parents vs students)
- P1-14: Image generator (`generate/image_generator.py`) — generates images from visual spec
- P1-15: Image evaluator (`evaluate/image_evaluator.py`) — attribute checklist scoring
- P3-01: Cost-tier model — Nano Banana 2 for volume experiments
- P3-03: Image A/B variants — single-variable visual comparison framework

---

## What This Ticket Must Accomplish

### Goal

Define a style library, generate images in multiple styles per audience, evaluate which styles perform best per segment, and document the style-audience mapping.

### Deliverables Checklist

#### A. Style Library (`generate/style_library.py` — new)

- [ ] `STYLE_PRESETS` dictionary defining available styles:
  - `photorealistic`: Natural lighting, real-world textures, candid feel
  - `illustrated`: Clean vector-style, modern illustration, bold outlines
  - `flat_design`: Minimal, geometric shapes, solid colors, no gradients
  - `lifestyle`: Aspirational, warm tones, natural settings, social-media aesthetic
  - `editorial`: Magazine-quality, high contrast, dramatic lighting
- [ ] `StylePreset` dataclass:
  - `name: str`
  - `prompt_modifier: str` (text appended to image generation prompt)
  - `target_audiences: list[str]` (audiences this style is hypothesized to work for)
- [ ] `get_styles_for_audience(audience: str) -> list[StylePreset]`
  - Returns styles to test for the given audience (all styles initially)
- [ ] `apply_style_to_spec(visual_spec: dict, style: StylePreset) -> dict`
  - Returns a modified visual spec with style modifiers applied

#### B. Style Experiment Runner (`generate/style_experiments.py` — new)

- [ ] `StyleExperimentResult` dataclass:
  - `ad_id: str`
  - `audience: str`
  - `style_results: dict[str, dict]` (style_name → {attribute_pass_pct, coherence_avg, composite_score})
  - `best_style: str`
  - `worst_style: str`
- [ ] `run_style_experiment(ad_id: str, visual_spec: dict, copy: dict, audience: str) -> StyleExperimentResult`
  - Generates the same scene in each style preset
  - Evaluates all via attribute checklist + coherence
  - Ranks by composite score
  - Logs all results to ledger as `StyleExperiment` events
- [ ] `aggregate_style_results(ledger_path: str) -> dict[str, dict[str, float]]`
  - Returns `{audience: {style: avg_composite_score}}` across all experiments
  - Identifies dominant style per audience

#### C. Style-Audience Mapping (`generate/style_library.py`)

- [ ] `StyleAudienceMap` dataclass:
  - `mappings: dict[str, str]` (audience → recommended_style)
  - `confidence: dict[str, float]` (audience → confidence based on sample size)
  - `sample_sizes: dict[str, int]`
- [ ] `build_style_audience_map(ledger_path: str, min_samples: int = 5) -> StyleAudienceMap`
  - Aggregates experiment results into recommended style per audience
  - Low sample sizes flagged as low confidence
- [ ] `get_recommended_style(audience: str, style_map: StyleAudienceMap) -> str`
  - Returns recommended style for audience, falls back to "photorealistic" if insufficient data

#### D. Tests (`tests/test_generation/test_style_experiments.py`)

- [ ] TDD first
- [ ] Test style presets all have required fields
- [ ] Test `apply_style_to_spec()` modifies spec correctly
- [ ] Test `get_styles_for_audience()` returns valid presets
- [ ] Test `StyleExperimentResult` identifies best and worst styles
- [ ] Test `aggregate_style_results()` computes averages correctly
- [ ] Test `build_style_audience_map()` picks highest-scoring style per audience
- [ ] Test low sample size → low confidence flag
- [ ] Test `get_recommended_style()` falls back when no data
- [ ] Minimum: 8+ tests

#### E. Documentation

- [ ] Add P3-04 entry in `docs/DEVLOG.md`
- [ ] Document style-audience mapping findings (can be a section in DEVLOG)

---

## Branch & Merge Workflow

Work on `develop` branch per project convention.

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Style as prompt modifier | Section 4.6 | Style applied via prompt engineering, not post-processing |
| Audience segmentation | P1-03 | Parents vs students have distinct preferences |
| Cost-tier for experiments | P3-01 | Use Nano Banana 2 for style experiments to manage cost |
| Composite scoring | P1-15 | `attribute_pass_pct * 0.4 + coherence_avg * 0.6` |

### Style Hypotheses

| Style | Parents (Hypothesis) | Students (Hypothesis) |
|-------|---------------------|----------------------|
| Photorealistic | Strong — trust/credibility | Moderate |
| Illustrated | Moderate | Strong — modern/engaging |
| Flat design | Weak | Moderate — clean/tech |
| Lifestyle | Strong — aspirational | Strong — relatable |
| Editorial | Moderate | Weak |

### Files to Create

| File | Why |
|------|-----|
| `generate/style_library.py` | Style presets + audience mapping |
| `generate/style_experiments.py` | Experiment runner + aggregation |
| `tests/test_generation/test_style_experiments.py` | Tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `generate/image_generator.py` | How images are generated from visual specs |
| `generate/visual_spec.py` | Visual spec structure to modify |
| `generate/brand_voice.py` | Audience profile patterns |
| `evaluate/image_evaluator.py` | Attribute evaluation |
| `evaluate/coherence_checker.py` | Coherence scoring |

---

## Definition of Done

- [ ] 5 style presets defined with prompt modifiers
- [ ] Style experiments generate + evaluate each style per ad
- [ ] Results aggregated per audience
- [ ] Style-audience mapping built with confidence scores
- [ ] Recommended style retrieval works with fallback
- [ ] Tests pass (8+)
- [ ] Lint clean
- [ ] DEVLOG updated with style-audience findings

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**P3-05 (Multi-model orchestration doc)** documents which model handles which task across all three formats, including the style experiment findings from P3-04.
