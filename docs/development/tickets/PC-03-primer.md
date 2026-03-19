# PC-03 Primer: App Integration + Video Assembly

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PC-00 (session type + form), PC-01 (Kling client + video spec), PC-02 (video pipeline + evaluation). See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PC-03 is the capstone — it wires the video pipeline into the app so a user can create a video session, run it, and see generated video ads in the Ad Library with a video player. This ticket also creates the video-specific assembler and handles progress reporting.

### Why It Matters

- Without this ticket, the video pipeline (PC-02) is CLI-only — no app integration
- Users need to see their video sessions running with real-time progress
- The Ad Library needs a video player (not just image thumbnails) for video sessions
- The Celery task must route to the correct pipeline based on `session_type`
- Video assembly is simpler than image: output is copy JSON + video MP4 (no image)

---

## What Was Already Done

- PC-00: `SessionConfig` with `session_type`, video form fields, session type badge/filter
- PC-01: `generate_video/kling_client.py`, `generate_video/video_spec.py`
- PC-02: `generate_video/orchestrator.py` — `run_video_pipeline()`, `evaluate/video_evaluator.py`
- PA-07: `app/workers/tasks/pipeline_task.py` — Celery task for image pipeline
- PA-08: SSE progress reporting (`publish_progress()`)
- P1-18: `output/assembler.py` — image ad assembly pattern

---

## What This Ticket Must Accomplish

### Goal

Wire the video pipeline into the Celery task, create video assembly/export, and update the frontend to display video sessions and video ads.

### Deliverables Checklist

#### A. Celery Task Routing (`app/workers/tasks/pipeline_task.py` — extend)

- [ ] At the start of `run_pipeline_session()`, read `session_type` from session config
- [ ] If `session_type == "video"`:
  - Extract video-specific config: `video_count`, `video_duration`, `video_audio_mode`, `video_aspect_ratio`, all advanced fields
  - Call `run_video_pipeline()` from `generate_video/orchestrator.py`
  - Use `video_count` as the number of ads (not `ad_count`)
  - Pass Kling-specific config (API key, RPM, mode from config.yaml)
- [ ] If `session_type == "image"` (or missing for backward compat):
  - Run existing image pipeline (unchanged)
- [ ] Video progress stages reported via SSE:
  - `VIDEO_PIPELINE_START` — with total video count
  - `VIDEO_AD_START` — per ad (brief expansion + copy gen)
  - `VIDEO_GENERATING` — Kling API call in progress
  - `VIDEO_EVALUATING` — evaluation in progress
  - `VIDEO_AD_COMPLETE` — per ad (with result: selected/blocked)
  - `VIDEO_PIPELINE_COMPLETE` — with summary stats

#### B. Video Assembler (`output/video_assembler.py` — create)

- [ ] `VideoAssembledAd` dataclass:
  ```python
  @dataclass
  class VideoAssembledAd:
      ad_id: str
      brief_id: str
      primary_text: str
      headline: str
      description: str
      cta_button: str
      winning_video_path: str | None
      video_scores: dict | None  # attribute + coherence scores
      formats: list[str]  # ["copy"] or ["copy", "video"]
      audience: str
      campaign_goal: str
      persona: str
      seed: int
  ```
- [ ] `assemble_video_ad(ad_result, ledger_path) -> VideoAssembledAd`:
  - Reads copy from ad result
  - Reads video path from `VideoSelected` event in ledger (or None if `VideoBlocked`)
  - Sets `formats` to `["copy", "video"]` or `["copy"]`
- [ ] `export_video_ads(assembled_ads, output_dir) -> list[str]`:
  - Per ad: create directory, write `metadata.json`, copy video MP4
  - Returns list of output directories

#### C. Static Video Serving (`app/api/main.py` — extend)

- [ ] Mount `output/videos/` at `/api/videos/` (StaticFiles)
- [ ] Mount session-specific video dirs: `/api/sessions/{session_id}/videos/`
- [ ] CORS: ensure video files are accessible from the frontend

#### D. Frontend — Session Detail for Video (`app/frontend/src/views/SessionDetail.tsx` — extend)

- [ ] Detect `session_type` from session config
- [ ] If `video`: adjust Overview tab to show video-specific stats (videos generated, videos selected, videos blocked)
- [ ] If `video`: Ad Library tab shows video player instead of image thumbnail:
  - `<video>` element with controls, poster frame (first frame or placeholder)
  - Video source URL: `/api/sessions/{session_id}/videos/{filename}`
  - Copy text (primary_text, headline, CTA) displayed alongside
  - Score badge showing composite score
- [ ] Progress bar: video-specific stage labels (not "Generating images...")

#### E. Frontend — Ad Library Video Card

- [ ] Video card component showing:
  - Video player (inline, muted autoplay on hover or click-to-play)
  - Ad copy below (primary_text, headline)
  - CTA button label
  - Scores: attribute pass %, coherence avg, composite
  - Status badge: "Selected" (green) or "Blocked" (red with reason)
  - Download button for the MP4
- [ ] For blocked ads: show copy-only card with "Video generation failed" message

#### F. Tests

- [ ] TDD first
- [ ] Test Celery task routes to video pipeline when `session_type=video`
- [ ] Test Celery task routes to image pipeline when `session_type=image`
- [ ] Test backward compat: missing `session_type` defaults to image
- [ ] Test `assemble_video_ad()` with VideoSelected event
- [ ] Test `assemble_video_ad()` with VideoBlocked event (copy-only)
- [ ] Test `export_video_ads()` creates correct directory structure
- [ ] Test progress stages emitted in correct order
- [ ] Minimum: 8+ tests

---

## Branch & Merge Workflow

Work on `develop` branch per project convention.

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `output/video_assembler.py` | Video ad assembly and export |
| `tests/test_pipeline/test_video_app_integration.py` | App integration tests |

### Files to Modify

| File | Action |
|------|--------|
| `app/workers/tasks/pipeline_task.py` | Route by session_type |
| `app/api/main.py` | Mount video static files |
| `app/frontend/src/views/SessionDetail.tsx` | Video session display |
| `docs/DEVLOG.md` | Add ticket entry |
| `docs/deliverables/decisionlog.md` | Document session type routing decision |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `app/workers/tasks/pipeline_task.py` | Current Celery task flow |
| `generate_video/orchestrator.py` | Video pipeline from PC-02 |
| `output/assembler.py` | Image assembly pattern (reference) |
| `app/frontend/src/views/SessionDetail.tsx` | Current session detail layout |
| `app/frontend/src/types/session.ts` | Frontend types |

### Files You Should NOT Modify

- `iterate/batch_processor.py` — image pipeline stays untouched
- `generate/image_generator.py` — image generation stays untouched
- `evaluate/image_evaluator.py` — image evaluation stays untouched
- `output/assembler.py` — image assembly stays untouched

---

## Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| Route at Celery task level | Single dispatch point. Clean separation. Image pipeline code never sees video config. |
| Separate video assembler | Video output shape is different (no image). Shared assembler would need conditionals everywhere. |
| Video formats = ["copy", "video"] | Not ["copy", "image", "video"]. Video sessions don't generate images. |
| Static file serving for videos | Same pattern as image serving. Videos are large files — serve from disk, not database. |

---

## Edge Cases

1. Session created before PC-00 (no `session_type` field) — default to `image` (backward compat)
2. Video pipeline crashes mid-run — Celery retry + checkpoint-resume from PC-02
3. All videos blocked in a session — session completes with copy-only ads, results_summary notes `0 videos selected`
4. Very long session (20 videos) — progress reporting must show per-ad status, not just batch
5. Video file deleted after generation but before frontend loads — video player shows error state, not crash

---

## Definition of Done

- [ ] Video sessions run end-to-end via the app (create session → run → view results)
- [ ] Ad Library shows video player for video sessions, image cards for image sessions
- [ ] Progress reporting shows video-specific stages
- [ ] Session type routing works correctly (video → video pipeline, image → image pipeline)
- [ ] Backward compatible: existing image sessions unaffected
- [ ] Video files served via static mount
- [ ] Assembly exports copy + video per ad
- [ ] Tests pass, lint clean
- [ ] DEVLOG and decision log updated

---

## Estimated Time: 90–120 minutes

---

## After This Ticket: Phase PC Is Complete

The pipeline now supports two independent tracks:
- **Image sessions:** Brief → Copy → Evaluate → Image → Select → Assemble (copy + image)
- **Video sessions:** Brief → Copy → Evaluate → Video Spec → Kling Generate → Video Evaluate → Select → Assemble (copy + video)

Next priorities:
- **Pilot run:** Create a video session with 3 ads to verify end-to-end
- **P2 (cherry-pick):** Inversion tests, correlation analysis, e2e integration
- **P5 (dashboard + docs):** Include video session data in dashboard panels
