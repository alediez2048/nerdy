# PD-03 Primer: Dead Config Cleanup

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-04 (Session CRUD API), PC-09 (Pre-fill session form from campaign defaults), P3-07+ (Video pipeline). See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PD-03 audits and resolves dead configuration fields — form inputs and schema properties that the user fills out but the pipeline never reads. The session config schema and frontend form collect fields like `model_tier`, `budget_cap_usd`, and `dimension_weights`, plus nine video prompt framework fields, none of which are wired to `pipeline_task.py` or the video pipeline. Users believe they are configuring behavior that is silently ignored.

### Why It Matters

- Users set a budget cap expecting enforcement — it is never checked, creating false confidence
- Users select Flash vs Pro model tier — Flash is always used regardless, which is misleading
- Nine elaborate video prompt fields (scene, visual style, camera movement, etc.) are displayed in the form but `_run_video_pipeline()` never extracts or passes them to `video_spec.py`
- Dead UI fields erode trust: if a user discovers their choices are ignored, the entire config surface becomes suspect
- Cleaning up dead fields reduces schema complexity, form maintenance burden, and test surface

---

## What Was Already Done

- PA-04: `app/api/schemas/session.py` — SessionCreate with config fields including `model_tier`, `budget_cap_usd`, `dimension_weights`
- P3-07+: Video pipeline added 9 video prompt framework fields to the schema (lines 84-91)
- `app/frontend/src/views/NewSessionForm.tsx` — Frontend form renders all config fields including video prompt sections
- `app/workers/tasks/pipeline_task.py` — Pipeline reads session config but only uses a subset of fields

---

## What This Ticket Must Accomplish

### Goal

For every dead config field, decide: (A) wire it to the pipeline, (B) remove it from form + schema, or (C) keep it but disable with a "coming soon" tooltip — then implement that decision.

### Deliverables Checklist

#### A. Audit & Decision (`evaluate each dead field`)

- [ ] `model_tier` (schema line 68) — pipeline always uses Flash. Decision: (B) remove or (C) "coming soon"
- [ ] `budget_cap_usd` (schema line 69) — never enforced. Decision: (B) remove or (C) "coming soon"
- [ ] `dimension_weights` (schema line 67) — awareness/conversion/equal profiles never applied. Decision: (B) remove or (C) "coming soon"
- [ ] 9 video prompt fields (schema lines 84-91): `video_scene`, `video_visual_style`, `video_camera_movement`, `video_subject_action`, `video_setting`, `video_lighting_mood`, `video_audio_detail`, `video_color_palette`, `video_negative_prompt` — Decision: (A) wire to `video_spec.py` if straightforward, or (C) "coming soon"
- [ ] `video_duration` — schema allows 5-10s but frontend only renders an 8s button. Decision: fix frontend to match schema range or restrict schema to match
- [ ] `video_audio_mode`, `video_aspect_ratio` — raw strings in schema, should be Literal/Enum types

#### B. Schema Changes (`app/api/schemas/session.py` — modify)

- [ ] Remove dead fields chosen for option (B)
- [ ] Add "coming soon" metadata or comments for fields chosen for option (C)
- [ ] Convert `video_audio_mode` and `video_aspect_ratio` to `Literal` types with valid values
- [ ] Fix `video_duration` constraint to match the chosen range

#### C. Frontend Changes (`app/frontend/src/views/NewSessionForm.tsx` + `app/frontend/src/types/session.ts` — modify)

- [ ] Remove form sections for fields chosen for option (B)
- [ ] Add disabled state + "coming soon" tooltip for fields chosen for option (C)
- [ ] Fix video duration control to offer full 5-10s range or restrict to 8s only (match schema)
- [ ] Update TypeScript types to match schema changes

#### D. Documentation

- [ ] Add ticket entry in `docs/DEVLOG.md`
- [ ] Update decision log with rationale for each field's disposition (wire / remove / coming-soon)

---

## Branch & Merge Workflow

Work on `develop` branch per project convention.

---

## Important Context

### Files to Create

None — this ticket modifies existing files only.

### Files to Modify

| File | Action |
|------|--------|
| `app/api/schemas/session.py` | Remove or annotate dead fields, add Literal types |
| `app/frontend/src/views/NewSessionForm.tsx` | Remove or disable dead form sections |
| `app/frontend/src/types/session.ts` | Update types to match schema changes |
| `docs/DEVLOG.md` | Add ticket entry |
| `docs/deliverables/decisionlog.md` | Document field disposition decisions |

### Files You Should NOT Modify

- `app/workers/tasks/pipeline_task.py` — unless wiring a field (option A), do not touch pipeline logic
- `app/models/session.py` — config is stored as JSON blob, model column itself doesn't change
- Any `generate/`, `evaluate/`, `iterate/` modules — out of scope unless wiring video fields

### Files You Should READ for Context

| File | Why |
|------|-----|
| `app/workers/tasks/pipeline_task.py` | Verify which config fields are actually read by the pipeline |
| `generate_video/video_spec.py` | Check if video prompt fields could be wired (option A feasibility) |
| `app/api/schemas/session.py` | Current schema with all dead fields — the primary target |
| `app/frontend/src/views/NewSessionForm.tsx` | Current form rendering all dead fields |
| `app/frontend/src/types/session.ts` | TypeScript types that must stay in sync with schema |

---

## Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| Per-field disposition (A/B/C) | Not all dead fields are equal — some are near-ready to wire, others are pure fantasy |
| Prefer (B) remove over (C) "coming soon" | Dead code is worse than missing features — removes maintenance burden |
| Literal types for enums | Raw strings allow invalid values; Literal types give schema validation + IDE autocomplete |
| Fix duration mismatch at frontend | Schema is more permissive — frontend should offer the full range or schema should be tightened |

---

## Suggested Implementation Pattern

```python
# Schema: Replace raw strings with Literal types
from typing import Literal

video_audio_mode: Literal["music", "voiceover", "silent"] = "music"
video_aspect_ratio: Literal["9:16", "1:1", "16:9"] = "9:16"
```

```tsx
// Frontend: "Coming soon" tooltip pattern
<Tooltip title="Coming soon — not yet wired to pipeline">
  <TextField disabled label="Budget Cap (USD)" value="" />
</Tooltip>
```

---

## Edge Cases to Handle

1. Existing sessions in the DB have dead fields stored in their config JSON — removing from schema must not break deserialization of old sessions (use `Optional` with defaults)
2. Frontend form may have validation rules tied to dead fields — remove those validators too
3. If wiring video fields (option A), ensure `video_spec.py` gracefully handles `None` values for optional fields
4. Campaign default_config may reference dead fields — check PC-09 pre-fill logic

---

## Definition of Done

- [ ] Every dead field has an explicit disposition decision documented
- [ ] No form field collects input that the pipeline silently ignores (removed or marked "coming soon")
- [ ] `video_audio_mode` and `video_aspect_ratio` use Literal types
- [ ] `video_duration` frontend and schema are consistent
- [ ] Existing sessions with old config JSON still deserialize without errors
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Decision log updated

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Read pipeline_task.py + video_spec.py to confirm dead fields | 10 min |
| Decide disposition for each field | 5 min |
| Schema changes (remove/annotate/Literal) | 10 min |
| Frontend changes (remove/disable form sections) | 15 min |
| TypeScript type updates | 5 min |
| Backward compat testing (old session deserialization) | 10 min |
| DEVLOG + decision log | 5 min |

---

## After This Ticket: What Comes Next

- **PD-04:** Video Evaluation Consolidation — also cleans up dead/placeholder code in the video evaluation path
- Future tickets that wire "coming soon" fields to the pipeline (e.g., model tier selection, budget enforcement)
