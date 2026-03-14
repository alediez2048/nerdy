# P1-16 Primer: Text-Image Coherence Checker

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P1-14 (Nano Banana Pro integration), P1-15 (visual attribute evaluator) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P1-16 implements the **text-image coherence checker** — a multimodal verification step that scores how well each image variant matches its ad copy. Each copy + image pair is evaluated across 4 coherence dimensions. A score below 6 marks the pair as incoherent. The coherence score feeds into Pareto selection at 60% weight (the dominant factor in variant selection).

### Why It Matters

- **Prevention Over Detection Over Correction** (Pillar 2): The shared semantic brief (R1-Q10) prevents incoherence by design, but verification catches what prevention misses
- A beautiful image paired with mismatched copy is worse than no image at all
- Coherence is weighted 60% in the Pareto composite — it is the primary selection signal
- Incoherent-only results (all 3 variants below 6) trigger targeted regen in P1-17, saving token spend on manual re-runs
- Without coherence checking, the pipeline could publish visually strong but semantically disconnected ads

---

## What Was Already Done

- P1-14: 3 image variants generated per ad from shared semantic brief
- P1-15: Visual attribute evaluation with binary checklist (40% of Pareto composite)
- P1-15: Pareto selection framework awaiting coherence scores (60% weight)
- R1-Q10: Architectural decision — shared semantic brief expansion for multi-modal coherence

---

## What This Ticket Must Accomplish

### Goal

Build the multimodal coherence verification system that scores each copy + image pair across 4 dimensions, flags incoherent pairs, and feeds coherence scores into the Pareto selection composite.

### Deliverables Checklist

#### A. Coherence Checker (`evaluate/coherence_checker.py`)

- [ ] `check_coherence(copy: dict, image_path: str) -> CoherenceResult`
  - Multimodal Gemini Flash call: ad copy JSON + image as input
  - 4-dimension coherence scoring (each 1-10):
    - `message_alignment`: Does the image reinforce the ad's core message?
    - `audience_match`: Does the image appeal to the target audience (parents/students)?
    - `emotional_consistency`: Does the image's emotional tone match the copy's tone?
    - `visual_narrative`: Does the image tell a story consistent with the ad's value proposition?
  - Returns per-dimension scores + `coherence_avg` (mean of 4 dimensions)
  - Below 6.0 average = flagged as incoherent
- [ ] `is_incoherent(result: CoherenceResult) -> bool`
  - Returns True if `coherence_avg < 6.0`
- [ ] `all_variants_incoherent(results: list[CoherenceResult]) -> bool`
  - Returns True if every variant in the list is incoherent — triggers targeted regen (P1-17)

#### B. Coherence Integration with Pareto Selection

- [ ] Update P1-15's `select_best_variant()` to consume coherence scores
  - Composite = `(attribute_pass_pct x 0.4) + (coherence_avg x 0.6)`
  - Coherence score normalized to 0-1 range (divide by 10) before weighting
- [ ] `log_coherence_results(results: list[CoherenceResult], ad_id: str, ledger_path: str)`
  - Append `CoherenceEvaluated` event for each variant with all 4 dimension scores

#### C. Tests (`tests/test_pipeline/test_coherence_checker.py`)

- [ ] TDD first
- [ ] Test coherence evaluation returns correct 4-dimension structure
- [ ] Test `coherence_avg` calculation (mean of 4 dimensions)
- [ ] Test incoherence threshold: avg < 6.0 = incoherent
- [ ] Test `all_variants_incoherent` returns True when all fail
- [ ] Test `all_variants_incoherent` returns False when at least one passes
- [ ] Test coherence score feeds correctly into Pareto composite
- [ ] Test normalized coherence (divide by 10) in composite calculation
- [ ] Minimum: 7+ tests

#### D. Documentation

- [ ] Add P1-16 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/P1-16-coherence-checker
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Shared semantic brief | R1-Q10 | Prevention by design — same brief drives both copy and image generation, reducing incoherence structurally |
| 4-dimension coherence | Section 4.6 | Message alignment, audience match, emotional consistency, visual narrative — mirrors text evaluation decomposition |
| 60% coherence weight | Section 4.6 | Coherence matters more than visual attributes alone — a coherent image with minor attribute issues beats an incoherent image that passes all attributes |

### Files to Create

| File | Why |
|------|-----|
| `evaluate/coherence_checker.py` | Multimodal coherence verification |
| `tests/test_pipeline/test_coherence_checker.py` | Coherence evaluation tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| P1-15 image evaluator/selector | How coherence scores integrate into Pareto composite |
| P1-14 image generation module | How variants and visual specs are structured |
| `interviews.md` (R1-Q10) | Shared semantic brief rationale |
| `evaluate/` existing evaluator modules | Pattern for structured evaluation output |

---

## Definition of Done

- [ ] Each copy + image pair scored across 4 coherence dimensions (1-10 each)
- [ ] Coherence average calculated; below 6.0 = incoherent
- [ ] Coherence scores feed into Pareto composite at 60% weight
- [ ] `all_variants_incoherent()` correctly identifies when targeted regen is needed
- [ ] Coherence results logged to ledger for all variants
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**P1-17 (Image targeted regen loop)** handles the case when all variants fail — either all incoherent or all failing attribute checks. It diagnoses the weakest attribute, generates regen variants, and caps total images at 5 per ad. With P1-15 and P1-16 complete, the evaluation side of the image pipeline is done; P1-17 closes the feedback loop.
