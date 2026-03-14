# P2-03 Primer: Adversarial Boundary Tests

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P2-01 (inversion tests), P2-02 (correlation analysis), P1-04 (CoT evaluator) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P2-03 implements **adversarial boundary tests** — hand-crafted edge cases that probe whether the evaluator can correctly identify dimension-specific failures in extreme scenarios. These aren't natural ads; they're designed to stress-test dimension boundaries. Examples: perfect clarity but completely wrong brand voice, pure emotional manipulation with zero substance, technical jargon with no CTA.

### Why It Matters

- **Prevention Over Detection Over Correction** (Pillar 2): Adversarial tests catch evaluator blind spots before production ads exploit them
- R2-Q3 recommends adversarial boundary tests alongside inversion and correlation analysis
- If the evaluator can't identify "fast food brand voice" as failing Brand Voice, targeted regen (P1-08) will give wrong guidance
- Edge cases reveal where the CoT evaluation prompt needs more specific rubric anchors
- These tests become a regression gate — future evaluator prompt changes must pass them

---

## What Was Already Done

- P2-01: Inversion tests proved dimensions are causally independent
- P2-02: Correlation analysis showed dimensions are statistically independent
- P1-04: CoT evaluator with 5-step structured evaluation and contrastive rationales
- P1-05: Floor constraints (Clarity ≥ 6.0, Brand Voice ≥ 5.0)
- P0-07: Golden set regression tests with 18 human-scored ads

---

## What This Ticket Must Accomplish

### Goal

Create adversarial ad texts that exploit dimension boundaries and verify the evaluator correctly identifies the specific dimension failures. 8+ adversarial tests.

### Deliverables Checklist

#### A. Adversarial Test Data (`tests/test_data/adversarial_ads.json`)

- [ ] Hand-craft 8+ adversarial ads, each designed to probe a specific boundary:

1. **Wrong Brand Voice:** Fast-food urgency style. "🍔 HUNGRY FOR SCORES? MEGA SAT DEAL! Two-for-one tutoring sessions! Rush in NOW before seats run out!!!" → Brand Voice ≤ 3.0, others may be moderate
2. **High Clarity, Zero Emotion:** Purely factual. "SAT prep tutoring. 1-on-1 sessions. Online scheduling available. Visit website." → Clarity ≥ 7.0, Emotional Resonance ≤ 4.0
3. **Pure Emotional Manipulation:** All feelings, no substance. "Every parent dreams of their child's success. That magical moment when they hold their acceptance letter, tears of joy streaming down..." → Emotional Resonance may be high, Value Proposition ≤ 3.0
4. **Perfect Structure, Wrong Brand:** Competitor branding. "Princeton Review's expert tutors guarantee 200+ point improvement. Our proven Kaplan-style methodology..." → CTA and structure fine, Brand Voice ≤ 3.0
5. **Aggressive CTA, No Value:** Hard sell with no substance. "SIGN UP NOW! DON'T WAIT! LIMITED SPOTS! ACT TODAY! CLICK HERE! ENROLL IMMEDIATELY!" → CTA structure present, Value Proposition ≤ 3.0, Clarity ≤ 4.0
6. **Technical Jargon Overload:** "Leveraging proprietary metacognitive scaffolding algorithms, our pedagogical framework optimizes neuroplasticity-driven retention curves..." → Clarity ≤ 4.0, may score on VP if evaluator is fooled by complexity
7. **Compliance Violation:** "Guaranteed 1600 SAT score or 100% money back! Every student passes — we've never failed!" → Should fail compliance; scores irrelevant if compliance works
8. **Empty/Minimal Ad:** "Tutoring." → All dimensions low (≤ 4.0)

- [ ] Each entry includes: `ad_text`, `expected_failures` (list of dimensions expected ≤ threshold), `expected_passes` (dimensions expected to be fine), `boundary_being_tested`

#### B. Adversarial Test Suite (`tests/test_evaluation/test_adversarial.py`)

- [ ] `test_wrong_brand_voice_scores_low_brand`: Brand Voice ≤ 3.0
- [ ] `test_high_clarity_zero_emotion`: Clarity ≥ 7.0, Emotional Resonance ≤ 4.0
- [ ] `test_pure_manipulation_low_value_prop`: Value Proposition ≤ 3.0
- [ ] `test_competitor_branding_fails_brand_voice`: Brand Voice ≤ 3.0
- [ ] `test_aggressive_cta_no_value`: Value Proposition ≤ 3.0
- [ ] `test_jargon_overload_low_clarity`: Clarity ≤ 4.0
- [ ] `test_empty_ad_all_dimensions_low`: All dimensions ≤ 4.0
- [ ] `test_adversarial_ads_dont_pass_threshold`: None of the adversarial ads should pass the 7.0 threshold
- [ ] Minimum: 8+ tests

#### C. Documentation

- [ ] Add P2-03 entry in `docs/DEVLOG.md`
- [ ] Document any adversarial cases the evaluator gets wrong — these inform prompt improvements

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Adversarial boundary tests | R2-Q3 (Option B) | Edge cases that probe each dimension's independence |
| CoT decomposition | R3-Q6 | 5-step evaluation should prevent halo even on adversarial inputs |
| Contrastive rationales | R3-Q10 | "+2 version" should give specific fixes for adversarial failures |

### Key Thresholds

```python
# From evaluate/dimensions.py
QUALITY_THRESHOLD = 7.0    # Weighted average to publish
CLARITY_FLOOR = 6.0        # Hard floor
BRAND_VOICE_FLOOR = 5.0    # Hard floor

# Adversarial tests use more extreme thresholds:
# "Low" dimension score: ≤ 3.0 or ≤ 4.0 (clearly failing)
# "High" dimension score: ≥ 7.0 (clearly passing)
```

### Testing Approach

These tests call the real Gemini API — NOT mocked. The goal is to verify real evaluator behavior on adversarial inputs. Tests should:
- Use `@pytest.mark.skipif` if `GEMINI_API_KEY` is not set
- Allow reasonable tolerance (±1.0) since LLM scoring has variance
- Focus on extreme cases where the expected direction is clear
- Log actual scores for any failures so we can improve the evaluation prompt

### Files to Create

| File | Why |
|------|-----|
| `tests/test_data/adversarial_ads.json` | Adversarial test data |
| `tests/test_evaluation/test_adversarial.py` | Adversarial test suite |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `evaluate/evaluator.py` | `evaluate_ad()` signature and EvaluationResult |
| `evaluate/dimensions.py` | Dimension names, floors, thresholds |
| `tests/test_evaluation/test_golden_set.py` | Existing test patterns |
| `tests/test_data/golden_ads.json` | For contrast with adversarial ads |

---

## Definition of Done

- [ ] 8+ adversarial ads in `tests/test_data/adversarial_ads.json`
- [ ] 8+ adversarial tests passing
- [ ] Each adversarial ad correctly identified as failing its target dimension
- [ ] No adversarial ad passes the 7.0 quality threshold
- [ ] Any evaluator blind spots documented with proposed prompt fixes
- [ ] Lint clean
- [ ] DEVLOG updated

---

## After This Ticket: What Comes Next

**P2-04 (SPC Drift Detection)** shifts from proving the evaluator works today to ensuring it continues working over time. SPC monitoring catches silent evaluator drift before it corrupts the quality ratchet.
