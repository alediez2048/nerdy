# PC-01 Primer: Kling 2.6 Client + Video Spec Builder

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PC-00 (session type + video form fields), P0-08 (retry logic), P0-02 (ledger). See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PC-01 creates the Kling 2.6 API client and a video spec builder that converts session config (persona, key message, 8-part framework fields) into a Kling-ready prompt. This replaces the Veo approach from the first attempt.

### Why Kling 2.6 Instead of Veo

| Factor | Veo 3.1 Fast | Kling 2.6 |
|--------|-------------|-----------|
| Rate limit | 2 RPM (Paid Tier 1) — primary blocker | No known hard RPM cap |
| Pricing | ~$0.15/sec ($0.90/6s clip) | ~$0.049/sec ($0.49/10s clip) |
| Audio | No `generate_audio` param; prompt-only | Native `sound` boolean |
| Negative prompt | Not supported on Veo endpoint | Supported (`negative_prompt` param) |
| API style | Synchronous (blocking) | Async task-based (submit → poll → download) |
| Auth | `GEMINI_API_KEY` (shared with text) | Separate `KLING_API_KEY` |

Decision documented in `docs/deliverables/decisionlog.md`.

---

## What Was Already Done

- PC-00: `SessionConfig` has `session_type`, `video_count`, `video_duration`, `video_audio_mode`, `video_aspect_ratio`, and all 8-part advanced fields
- P0-08: `iterate/retry.py` — `retry_with_backoff()` for API resilience
- P0-03: `generate/seeds.py` — identity-derived deterministic seeds
- P0-02: `iterate/ledger.py` — append-only event logging

---

## What This Ticket Must Accomplish

### Goal

Build a Kling 2.6 client and a video spec builder that produces Kling-ready prompts from session config + expanded brief + ad copy.

### Deliverables Checklist

#### A. Kling Client (`generate_video/kling_client.py` — create)

- [ ] `KlingClient` class:
  - Auth via `KLING_API_KEY` env var
  - Base URL: `https://api.klingapi.com`
  - Model: `kling-v2.6-pro`
- [ ] `submit_text2video(prompt, duration, aspect_ratio, audio, negative_prompt, mode) -> str`:
  - POST to `/v1/videos/text2video`
  - Returns `task_id`
  - `mode`: "standard" (default, ~30s) or "professional" (~60s)
  - `duration`: "5" or "10"
  - `aspect_ratio`: "9:16", "16:9", "1:1"
  - `sound`: boolean (True = with audio, doubles credits)
  - `negative_prompt`: string (default: "blur, distort, low quality, brand logos, trademarks")
- [ ] `poll_task(task_id, timeout_seconds, poll_interval) -> TaskResult`:
  - GET `/v1/videos/{task_id}`
  - Poll until status is "completed" or "failed"
  - Default timeout: 120s, poll interval: 5s
  - Returns `TaskResult` dataclass: `status`, `video_url`, `error_message`
- [ ] `download_video(video_url, output_path) -> str`:
  - Downloads MP4 to `output_path`
  - Returns path on success
- [ ] `generate_video(prompt, duration, aspect_ratio, audio, negative_prompt, output_path) -> str`:
  - Convenience method: submit → poll → download
  - Uses `retry_with_backoff()` from `iterate/retry.py`
  - Raises `VideoGenerationError` on failure
- [ ] Rate limiter:
  - Configurable RPM (default 10, from `data/config.yaml`)
  - Tracks last N call timestamps, waits if needed
  - Logs wait time

#### B. Video Spec Builder (`generate_video/video_spec.py` — create/rewrite)

- [ ] `VideoSpec` dataclass:
  ```python
  @dataclass
  class VideoSpec:
      scene: str
      visual_style: str
      camera_movement: str
      subject_action: str
      setting: str
      lighting_mood: str
      audio_mode: str  # "silent" | "with_audio"
      audio_detail: str
      color_palette: str
      negative_prompt: str
      duration: int  # 5 or 10
      aspect_ratio: str  # "9:16" | "16:9" | "1:1"
      text_overlay_sequence: list[str]  # [hook, value_prop, cta]
      persona: str
      campaign_goal: str
  ```
- [ ] `build_video_spec(expanded_brief, session_config, ad_copy) -> VideoSpec`:
  - **If user provided explicit fields** (non-empty strings in session_config): use them directly
  - **If fields are empty** (auto mode): derive from persona + creative_brief + ad_copy using Gemini Flash
  - Persona mapping (same as image but video-specific):
    - `athlete_recruit` → fast-paced, competitive energy, campus/field, handheld
    - `suburban_optimizer` → calm, organized, before/after progression, steady camera
    - `immigrant_navigator` → warm family scenes, step-by-step, reassuring, medium shot
    - `cultural_investor` → technology-focused, data overlays, clean, dolly-in
    - `system_optimizer` → data dashboard aesthetic, minimal motion, fast
    - `neurodivergent_advocate` → warm, inclusive, comfortable setting, slow-motion
    - `burned_returner` → transformation story, contrast (before/after), tracking shot
  - Text overlay sequence from ad copy: `[hook_line, value_prop, cta_button]`
  - Brand safety negative prompt always included
- [ ] `build_kling_prompt(spec: VideoSpec) -> str`:
  - Assembles the 8-part framework into a single prompt string (100–150 words)
  - Structure: subject/action first, then scene, visual style, camera, setting, lighting, audio cues, color palette
  - Appends brand-specific instructions (no logos, generic clothing)
  - Does NOT include negative prompt (that goes as a separate Kling API param)

#### C. Config (`data/config.yaml` — extend)

- [ ] `kling_rpm: 10` (rate limiter)
- [ ] `kling_mode: "standard"` (or "professional")
- [ ] `video_budget_per_session: 10.00` (dollars)

#### D. Environment (`.env.example` — extend)

- [ ] `KLING_API_KEY=` placeholder

#### E. Tests (`tests/test_pipeline/test_kling_client.py`, `tests/test_pipeline/test_video_spec.py`)

- [ ] TDD first
- [ ] Test `submit_text2video()` constructs correct request (mock HTTP)
- [ ] Test `poll_task()` handles completed, failed, and timeout states
- [ ] Test `generate_video()` end-to-end flow (mock)
- [ ] Test rate limiter waits when at capacity
- [ ] Test `build_video_spec()` with explicit fields (passthrough)
- [ ] Test `build_video_spec()` with empty fields (auto-derive, mock Gemini)
- [ ] Test `build_kling_prompt()` produces 100–150 word prompt
- [ ] Test persona mapping produces different specs
- [ ] Test brand safety negative prompt always present
- [ ] Minimum: 10+ tests

---

## Branch & Merge Workflow

Work on `develop` branch per project convention.

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `generate_video/kling_client.py` | Kling 2.6 API client |
| `generate_video/video_spec.py` | VideoSpec dataclass + prompt builder |
| `tests/test_pipeline/test_kling_client.py` | Client tests |
| `tests/test_pipeline/test_video_spec.py` | Spec builder tests |

### Files to Modify

| File | Action |
|------|--------|
| `data/config.yaml` | Add Kling config section |
| `.env.example` | Add KLING_API_KEY placeholder |
| `docs/DEVLOG.md` | Add ticket entry |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `generate/visual_spec.py` | Existing VisualSpec pattern (image) — similar structure |
| `iterate/retry.py` | Reuse retry logic |
| `video-ad-creation-best-practices.md` | 8-part prompt framework |
| `app/api/schemas/session.py` | Video config fields from PC-00 |
| `docs/development/VIDEO_IMPLEMENTATION_SESSION_PRIMER.md` | Lessons from Veo attempt |

### Files You Should NOT Modify

- `generate/image_generator.py` — video is a separate track
- `evaluate/image_evaluator.py` — video evaluation is in PC-02
- `iterate/batch_processor.py` — video pipeline wiring is in PC-02/PC-03
- Old Veo code on `video-implementation` branch — abandoned

---

## Kling API Reference

**Text-to-Video endpoint:**
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

**Response:** `{ "task_id": "..." }`

**Poll status:**
```
GET https://api.klingapi.com/v1/videos/{task_id}
```

**Response:** `{ "status": "completed", "video_url": "https://..." }`

**Credit costs:**
- 5s silent: 65 credits
- 10s silent: 130 credits
- 5s with audio: 130 credits
- 10s with audio: 260 credits

Standard plan: $6.99/month = 660 credits (~5 silent 10s videos).
New users: $1 free credits.

---

## Edge Cases to Handle

1. `KLING_API_KEY` not set — raise clear error at client init, not mid-pipeline
2. Task stuck in "processing" beyond timeout — cancel and log `VideoGenerationFailed`
3. Downloaded file is corrupt/empty — validate file size > 0, retry once
4. Rate limiter at capacity — wait with logging, never exceed configured RPM
5. Budget cap exceeded — skip remaining videos in session, log reason per ad

---

## Definition of Done

- [ ] Kling client can submit, poll, and download a video (integration test with real API optional)
- [ ] `build_video_spec()` correctly uses explicit fields or auto-derives from persona
- [ ] `build_kling_prompt()` produces well-structured 100–150 word prompts
- [ ] Rate limiter works correctly
- [ ] All tests pass, lint clean
- [ ] DEVLOG updated
- [ ] `.env.example` has `KLING_API_KEY`

---

## Estimated Time: 90–120 minutes

---

## After This Ticket: What Comes Next

**PC-02** builds the video pipeline orchestrator and video evaluator that uses this client.
