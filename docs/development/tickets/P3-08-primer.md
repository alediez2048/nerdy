# P3-08 Primer: Video Attribute Evaluator

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P3-07 (Veo integration + video spec extraction), P1-15 (visual attribute evaluator — image pattern to follow) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P3-08 builds the **video attribute evaluator** — a multimodal Gemini Flash call that takes video frames + the video spec and scores each variant against a 10-attribute checklist. All attributes marked "Required" must pass for the variant to proceed. This is the video equivalent of P1-15 (image attribute evaluator).

### Why It Matters

- **Prevention Over Detection Over Correction** (Pillar 2): Catching bad video early avoids wasting downstream coherence checks and assembly steps
- UGC video artifacts (face distortions, illegible text overlays, poor pacing) are harder to fix than detect
- The 10-attribute checklist provides structured, explainable evaluation — not a single opaque score
- Section 4.9.4 of the PRD defines the video attribute evaluation spec
- Failures logged with diagnostics feed the regen loop (P3-10)

---

## What Was Already Done

- P3-07: Veo integration generates 2 video variants per ad
- P1-15: Image attribute evaluator (pattern to follow — binary checklist approach)
- P1-04: Chain-of-thought evaluator (text evaluation — scoring methodology reference)
- P0-06: Evaluator calibration approach

---

## What This Ticket Must Accomplish

### Goal

Build a multimodal video evaluator that scores each video variant against a 10-attribute checklist, logging pass/fail per attribute with diagnostics on failures.

### Deliverables Checklist

#### A. Video Attribute Evaluator (`evaluate/video_attributes.py`)

- [ ] `evaluate_video_attributes(video_path: str, video_spec: VideoSpec) -> VideoAttributeResult`
  - Extracts key frames from video (first frame, hook frame ~1s, mid-point, final frame)
  - Sends frames + video spec to Gemini Flash (multimodal)
  - Evaluates against 10-attribute checklist:
    1. **Hook Timing** (Required) — Attention-grabbing action within first 1.5 seconds
    2. **UGC Authenticity** (Required) — Feels organic/user-generated, not overly polished
    3. **Pacing** (Required) — Matches spec (fast/medium/slow); no dead frames
    4. **Text Legibility** — Any text overlays are readable at mobile resolution
    5. **Brand Safety** (Required) — No inappropriate content, artifacts, or brand conflicts
    6. **Subject Clarity** — Main subject/action is clearly visible and identifiable
    7. **Aspect Ratio Compliance** — Video fills 9:16 frame without letterboxing
    8. **Visual Continuity** — No jarring cuts, glitches, or frame jumps
    9. **Emotional Tone Match** — Video mood matches the spec's intended emotion
    10. **Audio Appropriateness** — Audio (if present) is appropriate; silence is clean
  - Each attribute: pass/fail + confidence score + diagnostic note
  - Returns structured result with overall pass/fail
- [ ] Pass threshold: ALL attributes marked "Required" must pass
- [ ] Non-required attribute failures are logged as warnings, not blockers

#### B. Frame Extraction Utility (`evaluate/frame_extractor.py`)

- [ ] `extract_key_frames(video_path: str, frame_count: int = 4) -> list[str]`
  - Extracts frames at strategic timestamps (0s, 1s, mid, end)
  - Returns list of temporary image file paths
  - Handles various video formats from Veo output

#### C. Tests (`tests/test_pipeline/test_video_attributes.py`)

- [ ] TDD first
- [ ] Test evaluator returns scores for all 10 attributes (mock Gemini response)
- [ ] Test Required attribute failure → overall fail
- [ ] Test non-Required attribute failure → overall pass with warnings
- [ ] Test all Required pass → overall pass
- [ ] Test frame extraction produces expected number of frames
- [ ] Test diagnostic notes are populated on failures
- [ ] Test results logged to ledger with ad_id and variant_id
- [ ] Minimum: 7+ tests

#### D. Documentation

- [ ] Add P3-08 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/P3-08-video-attribute-evaluator
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Attribute checklist (not single score) | R2-Q7, Section 4.9.4 | Structured binary checklist is more actionable than a single quality score — diagnostics feed targeted regen |
| Multimodal evaluation | Section 4.9.4 | Gemini Flash processes video frames + spec together for context-aware evaluation |
| Required vs. optional attributes | Section 4.9.4 | Required attributes are non-negotiable (hook, authenticity, pacing, brand safety); others are warnings |

### Files to Create

| File | Why |
|------|-----|
| `evaluate/video_attributes.py` | Video attribute evaluator (10-attribute checklist) |
| `evaluate/frame_extractor.py` | Key frame extraction from video files |
| `tests/test_pipeline/test_video_attributes.py` | Video attribute evaluation tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| P1-15 image attribute evaluator | Direct pattern to follow (binary checklist for images) |
| P3-07 video generation module | How videos are generated and stored |
| `docs/reference/prd.md` (Section 4.9.4) | Full video attribute evaluation spec |

---

## Definition of Done

- [ ] 10-attribute checklist evaluates each video variant
- [ ] All Required attributes must pass for variant to proceed
- [ ] Failures logged with diagnostic notes
- [ ] Frame extraction works on Veo output format
- [ ] Results logged to ledger per variant
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**P3-09 (Script-video coherence checker)** verifies that the video content aligns with the ad copy across 4 dimensions. P3-08 ensures the video is technically sound; P3-09 ensures it matches the message.
