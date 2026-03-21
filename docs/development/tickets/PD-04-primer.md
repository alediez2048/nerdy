# PD-04 Primer: Video Evaluation Consolidation

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P3-07+ (Video pipeline + evaluation), P1-08 (Image evaluation), P1-05 (Text evaluation). See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PD-04 consolidates the video evaluation system, which currently has two conflicting implementations: one with real Gemini API calls (`video_evaluator.py`) and one that is entirely placeholder (`video_attributes.py` + `video_coherence.py`). Different callers import from different modules, producing inconsistent results. There is also a composite score normalization bug shared with image evaluation that makes video scores incomparable to text scores.

### Why It Matters

- Two modules define `VideoCoherenceResult` with different field names — importing the wrong one causes silent bugs or crashes
- The placeholder modules return hardcoded `passed=True` / `score=7.0` for every video, meaning any video that goes through `selector.py` always "passes" evaluation
- The normalization bug mixes a 0-1 scale with a 1-10 scale in a weighted sum, producing composite scores in the 0.4-6.4 range instead of the expected 1.0-10.0 range
- Until this is fixed, no video can be meaningfully compared to text ads on quality, and the selector cannot make real quality-based choices

---

## What Was Already Done

- `evaluate/video_evaluator.py` — Real implementation with Gemini multimodal API calls, 5 binary attributes, 80% pass threshold, coherence threshold 4.0
- `evaluate/video_attributes.py` — Placeholder: 10 attributes (5 Required + 5 non-Required), all return `passed=True, confidence=0.9`
- `evaluate/video_coherence.py` — Placeholder: every dimension returns `score=7.0` with "evaluation pending" rationale
- `generate_video/selector.py` — Imports from the placeholder modules (`video_attributes` + `video_coherence`)
- `app/workers/tasks/pipeline_task.py` — Imports from the real module (`video_evaluator`)
- `generate_image/image_selector.py` — Same normalization bug as `selector.py`

---

## What This Ticket Must Accomplish

### Goal

Consolidate video evaluation into a single authoritative module (`video_evaluator.py`), delete the placeholder modules, fix composite score normalization, and update all imports.

### Deliverables Checklist

#### A. Consolidation (`evaluate/video_evaluator.py` — keep and extend)

- [ ] Verify `video_evaluator.py` covers all attributes needed by the pipeline
- [ ] If any attributes from `video_attributes.py` are genuinely useful and missing from `video_evaluator.py`, migrate them
- [ ] Ensure `VideoCoherenceResult` uses a consistent field name (pick `coherence_avg` or `avg_score` and standardize)
- [ ] Ensure coherence threshold is consistent (4.0 in evaluator vs 6.0 in attributes — decide which)

#### B. Delete Placeholders

- [ ] Delete `evaluate/video_attributes.py` (or merge any non-placeholder logic first)
- [ ] Delete `evaluate/video_coherence.py` (or merge any non-placeholder logic first)
- [ ] Verify no other modules import from the deleted files

#### C. Fix Imports (`generate_video/selector.py` — modify)

- [ ] Update `selector.py` to import from `evaluate.video_evaluator` instead of `evaluate.video_attributes` / `evaluate.video_coherence`
- [ ] Update any function calls to match `video_evaluator.py` signatures and return types
- [ ] Verify `pipeline_task.py` imports remain correct (already uses `video_evaluator`)

#### D. Fix Normalization Bug (`generate_video/selector.py` + `generate_image/image_selector.py` — modify)

- [ ] Current formula: `attribute_pass_pct * 0.4 + coherence_avg * 0.6` — mixes 0-1 with 1-10
- [ ] Fix: normalize to common scale. Either `(attribute_pass_pct * 10) * 0.4 + coherence_avg * 0.6` or equivalent
- [ ] Apply same fix to `generate_image/image_selector.py` line 50 (identical bug)
- [ ] Resulting composite scores should be in 1.0-10.0 range, comparable to text evaluation scores

#### E. Tests

- [ ] TDD first: write tests before implementation
- [ ] Test that consolidated evaluator returns correct attribute structure
- [ ] Test composite score normalization produces values in 1.0-10.0 range
- [ ] Test that a perfect evaluation (all pass, coherence 10.0) produces composite ~10.0
- [ ] Test that a failing evaluation (no pass, coherence 1.0) produces composite ~1.0
- [ ] Test that deleted modules are not imported anywhere (import scan)
- [ ] Test image_selector normalization fix matches video selector

#### F. Documentation

- [ ] Add ticket entry in `docs/DEVLOG.md`
- [ ] Update decision log with consolidation rationale and chosen thresholds

---

## Branch & Merge Workflow

Work on `develop` branch per project convention.

---

## Important Context

### Files to Create

None — this ticket consolidates and deletes, it does not add new modules.

### Files to Modify

| File | Action |
|------|--------|
| `evaluate/video_evaluator.py` | Keep as authoritative module; standardize field names |
| `evaluate/video_attributes.py` | Delete after merging any real logic |
| `evaluate/video_coherence.py` | Delete after merging any real logic |
| `generate_video/selector.py` | Update imports + fix normalization bug |
| `generate_image/image_selector.py` | Fix same normalization bug |
| `docs/DEVLOG.md` | Add ticket entry |
| `docs/deliverables/decisionlog.md` | Document consolidation decisions |

### Files You Should NOT Modify

- `app/workers/tasks/pipeline_task.py` — already imports from the correct module
- `evaluate/evaluator.py` — text evaluator, separate concern
- Any `app/api/` or `app/frontend/` code — evaluation is backend-only

### Files You Should READ for Context

| File | Why |
|------|-----|
| `evaluate/video_evaluator.py` | The real implementation to keep — understand its API surface |
| `evaluate/video_attributes.py` | The placeholder to delete — check for any salvageable logic |
| `evaluate/video_coherence.py` | The placeholder to delete — check for any salvageable logic |
| `generate_video/selector.py` | Caller that uses the wrong imports — needs fixing |
| `generate_image/image_selector.py` | Has the same normalization bug — needs identical fix |
| `app/workers/tasks/pipeline_task.py` | Verify which evaluation module the pipeline actually calls |
| `evaluate/evaluator.py` | Text evaluation scoring for comparison — target 1.0-10.0 range |

---

## Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| Keep `video_evaluator.py`, delete placeholders | Real Gemini API calls vs hardcoded `True` — no contest |
| Normalize to 1.0-10.0 scale | Text evaluation uses 1.0-10.0; cross-media comparisons require a common scale |
| Single `VideoCoherenceResult` class | Two classes with the same name and different fields is a bug waiting to happen |
| Fix image_selector in same ticket | Identical bug, same formula, same root cause — fix together |

---

## Suggested Implementation Pattern

```python
# Fix normalization — generate_video/selector.py and generate_image/image_selector.py
# BEFORE (broken):
composite = attribute_pass_pct * 0.4 + coherence_avg * 0.6

# AFTER (fixed — both terms on 1.0-10.0 scale):
composite = (attribute_pass_pct * 10.0) * 0.4 + coherence_avg * 0.6
# Perfect: (1.0 * 10) * 0.4 + 10.0 * 0.6 = 4.0 + 6.0 = 10.0
# Worst:   (0.0 * 10) * 0.4 +  1.0 * 0.6 = 0.0 + 0.6 =  0.6
```

```python
# Fix imports — generate_video/selector.py
# BEFORE:
from evaluate.video_attributes import evaluate_video_attributes
from evaluate.video_coherence import evaluate_video_coherence

# AFTER:
from evaluate.video_evaluator import evaluate_video_attributes, evaluate_video_coherence
```

---

## Edge Cases to Handle

1. `video_evaluator.py` may not export functions with the exact same names as the placeholder modules — check and create wrappers or rename
2. If `video_evaluator.py` coherence threshold (4.0) differs from placeholder (6.0), pick the real one (4.0) and document why
3. Composite score floor: with the fix, minimum is ~0.6 not 1.0 — decide if a floor clamp to 1.0 is needed
4. Existing ledger entries may have scores computed with the old broken formula — do NOT retroactively fix them, but add a comment noting the schema version change
5. Tests that mock the deleted modules will break — find and update them

---

## Definition of Done

- [ ] Only one video evaluation module exists (`evaluate/video_evaluator.py`)
- [ ] `evaluate/video_attributes.py` and `evaluate/video_coherence.py` are deleted
- [ ] `generate_video/selector.py` imports from `evaluate.video_evaluator`
- [ ] Composite score formula produces values in 1.0-10.0 range (or 0.6-10.0, documented)
- [ ] Same normalization fix applied to `generate_image/image_selector.py`
- [ ] No import errors — `python -c "from generate_video.selector import ..."` works
- [ ] Tests pass (`python -m pytest tests/ -v`)
- [ ] Lint clean (`ruff check . --fix`)
- [ ] DEVLOG updated
- [ ] Decision log updated

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Read all three evaluation modules + selector + image_selector | 10 min |
| Write tests (TDD) | 10 min |
| Consolidate evaluator + delete placeholders | 10 min |
| Fix selector imports | 5 min |
| Fix normalization in both selectors | 10 min |
| Verify no broken imports | 5 min |
| DEVLOG + decision log | 5 min |

---

## After This Ticket: What Comes Next

- Video evaluation scores become meaningful, enabling real quality-based selection in the pipeline
- Image composite scores become comparable to text scores, enabling cross-media quality dashboards (P5)
- Future tickets can tune thresholds with confidence that scores are on a consistent 1.0-10.0 scale
