# P1-04 Primer: Chain-of-Thought Evaluator

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P0-06 (evaluator calibration) must be complete — `evaluate/evaluator.py` already exists with `evaluate_ad()` and `EvaluationResult`. P1-01 (brief expansion), P1-02 (ad generator), P1-03 (brand voice profiles) should be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P1-04 extends the existing evaluator (`evaluate/evaluator.py`) with the **full production chain-of-thought evaluation prompt** (R3-Q6) and **contrastive rationale generation** (R3-Q10). The P0-06 evaluator established calibration and the basic `evaluate_ad()` / `EvaluationResult` interface. This ticket replaces the calibration prompt with the 5-step CoT prompt that forces the LLM to decompose the ad before scoring, generates contrastive rationales ("what the ad is, what +2 would look like, the specific gap"), and flags low-confidence dimensions.

### Why It Matters

- **Visible Reasoning Is a First-Class Output** (Pillar 7): Contrastive rationales are the highest-ROI decision from the architectural interviews (R3-Q10). They tell the generator exactly what to fix, not just what's wrong.
- **Quality Measurement & Evaluation** is 25% of the rubric. The evaluator's prompt design is one of the five load-bearing components of the entire system.
- Chain-of-thought structured evaluation (R3-Q6) reduces halo effect — the LLM must identify structural elements before scoring, preventing "this feels like a 7" holistic judgments.
- Confidence flags feed into confidence-gated autonomy (R2-Q5) — dimensions with low evaluator confidence get flagged for human review rather than trusted blindly.

---

## What Was Already Done

- P0-06: Evaluator calibration (`evaluate/evaluator.py`) — `evaluate_ad()` function and `EvaluationResult` dataclass exist and are tested. The evaluator was calibrated against labeled reference ads to be within +/-1.0 of human labels on 80%+ of cases.
- P0-05: Reference ads (`data/reference_ads.json`) — 42 real ads with baseline scores used for calibration
- P0-08: Retry infrastructure (`iterate/retry.py`) — `retry_with_backoff()` for resilient API calls
- P0-02: Decision ledger (`iterate/ledger.py`) — `log_event()` for tracking evaluation events
- P1-03: Brand voice profiles (`generate/brand_voice.py`) — `get_voice_for_evaluation()` provides audience-specific Brand Voice rubric
- P0-01: Config (`data/config.yaml`) — model parameters, evaluation settings

---

## What This Ticket Must Accomplish

### Goal

Extend the existing evaluator with the full production CoT prompt that forces structured decomposition before scoring, produces contrastive rationales for every dimension, and flags low-confidence scores. The existing `evaluate_ad()` interface and `EvaluationResult` dataclass must be preserved or extended (not broken).

### Deliverables Checklist

#### A. Extend Evaluator (`evaluate/evaluator.py`)

- [ ] Replace/extend the evaluation prompt with the 5-step CoT sequence (R3-Q6):
  1. **Read the ad** — full text of primary_text, headline, description, cta_button
  2. **Identify structural elements** — extract the hook, value proposition, CTA, and emotional angle BEFORE scoring (forced decomposition)
  3. **Compare against calibration rubric** — for each dimension, reference the 1-score and 10-score anchors from the rubric
  4. **Score with contrastive rationale** (R3-Q10) — for each dimension: current score, what a +2 version would look like, the specific gap between current and +2
  5. **Flag low confidence** — for each dimension, output confidence (1-10); flag dimensions where confidence < 7 (feeds R2-Q5 confidence-gated autonomy)
- [ ] Extend or replace `EvaluationResult` dataclass to include:
  - `scores`: dict of dimension -> float (existing)
  - `rationales`: dict of dimension -> `DimensionRationale` (NEW)
  - `structural_elements`: dict with identified hook, value_prop, cta, emotional_angle (NEW)
  - `confidence_flags`: dict of dimension -> float, with flagged dimensions where confidence < 7 (NEW)
  - `weighted_average`: float (existing, now computed by P1-05 weighting)
  - `metadata`: model used, token count, timestamp (existing or extend)
- [ ] `DimensionRationale` dataclass (NEW):
  - `current_assessment`: what the ad does for this dimension
  - `score`: float (1-10)
  - `plus_two_description`: what a version scoring +2 higher would look like
  - `specific_gap`: the concrete gap between current and +2
  - `confidence`: float (1-10)
- [ ] `_build_evaluation_prompt(ad: GeneratedAd, audience: str) -> str`
  - Constructs the full 5-step CoT prompt
  - Includes audience-specific Brand Voice rubric from `get_voice_for_evaluation(audience)`
  - Includes calibration anchors (1-score and 10-score examples per dimension)
  - Requests structured JSON output
- [ ] `_parse_evaluation_response(response: str) -> EvaluationResult`
  - Parses the structured JSON response
  - Extracts per-dimension scores, rationales, confidence flags
  - Validates score ranges (1-10), flags parsing issues
  - Falls back gracefully if response is malformed (scores only, no rationales, with warning)
- [ ] Maintain backward compatibility: existing tests from P0-06 should still pass (or be updated to match the extended interface)

#### B. Tests (`tests/test_evaluation/test_evaluator.py` — extend existing)

- [ ] TDD first for new functionality
- [ ] Test CoT evaluation produces all 5 dimension scores
- [ ] Test each dimension has a contrastive rationale (current, +2 description, gap)
- [ ] Test confidence flags are present for all dimensions
- [ ] Test low-confidence dimensions (confidence < 7) are identified
- [ ] Test structural elements (hook, VP, CTA, emotional angle) are extracted
- [ ] Test malformed API response falls back to scores-only gracefully
- [ ] Test audience-specific voice rubric is included in the prompt
- [ ] Test score validation (reject scores outside 1-10 range)
- [ ] Existing P0-06 calibration tests remain passing
- [ ] Minimum: 8+ new tests (plus existing tests passing)

#### C. Integration

- [ ] Ensure evaluator output is compatible with P1-05 weighting module (scores dict)
- [ ] Ensure rationales are logged to decision ledger via `log_event()` (for the narrated replay in P4-07)
- [ ] Wire `get_voice_for_evaluation()` from `generate/brand_voice.py` (P1-03) into the evaluation prompt

#### D. Documentation

- [ ] Add P1-04 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

All work is done directly on `develop`. No feature branches.

```bash
git switch develop && git pull
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Chain-of-thought structured evaluation | R3-Q6 | Single call, strict 5-step sequence. Forced decomposition reduces halo effect. Achieves dimension isolation at single-call cost. |
| Contrastive rationale generation | R3-Q10 | Not just "why X scored Y" but "what a +2 version would look like" with specific gap identification. Highest ROI decision from interviews. |
| Confidence-gated autonomy | R2-Q5 | Dimensions with confidence < 7 are flagged. System trusts high-confidence scores autonomously; low-confidence scores trigger review. |
| Audience-specific Brand Voice rubric | R1-Q6 | Brand Voice scored against audience-specific criteria, not a generic voice rubric. |

### Files to Modify

| File | Why |
|------|-----|
| `evaluate/evaluator.py` | Extend with CoT prompt, contrastive rationales, confidence flags |
| `tests/test_evaluation/test_evaluator.py` | Add new tests for CoT evaluation (keep existing tests passing) |

### Files to Create

| File | Why |
|------|-----|
| None | This ticket modifies existing files only |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `evaluate/evaluator.py` | The existing evaluator you are extending — understand current interface before modifying |
| `generate/brand_voice.py` | `get_voice_for_evaluation()` — audience-specific rubric for Brand Voice dimension |
| `data/reference_ads.json` | Calibration anchors — 1-score and 10-score examples per dimension |
| `iterate/retry.py` | `retry_with_backoff()` for resilient Gemini calls |
| `iterate/ledger.py` | `log_event()` for logging evaluation events with rationales |
| `data/config.yaml` | Model selection, evaluation parameters |
| `docs/reference/prd.md` (R3-Q6, R3-Q10, R2-Q5, Section 5.3) | Full CoT prompt design, contrastive rationale spec, confidence gating |

---

## Definition of Done

- [ ] 5-step CoT evaluation prompt replaces/extends the P0-06 prompt
- [ ] Every dimension has a contrastive rationale (current assessment, +2 description, specific gap)
- [ ] Confidence flags present for all dimensions; low-confidence (< 7) dimensions identified
- [ ] Structural elements (hook, VP, CTA, emotional angle) extracted before scoring
- [ ] Audience-specific Brand Voice rubric integrated via `get_voice_for_evaluation()`
- [ ] Existing P0-06 tests still pass (backward compatibility)
- [ ] New tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Committed on `develop`

---

## Estimated Time: 60–90 minutes

---

## After This Ticket: What Comes Next

**P1-05 (Campaign-goal-adaptive weighting)** takes the per-dimension scores from this evaluator and applies campaign-specific weights with floor constraints to produce the final weighted average and pass/reject decision.

**P1-06 (Tiered model routing)** uses the evaluator's scores to route ads: < 5.5 discarded, > 7.0 published, 5.5-7.0 escalated to Pro for regeneration.

**P1-07 (Pareto-optimal regeneration)** uses the contrastive rationales to guide targeted regeneration — the "+2 description" tells the generator exactly what to improve.

The contrastive rationales are also critical for **P4-07 (Narrated pipeline replay)** — they power the reasoning trace in the demo.
