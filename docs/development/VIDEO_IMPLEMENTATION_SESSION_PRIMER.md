# Video Implementation Session Primer — Handoff for a Fresh Agent

**For:** New Cursor Agent session  
**Project:** Ad-Ops-Autopilot (Nerdy) — Autonomous ad generation for Meta  
**Date:** March 18, 2026 (updated March 19, 2026)  
**Status:** Video implementation did **not** ship in the first attempt (Veo). Phase C has been **redesigned** to use Kling 2.6 with video as a separate session track.

**Start here:** Read this primer, then follow the PC ticket primers (`PC-00` through `PC-03`) in order.

---

## 1. Decision: Kling 2.6 Replaces Veo, Separate Tracks

After a full session attempting Veo 3.1 Fast integration, we identified three fundamental problems:

1. **Veo is unreliable** — 2 RPM rate limit, daily caps, key/project entitlement issues, 429 as the primary blocker
2. **Video needs its own form** — the 8-part prompt framework (scene, style, camera, subject, setting, lighting, audio, color) doesn't fit in the image form
3. **Video and image are different tracks** — cramming video into the image pipeline created fragility and complexity

**New approach:**
- **Kling 2.6** ($0.049/sec, ~$0.49/10s clip, native audio, `negative_prompt` support, async task-based API, no known hard RPM cap)
- **Separate session types** — `session_type: "image" | "video"` on every session, routing to independent pipelines
- **Hybrid video form** — simple mode (persona + key message + audio) + advanced accordion (full 8-part framework)

---

## 2. Previous Veo Attempt (Historical Context)

The first attempt used Veo 3.1 Fast on a `video-implementation` branch. Key facts:

- **Branch:** `video-implementation`, last commit `6502a1c` (PC-02 video flow). Two commits ahead of main.
- **Main** has no video code. All Veo work lives on the branch.
- **10 fixes were tried then reverted** (rate limiting, coherence threshold, missing file handling, JSON parsing, Gemini 2.5 migration, React hooks, ledger semantics, etc.)
- **Primary blocker:** 429 RESOURCE_EXHAUSTED — 2 RPM quota exhausted, plus likely daily cap
- **Secondary blockers:** key/project entitlement issues, gemini-2.0-flash 404 for new users, malformed JSON from Gemini 2.5 Flash

Full details of the 10 fixes and error analysis are preserved in the git history of this file (see commit prior to the Kling redesign).

**The old Veo code on `video-implementation` is abandoned.** Do not carry it forward. Start fresh from `main`.

---

## 3. New Phase C Tickets (PC-00 through PC-03)

| Ticket | Title | Key Deliverable |
|--------|-------|-----------------|
| PC-00 | Session Type + Schema Foundation | `session_type` enum, video form (simple + advanced), session type badge/filter |
| PC-01 | Kling 2.6 Client + Video Spec Builder | `generate_video/kling_client.py`, `VideoSpec`, `build_kling_prompt()` |
| PC-02 | Video Pipeline + Evaluation | `generate_video/orchestrator.py`, `evaluate/video_evaluator.py`, graceful degradation |
| PC-03 | App Integration + Video Assembly | Celery task routing, `output/video_assembler.py`, frontend video player |

Read the full primers at `docs/development/tickets/PC-00-primer.md` through `PC-03-primer.md`.

---

## 4. Lessons from Veo (Apply to Kling Implementation)

These were hard-won insights. Re-implement the concepts:

1. **Never log `VideoGenerated` unless the file actually exists on disk**
2. **Never evaluate a missing file** — check `Path(video_path).exists()` before calling evaluator
3. **Video coherence threshold = 4.0** (not 6.0) — short UGC clips score lower than static images
4. **Log `VideoGenerationFailed` with error details** when the API fails
5. **Positive prompt instructions** over negative prompts for scene/lighting (Kling supports `negative_prompt` as a separate param, so this is cleaner)
6. **Explicit audio instructions** — Kling has a native `sound` boolean, simpler than Veo's prompt-only approach
7. **Rate limiter** — even without a known hard cap, use one (configurable RPM, default 10)
8. **Docker restarts** — remind users that env changes require `docker compose down && docker compose up -d`

---

## 5. Files for a Fresh Agent

- **New Phase C primers:** `docs/development/tickets/PC-00-primer.md` through `PC-03-primer.md`
- **Phase plan:** `docs/development/tickets/P3-00-phase-plan.md`
- **PRD and architecture:** `docs/reference/prd.md`, `.cursor/rules/architecture.mdc`
- **Best practices:** `video-ad-creation-best-practices.md` (8-part framework reference)
- **Current app (start from main):**
  - `app/api/schemas/session.py` — SessionConfig to extend
  - `app/frontend/src/types/session.ts` — frontend types to extend
  - `app/frontend/src/views/NewSessionForm.tsx` — form to extend
  - `app/workers/tasks/pipeline_task.py` — Celery task to route
  - `app/frontend/src/views/SessionDetail.tsx` — session detail to extend
- **Config:** `data/config.yaml`, `.env.example`
- **Existing pipeline (reference, do not modify):** `iterate/batch_processor.py`, `generate/image_generator.py`, `evaluate/image_evaluator.py`

---

## 6. Kling API Quick Reference

```
POST https://api.klingapi.com/v1/videos/text2video
Authorization: Bearer {KLING_API_KEY}

{
  "model": "kling-v2.6-pro",
  "prompt": "...",
  "duration": "10",
  "aspect_ratio": "9:16",
  "mode": "standard",
  "negative_prompt": "blur, distort, low quality, brand logos",
  "sound": false
}
```

- **Auth:** `KLING_API_KEY` (separate from `GEMINI_API_KEY`)
- **Pricing:** ~$0.049/sec silent, ~$0.098/sec with audio
- **Flow:** Submit → get `task_id` → poll `/v1/videos/{task_id}` → download MP4
- **New users:** $1 free credits (~20 silent 10s videos)

---

## 7. Definition of Done (When Video Ships)

- [ ] A video session with 3 ads produces at least one published ad with `formats: ["copy", "video"]` and a playable video in the Ad Library
- [ ] No rate limit errors (429) for a 3-ad video session
- [ ] Ledger: `VideoGenerated` only when file exists; `VideoGenerationFailed` on API error
- [ ] Evaluators skip missing video files
- [ ] Image sessions work identically to before (zero regression)
- [ ] Session type badge and filter work in the session list
- [ ] DEVLOG, decision log, and primer docs updated

---

*Start from `docs/development/tickets/PC-00-primer.md` and work through PC-03 sequentially.*
