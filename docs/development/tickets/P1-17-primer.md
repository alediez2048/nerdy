# P1-17 Primer: Image Targeted Regen Loop

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P1-15 (visual attribute evaluator + Pareto selection), P1-16 (text-image coherence checker) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P1-17 implements the **image targeted regeneration loop** — the feedback mechanism that fires when all 3 image variants fail evaluation. Instead of blindly regenerating, the system diagnoses the weakest attribute or coherence dimension, appends targeted diagnostics to the visual spec, and generates focused regen variants. Total images per ad are capped at 5. If the budget is exhausted without a passing variant, the ad is flagged as "image-blocked" for human review.

### Why It Matters

- **Prevention Over Detection Over Correction** (Pillar 2): Targeted diagnostics prevent repeating the same failure mode
- **Every Token Is an Investment** (Pillar 3): Blind regeneration wastes tokens; diagnostic-guided regen has higher success probability
- The 5-image cap prevents runaway API costs on fundamentally problematic briefs
- "Image-blocked" status provides a clean escalation path rather than silent failure
- Without targeted regen, failed images would require manual intervention or the entire ad gets discarded

---

## What Was Already Done

- P1-15: Visual attribute evaluator identifies which specific attributes failed (age, lighting, diversity, brand, artifacts)
- P1-16: Coherence checker identifies which coherence dimensions are weak (message alignment, audience match, emotional consistency, visual narrative)
- P1-14: Image generation via Nano Banana Pro with visual spec input
- P0-08: Checkpoint-resume ensures regen attempts survive interruptions

---

## What This Ticket Must Accomplish

### Goal

Build the targeted regen loop that diagnoses image failures, generates focused regen variants with diagnostic-enhanced visual specs, and enforces the 5-image budget cap per ad.

### Deliverables Checklist

#### A. Regen Diagnostics (`iterate/image_regen.py`)

- [ ] `diagnose_failure(attribute_results: list, coherence_results: list) -> RegenDiagnostic`
  - When all 3 variants fail attributes: identify the most commonly failed attribute across variants
  - When best variant fails coherence: identify the weakest coherence dimension
  - Returns structured diagnostic with `failure_type`, `weakest_dimension`, and `fix_suggestion`
- [ ] `build_regen_spec(original_spec: dict, diagnostic: RegenDiagnostic) -> dict`
  - Appends diagnostic fix suggestions to the original visual spec
  - For attribute failures: e.g., "no distortions" or "ensure warm lighting"
  - For coherence failures: e.g., "image must directly show [value proposition]"

#### B. Regen Loop Controller (`iterate/image_regen.py`)

- [ ] `run_image_regen(ad_id: str, original_variants: list, diagnostic: RegenDiagnostic, ...) -> RegenResult`
  - When all 3 variants fail: generate 2 regen variants with diagnostic-enhanced spec
  - When best variant fails coherence only: generate 1 regen variant with `fix_suggestion` appended
  - Track total images generated per ad (initial 3 + regen variants)
  - Enforce 5-image cap: `if total_images >= 5: flag as image-blocked`
- [ ] `flag_image_blocked(ad_id: str, diagnostic: RegenDiagnostic, ledger_path: str)`
  - Append `ImageBlocked` event to ledger with full diagnostics
  - Ad proceeds to human review queue

#### C. Budget Tracking

- [ ] `get_image_count(ad_id: str, ledger_path: str) -> int`
  - Count total images generated for this ad from ledger events
- [ ] `can_generate_more(ad_id: str, ledger_path: str, requested: int) -> bool`
  - Returns True if `current_count + requested <= 5`

#### D. Tests (`tests/test_pipeline/test_image_regen.py`)

- [ ] TDD first
- [ ] Test failure diagnosis identifies most common failed attribute
- [ ] Test failure diagnosis identifies weakest coherence dimension
- [ ] Test regen spec includes diagnostic fix suggestions
- [ ] Test 2 regen variants generated on full attribute failure
- [ ] Test 1 regen variant generated on coherence-only failure
- [ ] Test 5-image cap enforced (3 initial + 2 regen = max)
- [ ] Test image-blocked flag set when budget exhausted
- [ ] Test image-blocked event logged with diagnostics
- [ ] Minimum: 8+ tests

#### E. Documentation

- [ ] Add P1-17 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/P1-17-image-regen-loop
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Targeted regen | Section 4.6.6 | Diagnose weakest attribute, append diagnostic, generate focused regen variants |
| 5-image budget | Section 4.6.6 | Cap prevents runaway costs; exhausted budget = human escalation |
| Brief mutation pattern | R1-Q2 | Same philosophy as text brief mutation — targeted fixes, not random retries |
| Confidence-gated autonomy | R2-Q5 | Image-blocked = low confidence = human required |

### Files to Create

| File | Why |
|------|-----|
| `iterate/image_regen.py` | Diagnosis, regen spec building, loop control, budget tracking |
| `tests/test_pipeline/test_image_regen.py` | Regen loop tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| P1-15 image evaluator | Attribute results structure |
| P1-16 coherence checker | Coherence results structure |
| P1-14 image generation module | How to call Nano Banana Pro with modified specs |
| `iterate/` existing regen/mutation modules | Pattern for text-side regen (P1-08) |

---

## Definition of Done

- [ ] Failure diagnosis correctly identifies weakest attribute or coherence dimension
- [ ] Regen visual spec includes targeted fix suggestions
- [ ] 2 regen variants generated on full failure; 1 on coherence-only failure
- [ ] 5-image cap enforced per ad
- [ ] Image-blocked ads flagged with full diagnostics in ledger
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**P1-18 (Full ad assembly + export)** takes the winning image (selected by P1-15's Pareto scorer after P1-16 coherence + P1-17 regen) and assembles it with the published copy into a Meta-ready export package. The image evaluation and regen loop is now complete — every published ad has a verified, coherent winning image.
