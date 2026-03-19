# PC-02 Primer: Video Pipeline + Evaluation

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PC-00 (session type + video form), PC-01 (Kling client + video spec builder). See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PC-02 builds the video pipeline orchestrator and a dedicated video evaluator. This is the core "generate → evaluate → select" loop for video sessions. It does NOT wire into the app (that's PC-03) — it's a standalone pipeline that can be tested via CLI or unit tests.

### Why It Matters

- Without orchestration, the Kling client (PC-01) is just a function — this ticket makes it a pipeline
- Video evaluation must be separate from image evaluation: different attributes, different thresholds, different failure modes
- Lessons from Veo attempt: must handle missing files, must not log `VideoGenerated` unless file exists, must use a lower coherence threshold for short UGC clips
- Graceful degradation is the critical pattern: if video fails, the ad gets copy-only output (no image in video sessions)

---

## What Was Already Done

- PC-00: `SessionConfig` with `session_type=video`, video form fields
- PC-01: `generate_video/kling_client.py` — `KlingClient.generate_video()`
- PC-01: `generate_video/video_spec.py` — `VideoSpec`, `build_video_spec()`, `build_kling_prompt()`
- P1-15: `evaluate/image_evaluator.py` — image attribute evaluation pattern (reference, not reuse)
- P1-16: `evaluate/coherence_checker.py` — coherence checking pattern (reference, not reuse)
- P0-08: `iterate/retry.py` — `retry_with_backoff()`
- P0-02: `iterate/ledger.py` — append-only event logging

---

## What This Ticket Must Accomplish

### Goal

Build a video pipeline that generates 2 variants per ad via Kling, evaluates them, selects the best, and handles failures gracefully. Create a dedicated video evaluator separate from the image evaluator.

### Deliverables Checklist

#### A. Video Variant Generation (`generate_video/orchestrator.py` — create)

- [ ] `VideoVariant` dataclass:
  ```python
  @dataclass
  class VideoVariant:
      ad_id: str
      variant_type: str  # "anchor" | "alternative"
      video_path: str
      duration: int
      audio_mode: str
      aspect_ratio: str
      prompt_used: str
      seed: int
      credits_consumed: int
      model_used: str  # "kling-v2.6-pro"
  ```
- [ ] `generate_video_variants(video_spec, ad_id, seed, output_dir, kling_client) -> list[VideoVariant]`:
  - Generate 2 variants: **anchor** (straight interpretation of spec) and **alternative** (different camera/pacing via modified spec)
  - For alternative: swap camera_movement (e.g. handheld→steady), adjust pacing keyword, change lighting
  - Log `VideoGenerated` event to ledger **only when file exists**
  - Log `VideoGenerationFailed` when Kling API fails (with error reason)
  - Deterministic seeds: anchor = seed, alternative = seed + 3000
  - Return only successful variants (0, 1, or 2)

#### B. Video Evaluator (`evaluate/video_evaluator.py` — create)

- [ ] **Separate from image evaluator** — different attributes, different thresholds
- [ ] `VIDEO_ATTRIBUTES` — 5 binary attributes:
  1. `hook_timing` — attention-grabbing element in first 2 seconds
  2. `ugc_authenticity` — feels genuine, not overproduced (handheld feel, natural lighting)
  3. `pacing` — matches campaign energy (fast for conversion, measured for awareness)
  4. `text_legibility` — text overlays (if present) readable at mobile size
  5. `no_artifacts` — no facial distortion, temporal glitches, physics violations, flickering
- [ ] `VideoEvalResult` dataclass:
  - `ad_id`, `variant_type`, `attributes` (dict[str, bool]), `attribute_pass_pct`, `meets_threshold`
- [ ] `evaluate_video_attributes(video_path, video_spec, ad_id, variant_type) -> VideoEvalResult`:
  - Calls Gemini Flash multimodal with video file (frame sampling)
  - 80% pass threshold (4/5 must pass)
  - **Critical:** If `video_path` does not exist, return a failing result immediately — do NOT call the API
  - Logs `VideoEvaluated` event to ledger
- [ ] `VideoCoherenceResult` dataclass:
  - `ad_id`, `variant_type`, `dimensions` (dict[str, float]), `avg_score`, `is_coherent`
- [ ] `check_video_coherence(ad_copy, video_path, ad_id, variant_type) -> VideoCoherenceResult`:
  - 4 dimensions: message_alignment, audience_match, emotional_consistency, narrative_flow
  - **Threshold: 4.0** (not 6.0 — lesson from Veo attempt; short UGC clips score lower than images)
  - **Critical:** If `video_path` does not exist, return incoherent result — do NOT call the API
  - Logs `VideoCoherenceChecked` event to ledger
- [ ] `compute_composite_score(eval_result, coherence_result) -> float`:
  - 40% attribute pass percentage + 60% coherence average
  - Used for variant selection

#### C. Video Selection + Degradation (`generate_video/orchestrator.py` — extend)

- [ ] `select_best_video(variants, eval_results, coherence_results) -> VideoVariant | None`:
  - Rank by composite score
  - Winner must pass attribute threshold (80%) AND coherence threshold (4.0)
  - If no variant passes: return None (graceful degradation)
- [ ] `run_video_pipeline(session_config, briefs, ledger_path, output_dir) -> list[dict]`:
  - For each brief:
    1. Expand brief (reuse `generate/brief_expansion.py`)
    2. Generate ad copy (reuse `generate/ad_generator.py`) — needed for text overlays and coherence
    3. Evaluate copy (reuse `evaluate/evaluator.py`)
    4. Build video spec from expanded brief + session config + ad copy
    5. Generate 2 video variants via Kling
    6. Evaluate each variant (attributes + coherence)
    7. Select best variant
    8. If none pass: log `VideoBlocked`, ad output is copy-only
    9. If winner exists: log `VideoSelected`, ad output is copy + video
  - Graceful degradation: API errors, missing files, eval failures all handled without crashing
  - Returns list of result dicts per ad (ad_id, copy, video_path or None, scores, events)

#### D. Checkpoint-Resume (`generate_video/orchestrator.py`)

- [ ] `should_skip_video_ad(ad_id, ledger_path) -> bool`:
  - Check ledger for existing `VideoSelected` or `VideoBlocked` events for this ad_id
  - If found: skip (already processed)
- [ ] In `run_video_pipeline()`: call `should_skip_video_ad()` before processing each ad

#### E. Tests

- [ ] TDD first
- [ ] Test `generate_video_variants()` produces 2 variants (mock Kling)
- [ ] Test `generate_video_variants()` handles API failure gracefully (returns 0 or 1 variant)
- [ ] Test `VideoGenerated` only logged when file exists
- [ ] Test `VideoGenerationFailed` logged on API error
- [ ] Test `evaluate_video_attributes()` with existing file (mock Gemini)
- [ ] Test `evaluate_video_attributes()` with missing file (returns fail, no API call)
- [ ] Test `check_video_coherence()` with 4.0 threshold
- [ ] Test `check_video_coherence()` with missing file (returns incoherent, no API call)
- [ ] Test `select_best_video()` picks higher composite score
- [ ] Test `select_best_video()` returns None when no variant passes
- [ ] Test `run_video_pipeline()` end-to-end (mock everything)
- [ ] Test checkpoint-resume skips already-processed ads
- [ ] Minimum: 12+ tests

---

## Branch & Merge Workflow

Work on `develop` branch per project convention.

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `generate_video/orchestrator.py` | Video variant generation + pipeline orchestrator |
| `evaluate/video_evaluator.py` | Video-specific evaluation (separate from image) |
| `tests/test_pipeline/test_video_orchestrator.py` | Pipeline tests |
| `tests/test_pipeline/test_video_evaluator.py` | Evaluator tests |

### Files to Modify

| File | Action |
|------|--------|
| `docs/DEVLOG.md` | Add ticket entry |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `generate_video/kling_client.py` | Client from PC-01 |
| `generate_video/video_spec.py` | VideoSpec from PC-01 |
| `evaluate/image_evaluator.py` | Pattern reference (do NOT extend — create separate) |
| `evaluate/coherence_checker.py` | Pattern reference (do NOT extend) |
| `iterate/ledger.py` | Event logging |
| `iterate/checkpoint.py` | Checkpoint pattern |
| `docs/development/VIDEO_IMPLEMENTATION_SESSION_PRIMER.md` | §2.2 fixes #4–6 (coherence threshold, missing files, ledger semantics) |

### Files You Should NOT Modify

- `evaluate/image_evaluator.py` — image evaluation stays separate
- `evaluate/coherence_checker.py` — image coherence stays separate
- `iterate/batch_processor.py` — that's the image pipeline; video has its own orchestrator
- `app/workers/tasks/pipeline_task.py` — app wiring is PC-03

---

## Lessons from Veo Attempt (Apply These)

These were fixes that worked during the Veo session but were reverted. Re-implement the concepts:

1. **Never log `VideoGenerated` unless the file actually exists on disk**
2. **Never evaluate a missing file** — check `Path(video_path).exists()` before calling evaluator
3. **Video coherence threshold = 4.0** — short UGC clips score ~5.0 on image-oriented 6.0 thresholds and get blocked
4. **Log `VideoGenerationFailed` with error details** when the API fails — not a generic failure

---

## Definition of Done

- [ ] `generate_video_variants()` produces 2 variants via Kling (mock in tests)
- [ ] Video evaluator scores 5 attributes + 4 coherence dimensions
- [ ] Missing files handled gracefully (no API calls, immediate fail result)
- [ ] `run_video_pipeline()` processes multiple ads with checkpoint-resume
- [ ] Graceful degradation: failures produce copy-only output
- [ ] Ledger events are semantically correct (VideoGenerated only on success)
- [ ] All tests pass, lint clean
- [ ] DEVLOG updated

---

## Estimated Time: 90–120 minutes

---

## After This Ticket: What Comes Next

**PC-03** wires this pipeline into the app (Celery task routing by session type, frontend video player, assembly).
