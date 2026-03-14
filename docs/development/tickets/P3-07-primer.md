# P3-07 Primer: Veo Integration + Video Spec Extraction

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P1-18 (full ad assembly), P3-06 (multi-aspect-ratio batch generation), P1-14 (Nano Banana Pro integration) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P3-07 integrates **Veo 3.1 Fast API** for UGC-style video generation, adding video as the third creative format alongside copy and image. The pipeline extracts a video spec from the expanded brief and generates 2 video variants per ad (anchor + alternative scene/pacing). Default aspect ratio is 9:16 for Stories/Reels placement.

### Why It Matters

- **Every Token Is an Investment** (Pillar 3): Video at ~$0.90/6-sec clip is expensive — spec extraction ensures each generation attempt is well-targeted
- UGC video is the highest-engagement format on Stories/Reels — adding it unlocks new Meta placements
- 2 variants per ad enable selection without brute-force generation
- Graceful degradation (video fails → copy + image only) means video never blocks ad delivery
- Section 4.9 of the PRD defines the full UGC video architecture

---

## What Was Already Done

- P1-01: Brief expansion engine (generates expanded briefs with grounding)
- P1-14: Nano Banana Pro integration (image generation pipeline — pattern to follow for Veo)
- P1-18: Full ad assembly (copy + image — will be extended in P3-11 to include video)
- P3-01: Shared semantic brief expansion (visual spec extraction — video spec extends this)
- P3-06: Multi-aspect-ratio batch generation (9:16 already generated for images)

---

## What This Ticket Must Accomplish

### Goal

Integrate Veo 3.1 Fast API and build video spec extraction so the pipeline can generate 2 UGC video variants per ad from the expanded brief.

### Deliverables Checklist

#### A. Video Spec Extractor (`generate_video/video_spec.py`)

- [ ] `extract_video_spec(expanded_brief: dict) -> VideoSpec`
  - Derives video spec from the expanded brief (Section 4.9.2)
  - Fields: hook_action, scene_description, pacing (fast/medium/slow), mood, subject_demographic, text_overlay_content, audio_mode (silent/music/voiceover), duration (default 6s), aspect_ratio (default 9:16)
  - Grounded in brief facts — no hallucinated claims
- [ ] `generate_variant_specs(video_spec: VideoSpec) -> tuple[VideoSpec, VideoSpec]`
  - Anchor variant: direct interpretation of the brief
  - Alternative variant: different scene/pacing while preserving message
  - Both specs logged to ledger

#### B. Veo API Client (`generate_video/veo_client.py`)

- [ ] `generate_video(video_spec: VideoSpec, seed: int) -> VideoResult`
  - Calls Veo 3.1 Fast API with the video spec
  - 6-second duration, 9:16 aspect ratio (default)
  - Returns video file path + generation metadata
  - Respects rate limits (shared Google ecosystem with Gemini)
- [ ] `VeoRateLimiter` — shared rate limit awareness with Gemini calls
- [ ] Error handling: API failures raise typed exceptions, do NOT crash the pipeline
- [ ] Retry with exponential backoff (reuse `iterate/retry.py` from P0-08)

#### C. Video Generation Orchestrator (`generate_video/orchestrator.py`)

- [ ] `generate_video_variants(ad_id: str, expanded_brief: dict) -> list[VideoVariant]`
  - Extracts video spec from brief
  - Generates 2 variants (anchor + alternative)
  - Logs all specs and results to ledger with checkpoint_id
  - Returns list of VideoVariant objects with file paths and metadata
- [ ] Video generation runs AFTER image selection (not in parallel) to stagger API load
- [ ] Checkpoint-resume: skips already-generated videos on resume

#### D. Tests (`tests/test_pipeline/test_video_generation.py`)

- [ ] TDD first
- [ ] Test video spec extraction produces valid spec from expanded brief
- [ ] Test variant spec generation produces 2 distinct specs
- [ ] Test anchor and alternative differ in scene/pacing but share message
- [ ] Test Veo client handles API errors gracefully (mock API)
- [ ] Test rate limiter respects configured limits
- [ ] Test orchestrator logs specs and results to ledger
- [ ] Test checkpoint-resume skips already-generated videos
- [ ] Minimum: 7+ tests

#### E. Documentation

- [ ] Add P3-07 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/P3-07-veo-integration
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Shared semantic brief | R1-Q10, Section 4.9.2 | Video spec derived from same expanded brief as image spec — prevents multi-modal incoherence |
| Checkpoint-resume | R3-Q2 | Every successful API call writes checkpoint_id. Resume from last checkpoint. |
| API resilience | R3-Q2 | Exponential backoff on 429/500/503. Fixed delay between calls. 3 retries max. |
| Graceful degradation | Section 4.9 | Video failure never blocks ad delivery — falls back to copy + image only |

### Cost Awareness

- Veo 3.1 Fast: ~$0.15/sec = ~$0.90 per 6-sec video
- 2 variants per ad = $1.80/ad before regen
- Budget cap in brief config (default $20 per ad across all formats)
- Silent mode saves ~33% on audio generation costs
- 10-ad pilot (P3-13) before scaling to full batch

### Files to Create

| File | Why |
|------|-----|
| `generate_video/video_spec.py` | Video spec extraction from expanded brief |
| `generate_video/veo_client.py` | Veo 3.1 Fast API client with rate limiting |
| `generate_video/orchestrator.py` | Video generation orchestration (2 variants per ad) |
| `tests/test_pipeline/test_video_generation.py` | Video generation tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| P1-14 image generation module | Pattern to follow for Veo integration |
| P3-01 shared semantic brief | How visual/video specs are derived from briefs |
| `iterate/retry.py` | Reuse retry logic from P0-08 |
| `iterate/checkpoint.py` | Checkpoint-resume integration |
| `docs/reference/prd.md` (Section 4.9) | Full UGC video architecture spec |

---

## Definition of Done

- [ ] Video specs extracted from expanded briefs
- [ ] 2 video variants generated per ad (anchor + alternative)
- [ ] All specs and results logged to ledger
- [ ] 9:16 default aspect ratio for Stories/Reels
- [ ] API errors handled gracefully (no pipeline crashes)
- [ ] Checkpoint-resume works for video generation
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 60–90 minutes

---

## After This Ticket: What Comes Next

**P3-08 (Video attribute evaluator)** scores each variant against a 10-attribute checklist. Without P3-07, there are no videos to evaluate.
