# P3-02 Primer: Single-Variable A/B Variants — Copy

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P1-06 (ad generator), P1-07 (Pareto selection), P3-01 (cost-tier model) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P3-02 implements **single-variable A/B variant generation for ad copy**. For each ad, the pipeline produces a control copy plus 3 variants, each changing exactly **one element** (hook type, emotional angle, or CTA). This enables structured learning about which copy elements drive performance per audience segment.

### Why It Matters

- **Learning Is Structural** (Pillar 6): Single-variable isolation means we learn *why* a variant wins, not just *that* it won
- Each variant is a learning investment, not a lottery ticket (R2-Q6)
- Winning patterns identified per segment feed back into future generation
- 4 copies per ad (1 control + 3 variants) with only one element changed → causal attribution

---

## What Was Already Done

- P1-06: Ad generator (`generate/ad_generator.py`) — generates ad copy from expanded brief
- P1-07: Pareto selection (`iterate/pareto_selection.py`) — multi-objective selection
- P1-05: Evaluator (`evaluate/evaluator.py`) — 5-dimension scoring
- P1-03: Brand voice profiles (`generate/brand_voice.py`) — audience-specific voice
- P3-01: Cost-tier model routing — makes variant volume affordable

---

## What This Ticket Must Accomplish

### Goal

Generate 1 control + 3 single-variable copy variants per ad, score all 4, and identify winning patterns per audience segment.

### Deliverables Checklist

#### A. Variant Generator (`generate/ab_variants.py` — new)

- [ ] `VARIANT_ELEMENTS = ("hook_type", "emotional_angle", "cta_style")` — the three elements that can be varied
- [ ] `CopyVariant` dataclass:
  - `ad_id: str`
  - `variant_id: str` (e.g., "control", "hook_variant", "emotion_variant", "cta_variant")
  - `varied_element: str | None` (None for control)
  - `original_value: str` (element value in control)
  - `variant_value: str` (element value in this variant)
  - `copy: dict` (the generated ad copy — headline, primary_text, description)
- [ ] `generate_copy_variants(ad_id: str, expanded_brief: dict, control_copy: dict) -> list[CopyVariant]`
  - Takes the control copy and produces 3 variants
  - Hook variant: changes hook type (question → statistic → story → command)
  - Emotion variant: changes emotional angle (aspiration → urgency → empathy → confidence)
  - CTA variant: changes CTA style (direct → soft → scarcity → social-proof)
  - Each variant preserves all other elements from control
- [ ] `get_element_alternatives(element: str, current_value: str) -> str`
  - Returns a different value for the specified element
  - Deterministic given seed

#### B. Variant Scoring & Comparison (`generate/ab_variants.py` — same file)

- [ ] `VariantComparison` dataclass:
  - `ad_id: str`
  - `control_scores: dict`
  - `variant_scores: dict[str, dict]` (variant_id → dimension scores)
  - `winner: str` (variant_id with highest weighted average)
  - `winning_element: str | None` (which element change won, None if control wins)
  - `lift: float` (winner score - control score)
- [ ] `compare_variants(control: CopyVariant, variants: list[CopyVariant], scores: dict[str, dict]) -> VariantComparison`
  - Compares each variant's scores against control
  - Identifies winner and the element that caused the lift

#### C. Segment Pattern Tracker (`generate/ab_variants.py` — same file)

- [ ] `track_variant_win(comparison: VariantComparison, audience: str, ledger_path: str) -> None`
  - Logs `VariantWin` event to ledger with audience, winning_element, lift
- [ ] `get_segment_patterns(ledger_path: str) -> dict[str, dict[str, float]]`
  - Returns `{audience: {element: win_rate}}` — e.g., `{"parents": {"hook_type": 0.6, "cta_style": 0.3, "emotional_angle": 0.1}}`
  - Enables future briefs to prioritize high-performing elements per audience

#### D. Tests (`tests/test_generation/test_ab_copy_variants.py`)

- [ ] TDD first
- [ ] Test control copy is preserved unchanged
- [ ] Test each variant changes exactly one element
- [ ] Test variant_id naming is consistent
- [ ] Test `compare_variants()` identifies correct winner
- [ ] Test lift calculation is accurate
- [ ] Test `track_variant_win()` logs correct event to ledger
- [ ] Test `get_segment_patterns()` aggregates win rates correctly
- [ ] Test element alternatives are distinct from current value
- [ ] Minimum: 8+ tests

#### E. Documentation

- [ ] Add P3-02 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

Work on `develop` branch per project convention.

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Single-variable isolation | R2-Q6 | Change one element at a time → causal attribution of what works |
| Learning is structural | Pillar 6 | Win patterns feed back into generation — the system improves structurally |
| Per-segment tracking | R2-Q6 | Parents and students respond differently — track separately |

### Variant Elements

| Element | Control | Alternatives |
|---------|---------|-------------|
| Hook type | question | statistic, story, command |
| Emotional angle | aspiration | urgency, empathy, confidence |
| CTA style | direct | soft, scarcity, social-proof |

### Files to Create

| File | Why |
|------|-----|
| `generate/ab_variants.py` | Variant generation + comparison + tracking |
| `tests/test_generation/test_ab_copy_variants.py` | Tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `generate/ad_generator.py` | How control copy is generated |
| `generate/brand_voice.py` | Audience-specific voice profiles |
| `evaluate/evaluator.py` | How copies are scored |
| `iterate/pareto_selection.py` | Multi-objective selection pattern |

---

## Definition of Done

- [ ] Control + 3 variants generated per ad
- [ ] Each variant changes exactly one element
- [ ] Variants scored and compared against control
- [ ] Winner and winning element identified with lift
- [ ] Win patterns tracked per audience segment
- [ ] Tests pass (8+)
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**P3-03 (Single-variable A/B variants — image)** applies the same single-variable isolation to images, holding copy constant and varying visual elements. P3-02's variant comparison framework is reused.
