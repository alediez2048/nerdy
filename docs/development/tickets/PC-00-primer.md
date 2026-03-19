# PC-00 Primer: Session Type + Schema Foundation

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-04 (session schemas), PA-05 (session form), PB-10–PB-14 (persona flow). Image pipeline fully functional on `main`.

---

## What Is This Ticket?

PC-00 adds a `session_type` concept that splits the app into two independent tracks: **image sessions** (existing behavior) and **video sessions** (new). This is the fork point — every subsequent PC ticket builds on this foundation.

### Why It Matters

- Video and image ad creation are fundamentally different workflows with different inputs, costs, and outputs
- Cramming video into the image pipeline created complexity and fragility in the first attempt (see `VIDEO_IMPLEMENTATION_SESSION_PRIMER.md`)
- A clean `session_type` field lets us route to completely separate pipelines without touching existing image code
- The video form needs different fields (8-part prompt framework, duration, audio mode) that don't belong in the image form

---

## What Was Already Done

- PA-04: `app/api/schemas/session.py` — `SessionConfig`, `SessionCreate`, `SessionDetail`, `SessionSummary`
- PA-05: `app/frontend/src/views/NewSessionForm.tsx` — full image session form with progressive disclosure
- PA-05: `app/frontend/src/types/session.ts` — frontend type definitions, `DEFAULT_CONFIG`
- PB-10–PB-14: Persona, creative brief, key message flow through pipeline

---

## What This Ticket Must Accomplish

### Goal

Add `session_type` to the data model and UI. When `video` is selected, show a video-specific form with the 8-part prompt framework (simple mode + advanced accordion). Image sessions remain unchanged.

### Deliverables Checklist

#### A. Backend Schema (`app/api/schemas/session.py`)

- [ ] Add `SessionType` enum: `image`, `video`
- [ ] Add `session_type: SessionType = SessionType.image` to `SessionConfig`
- [ ] Add video-specific fields to `SessionConfig` (all with defaults so image sessions ignore them):
  ```python
  # Video session fields (ignored when session_type=image)
  video_count: int = Field(default=3, ge=1, le=20)
  video_duration: int = Field(default=10, ge=5, le=10)  # 5 or 10 seconds
  video_audio_mode: str = "silent"  # "silent" | "with_audio"
  video_aspect_ratio: str = "9:16"  # "9:16" | "16:9" | "1:1"
  # Advanced video fields (empty = auto-derive from persona/brief)
  video_scene: str = ""
  video_visual_style: str = ""
  video_camera_movement: str = ""
  video_subject_action: str = ""
  video_setting: str = ""
  video_lighting_mood: str = ""
  video_audio_detail: str = ""
  video_color_palette: str = ""
  video_negative_prompt: str = ""
  ```

#### B. Frontend Types (`app/frontend/src/types/session.ts`)

- [ ] Add `SessionType = 'image' | 'video'`
- [ ] Add video fields to `SessionConfig` interface
- [ ] Update `DEFAULT_CONFIG` with video defaults
- [ ] Add `VIDEO_DEFAULTS` const for video-specific defaults

#### C. Session Form (`app/frontend/src/views/NewSessionForm.tsx`)

- [ ] Add session type toggle at the top of the form (Image / Video)
- [ ] When `image` is selected: show existing form (unchanged)
- [ ] When `video` is selected, show **Simple mode**:
  - Persona selector (same as image)
  - Key message (same as image)
  - Audience + Campaign Goal (same as image)
  - Video count (1–20, default 3)
  - Duration (5s / 10s toggle)
  - Audio mode (Silent / With Audio toggle)
  - Aspect ratio (9:16 / 16:9 / 1:1 radio)
- [ ] When `video` is selected, **Advanced accordion** adds:
  - Scene description (textarea)
  - Visual style (text input, placeholder: "UGC realistic, shot on phone")
  - Camera movement (select: handheld, dolly-in, tracking, static, slow-motion)
  - Subject & action (textarea)
  - Background/setting (text input)
  - Lighting & mood (text input, placeholder: "natural, soft morning light")
  - Audio detail (textarea, placeholder: "ambient classroom sounds, no dialogue")
  - Color palette (text input, placeholder: "brand teal #17e2ea, navy #0a2240")
  - Negative prompt (textarea, placeholder: "no text, no subtitles, no brand logos")

#### D. Session List/Card Updates

- [ ] `SessionCard.tsx`: show session type badge (Image / Video) with distinct colors
- [ ] `SessionList.tsx`: add session type filter dropdown
- [ ] Use `lightPurple` (#a488f7) for video badge per PRD color system

#### E. Tests

- [ ] Backend: `SessionConfig` validates video fields, ignores them for image sessions
- [ ] Backend: `session_type` defaults to `image` (backward compatible)
- [ ] Frontend: form renders image mode by default
- [ ] Frontend: toggling to video shows video fields, hides image fields
- [ ] 6+ tests

---

## Branch & Merge Workflow

Work on `develop` branch per project convention.

---

## Important Context

### Files to Modify

| File | Action |
|------|--------|
| `app/api/schemas/session.py` | Add SessionType enum, video fields to SessionConfig |
| `app/frontend/src/types/session.ts` | Mirror SessionType and video fields |
| `app/frontend/src/views/NewSessionForm.tsx` | Session type toggle + video form |
| `app/frontend/src/components/SessionCard.tsx` | Session type badge |
| `app/frontend/src/views/SessionList.tsx` | Session type filter |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `app/api/schemas/session.py` | Current SessionConfig structure |
| `app/frontend/src/types/session.ts` | Current frontend types and DEFAULT_CONFIG |
| `app/frontend/src/views/NewSessionForm.tsx` | Current form layout and progressive disclosure pattern |
| `video-ad-creation-best-practices.md` | 8-part prompt framework that maps to Advanced fields |
| `docs/development/VIDEO_IMPLEMENTATION_SESSION_PRIMER.md` | Why video is now a separate track |

### Files You Should NOT Modify

- `iterate/batch_processor.py` — image pipeline untouched
- `generate/image_generator.py` — image generation untouched
- `evaluate/image_evaluator.py` — image evaluation untouched
- Any pipeline code — this ticket is schema + UI only

---

## Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| Separate tracks, not a toggle | Video and image have different inputs, different pipelines, different outputs. A toggle within one pipeline was tried and failed. |
| Video fields on SessionConfig (not a separate model) | Keeps one config object per session. Video fields have defaults and are ignored for image sessions. Simpler than polymorphic schemas. |
| 8-part framework as Advanced accordion | Simple mode (persona + key message + audio) serves most users. Advanced gives full control for power users. Same progressive disclosure pattern as image form. |
| `video_count` not `ad_count` | Video sessions produce fewer, more expensive assets ($0.49–$0.98 per clip). Default 3, max 20. Different economics from image (default 50, max 200). |

---

## Edge Cases

1. Cloning an image session should keep `session_type=image` — do not carry video fields
2. Cloning a video session should preserve all video fields including advanced
3. Session type is immutable after creation — cannot switch mid-session
4. Empty advanced fields = auto-derive (not an error)

---

## Definition of Done

- [ ] `session_type` field exists on SessionConfig (backend + frontend)
- [ ] Form toggles between image and video modes
- [ ] Video form shows simple fields + advanced accordion
- [ ] Session cards show type badge
- [ ] Session list filters by type
- [ ] Image sessions work identically to before (zero regression)
- [ ] Tests pass, lint clean, DEVLOG updated

---

## Estimated Time: 60–90 minutes

---

## After This Ticket: What Comes Next

**PC-01** builds the Kling 2.6 client and video spec builder that consumes these form fields.
