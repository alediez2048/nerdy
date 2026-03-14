# P3-09 Primer: Script-Video Coherence Checker

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P3-08 (video attribute evaluator), P1-16 (text-image coherence checker — pattern to follow) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P3-09 builds the **script-video coherence checker** — a multimodal evaluation that takes ad copy + video and scores coherence across 4 dimensions. This is the video equivalent of P1-16 (text-image coherence checker). A score below 6 on any dimension marks the pair as incoherent and triggers targeted regen.

### Why It Matters

- **Decomposition Is the Architecture** (Pillar 1): Separating attribute evaluation (P3-08) from coherence checking ensures each concern is independently measurable
- A technically perfect video that contradicts the ad copy is worse than no video at all
- The 4 coherence dimensions provide actionable diagnostics for targeted regen (P3-10)
- Section 4.9.5 of the PRD defines the coherence verification spec

---

## What Was Already Done

- P1-16: Text-image coherence checker (direct pattern to follow — same 4-dimension approach)
- P3-07: Veo integration generates video variants
- P3-08: Video attribute evaluator confirms videos are technically sound
- P1-04: Chain-of-thought evaluator (scoring methodology reference)

---

## What This Ticket Must Accomplish

### Goal

Build a multimodal coherence checker that scores ad copy + video pairs across 4 dimensions, flagging incoherent pairs for targeted regen.

### Deliverables Checklist

#### A. Script-Video Coherence Checker (`evaluate/video_coherence.py`)

- [ ] `check_video_coherence(ad_copy: dict, video_path: str, video_spec: VideoSpec) -> VideoCoherenceResult`
  - Sends ad copy + video key frames + video spec to Gemini Flash (multimodal)
  - Scores 4 coherence dimensions (each 1-10):
    1. **Message Alignment** — Does the video reinforce the ad copy's core message?
    2. **Audience Match** — Does the video's subject/setting match the target audience?
    3. **Emotional Consistency** — Does the video's mood match the copy's emotional register?
    4. **Narrative Flow** — Does the video's pacing/story complement the copy's structure?
  - Each dimension: numeric score (1-10) + rationale
  - Below 6 on ANY dimension = incoherent
  - Returns structured result with per-dimension scores and overall coherence flag
- [ ] `is_coherent(result: VideoCoherenceResult) -> bool`
  - Returns True only if all 4 dimensions score >= 6
- [ ] Diagnostic output: on incoherence, identify which dimension(s) failed and why — feeds P3-10 targeted regen

#### B. Tests (`tests/test_pipeline/test_video_coherence.py`)

- [ ] TDD first
- [ ] Test coherent pair scores >= 6 on all dimensions (mock Gemini response)
- [ ] Test incoherent pair flags correctly when one dimension < 6
- [ ] Test incoherent pair flags correctly when multiple dimensions < 6
- [ ] Test diagnostic output identifies failing dimensions with rationale
- [ ] Test results logged to ledger with ad_id, variant_id, per-dimension scores
- [ ] Test `is_coherent()` returns correct boolean for edge cases (exactly 6.0)
- [ ] Test coherence check uses same frame extraction as P3-08
- [ ] Minimum: 7+ tests

#### C. Documentation

- [ ] Add P3-09 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/P3-09-video-coherence-checker
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| 4-dimension coherence | Section 4.9.5 | Same structure as text-image coherence (P1-16) — message alignment, audience match, emotional consistency, narrative flow |
| Below 6 = incoherent | Section 4.9.5 | Consistent threshold with image coherence checker |
| Targeted regen on failure | Section 4.9.5 | Incoherent pairs trigger regen with diagnostic context, not blind retry |

### Files to Create

| File | Why |
|------|-----|
| `evaluate/video_coherence.py` | Script-video coherence checker (4 dimensions) |
| `tests/test_pipeline/test_video_coherence.py` | Coherence evaluation tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| P1-16 text-image coherence checker | Direct pattern to follow (same 4-dimension structure) |
| P3-08 video attribute evaluator | Frame extraction and multimodal call patterns |
| P3-07 video generation module | How videos are generated and stored |
| `docs/reference/prd.md` (Section 4.9.5) | Full coherence verification spec |

---

## Definition of Done

- [ ] 4-dimension coherence scoring for ad copy + video pairs
- [ ] Below 6 on any dimension correctly flags incoherence
- [ ] Diagnostics identify failing dimensions with rationale
- [ ] Results logged to ledger per variant
- [ ] Incoherent pairs surfaced for targeted regen (P3-10)
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**P3-10 (Video Pareto selection + regen loop)** uses attribute scores (P3-08) and coherence scores (P3-09) to select the best variant and trigger targeted regen on failures.
