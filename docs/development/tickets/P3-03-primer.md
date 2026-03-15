# P3-03 Primer: Single-Variable A/B Variants — Image

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P1-14 (image generator), P1-15 (image evaluator), P3-01 (cost-tier model), P3-02 (copy A/B variants) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P3-03 implements **single-variable A/B variant generation for images**. For each ad, the pipeline holds copy constant and generates 3 image variants, each changing exactly **one visual element** (composition, color palette, or subject framing). This isolates visual impact independently from messaging.

### Why It Matters

- **Learning Is Structural** (Pillar 6): Isolating visual variables reveals which visual elements drive engagement per audience
- Same copy + different images → pure visual A/B testing
- Combined with P3-02 copy variants, enables full factorial learning (copy × image)
- Coherence comparison across image variants validates which visuals best reinforce the message

---

## What Was Already Done

- P1-14: Image generator (`generate/image_generator.py`) — 3 variants per ad (anchor, tone_shift, composition_shift)
- P1-15: Image evaluator (`evaluate/image_evaluator.py`) — 5-attribute checklist, 80% pass threshold
- P1-16: Coherence checker (`evaluate/coherence_checker.py`) — text-image coherence, 4 dimensions
- P3-01: Cost-tier model routing — Nano Banana 2 for variant volume
- P3-02: Copy A/B variants — single-variable framework to mirror

---

## What This Ticket Must Accomplish

### Goal

Hold copy constant. Generate 1 control image + 3 single-variable image variants per ad. Evaluate all 4 on attributes and coherence. Identify winning visual patterns per audience.

### Deliverables Checklist

#### A. Image Variant Generator (`generate/ab_image_variants.py` — new)

- [ ] `IMAGE_VARIANT_ELEMENTS = ("composition", "color_palette", "subject_framing")` — the three visual elements that can be varied
- [ ] `ImageVariant` dataclass:
  - `ad_id: str`
  - `variant_id: str` (e.g., "control", "composition_variant", "color_variant", "framing_variant")
  - `varied_element: str | None` (None for control)
  - `original_value: str`
  - `variant_value: str`
  - `visual_spec: dict` (the modified visual spec used for generation)
  - `image_path: str | None` (populated after generation)
- [ ] `generate_image_variants(ad_id: str, visual_spec: dict, copy: dict) -> list[ImageVariant]`
  - Takes the control visual spec and produces 3 variant specs
  - Composition variant: changes layout (centered → rule-of-thirds → diagonal → wide)
  - Color palette variant: changes palette (warm → cool → muted → vibrant)
  - Subject framing variant: changes framing (close-up → medium → wide → environmental)
  - Each variant preserves all other spec elements
- [ ] `get_visual_alternatives(element: str, current_value: str) -> str`
  - Returns a different value for the specified visual element

#### B. Image Variant Evaluation (`generate/ab_image_variants.py`)

- [ ] `ImageVariantComparison` dataclass:
  - `ad_id: str`
  - `control_attributes: dict` (attribute pass results)
  - `control_coherence: float`
  - `variant_results: dict[str, dict]` (variant_id → {attributes, coherence, composite})
  - `winner: str`
  - `winning_element: str | None`
  - `coherence_lift: float`
- [ ] `compare_image_variants(control: ImageVariant, variants: list[ImageVariant], attribute_results: dict, coherence_results: dict) -> ImageVariantComparison`
  - Uses composite scoring: `attribute_pass_pct * 0.4 + coherence_avg * 0.6` (same as P1-15)
  - Identifies winner and which visual element drove the improvement

#### C. Visual Pattern Tracker (`generate/ab_image_variants.py`)

- [ ] `track_image_variant_win(comparison: ImageVariantComparison, audience: str, ledger_path: str) -> None`
  - Logs `ImageVariantWin` event to ledger
- [ ] `get_visual_patterns(ledger_path: str) -> dict[str, dict[str, float]]`
  - Returns `{audience: {element: win_rate}}` per visual element per audience
  - Enables future visual specs to prioritize winning elements

#### D. Tests (`tests/test_generation/test_ab_image_variants.py`)

- [ ] TDD first
- [ ] Test control visual spec is preserved unchanged
- [ ] Test each image variant changes exactly one visual element
- [ ] Test variant_id naming is consistent
- [ ] Test `compare_image_variants()` identifies correct winner by composite score
- [ ] Test coherence lift calculation
- [ ] Test `track_image_variant_win()` logs correct event
- [ ] Test `get_visual_patterns()` aggregates per audience
- [ ] Test visual alternatives are distinct from current value
- [ ] Minimum: 8+ tests

#### E. Documentation

- [ ] Add P3-03 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

Work on `develop` branch per project convention.

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Single-variable isolation | R2-Q6 | One visual change at a time → causal attribution |
| Copy held constant | PRD P3-03 | Isolates visual impact from messaging impact |
| Same evaluation pipeline | P1-15, P1-16 | Attribute + coherence evaluation applied to all variants equally |
| Composite scoring | P1-15 | `attribute_pass_pct * 0.4 + coherence_avg * 0.6` |

### Visual Elements

| Element | Control | Alternatives |
|---------|---------|-------------|
| Composition | centered | rule-of-thirds, diagonal, wide |
| Color palette | warm | cool, muted, vibrant |
| Subject framing | close-up | medium, wide, environmental |

### Files to Create

| File | Why |
|------|-----|
| `generate/ab_image_variants.py` | Image variant generation + comparison + tracking |
| `tests/test_generation/test_ab_image_variants.py` | Tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `generate/image_generator.py` | How images are generated |
| `generate/visual_spec.py` | Visual spec structure |
| `evaluate/image_evaluator.py` | Attribute evaluation |
| `evaluate/coherence_checker.py` | Coherence scoring |
| `evaluate/image_selector.py` | Composite scoring formula |
| `generate/ab_variants.py` | P3-02 copy variant pattern to mirror |

---

## Definition of Done

- [ ] Control + 3 image variants generated per ad
- [ ] Each variant changes exactly one visual element
- [ ] All variants evaluated on attributes + coherence
- [ ] Winner identified by composite score
- [ ] Visual patterns tracked per audience
- [ ] Tests pass (8+)
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**P3-04 (Image style transfer experiments)** explores audience-specific visual styles, building on the visual pattern data from P3-03 to inform which styles work for parents vs students.
