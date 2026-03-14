# P3-10 Primer: Video Pareto Selection + Regen Loop

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P3-08 (video attribute evaluator), P3-09 (script-video coherence checker), P1-17 (image targeted regen loop — pattern to follow) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P3-10 implements **video variant selection and the targeted regen loop**. It selects the best of 2 video variants by composite score, triggers targeted regen on failure (1 retry, max 3 videos total per ad), and implements graceful degradation: if all video attempts fail, the ad publishes with copy + image only.

### Why It Matters

- **Prevention Over Detection Over Correction** (Pillar 2): Targeted regen with diagnostics is more efficient than blind retry
- **The System Knows What It Doesn't Know** (Pillar 4): Graceful degradation means video failure never blocks ad delivery
- Max 3 videos per ad caps cost at ~$2.70 (vs. unlimited regen)
- The image regen loop (P1-17) proved this pattern works — video applies the same architecture with tighter budget

---

## What Was Already Done

- P3-07: Veo integration generates 2 video variants per ad
- P3-08: Video attribute evaluator scores each variant (10 attributes)
- P3-09: Script-video coherence checker scores copy + video pairs (4 dimensions)
- P1-17: Image targeted regen loop (direct pattern to follow — diagnose, append, regen, cap)
- P1-07: Pareto-optimal text selection (composite scoring approach)

---

## What This Ticket Must Accomplish

### Goal

Select the best video variant by composite score, trigger targeted regen on failure, and gracefully degrade to image-only when video generation is exhausted.

### Deliverables Checklist

#### A. Video Selector (`generate_video/selector.py`)

- [ ] `compute_video_composite_score(attribute_result: VideoAttributeResult, coherence_result: VideoCoherenceResult) -> float`
  - Composite = (attribute_pass_pct * 0.4) + (coherence_avg * 0.6)
  - Mirrors image composite scoring from P1-15
- [ ] `select_best_video(variants: list[VideoVariant]) -> VideoVariant | None`
  - Ranks variants by composite score
  - Returns best variant if it passes all Required attributes AND coherence >= 6
  - Returns None if no variant passes (triggers regen or degradation)

#### B. Video Regen Loop (`generate_video/regen.py`)

- [ ] `diagnose_video_failure(attribute_result: VideoAttributeResult, coherence_result: VideoCoherenceResult) -> VideoDiagnostic`
  - Identifies weakest attribute or lowest coherence dimension
  - Produces diagnostic context for targeted regen prompt
- [ ] `regenerate_video(ad_id: str, video_spec: VideoSpec, diagnostic: VideoDiagnostic) -> VideoVariant`
  - Appends diagnostic to video spec (e.g., "ensure hook appears in first 1 second")
  - Generates 1 regen variant
  - Logs regen attempt to ledger
- [ ] Budget enforcement: max 3 videos total per ad (2 initial + 1 regen)
- [ ] On budget exhaustion: return None (triggers graceful degradation)

#### C. Graceful Degradation (`generate_video/degradation.py`)

- [ ] `handle_video_failure(ad_id: str) -> DegradationResult`
  - Logs "video-blocked" status to ledger with diagnostics
  - Returns DegradationResult indicating ad should publish with copy + image only
  - Does NOT raise exceptions — video failure is a recoverable state
- [ ] Degradation events include: reason, failed variant count, diagnostic summary

#### D. Tests (`tests/test_pipeline/test_video_selection.py`)

- [ ] TDD first
- [ ] Test composite score calculation weights correctly (0.4 attribute + 0.6 coherence)
- [ ] Test best variant selected when both pass
- [ ] Test best variant selected when only one passes
- [ ] Test None returned when no variant passes
- [ ] Test regen triggers on failure with correct diagnostic
- [ ] Test budget cap: max 3 videos total per ad
- [ ] Test graceful degradation logs video-blocked status
- [ ] Test degradation result indicates image-only fallback
- [ ] Minimum: 8+ tests

#### E. Documentation

- [ ] Add P3-10 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/P3-10-video-pareto-regen
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Composite scoring | Section 4.9, P1-15 | Same weighting as image: 40% attribute pass rate + 60% coherence average |
| Targeted regen | R1-Q2, Section 4.9 | Diagnose weakest dimension, append fix to spec, regen. Not blind retry. |
| Max 3 videos per ad | Section 4.9 | 2 initial + 1 regen. Caps cost at ~$2.70/ad for video. |
| Graceful degradation | Section 4.9 | Video failure never blocks ad. Falls back to copy + image only. |

### Files to Create

| File | Why |
|------|-----|
| `generate_video/selector.py` | Composite scoring and variant selection |
| `generate_video/regen.py` | Targeted regen with diagnostics |
| `generate_video/degradation.py` | Graceful degradation to image-only |
| `tests/test_pipeline/test_video_selection.py` | Selection, regen, and degradation tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| P1-17 image regen loop | Direct pattern to follow (diagnose → append → regen → cap) |
| P1-15 image Pareto selection | Composite scoring approach |
| P3-08 video attribute evaluator | Attribute results format |
| P3-09 video coherence checker | Coherence results format |

---

## Definition of Done

- [ ] Best video variant selected by composite score
- [ ] Targeted regen triggers on failure with diagnostic context
- [ ] Budget cap enforced: max 3 videos per ad
- [ ] Graceful degradation: video-blocked ads fall back to image-only
- [ ] All events logged to ledger (selection, regen, degradation)
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**P3-11 (Three-format ad assembly)** extends P1-18 to include the winning video alongside copy and image in the published ad output.
