# PD-05 Primer: Curated Set Video Support

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PD-04 (canonical video score structure). See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PD-05 ports video rendering support from the Ad Library tab into the Curated Set tab. Currently, `CuratedSet.tsx` only handles image ads — it renders `image_url` via `<img>` tags but has zero awareness of `video_url`. The Ad Library tab (`AdLibrary.tsx`) already has full video support: `<video>` elements with hover-to-play on thumbnails, controls on expanded view, download buttons, copy-only fallback with film emoji, and conditional `video_scores` display. This ticket reuses those patterns in the curation workflow and extends the backend ZIP export to include video files alongside images.

### Why It Matters

- **The Tool Is the Product** (Pillar 9): Video ads that make it to curation must be viewable and exportable, not just text stubs
- Without video rendering in the Curated Set, reviewers cannot preview their curated video ads before export — breaking the curation workflow for video sessions
- The export ZIP currently only bundles image files; video-session exports would ship empty media folders

---

## What Was Already Done

- PD-04: Canonical video score structure (`video_scores` with composite, attribute %, coherence) is in place
- PA-09: Ad Library tab has full video rendering (`<video>` elements, hover play, download, fallback)
- PA-10: Curated Set tab has full image curation workflow (reorder, annotate, edit copy, export ZIP)
- `app/api/routes/curation.py` `export_curated_zip` function bundles image files into per-ad folders (lines 267-354)
- `AdData` interface in `CuratedSet.tsx` includes `image_url` but not `video_url` or `video_scores`

---

## What This Ticket Must Accomplish

### Goal

Enable video ads to be rendered, scored, and exported in the Curated Set tab, matching the Ad Library's video support.

### Deliverables Checklist

#### A. Frontend — Video Rendering (`app/frontend/src/tabs/CuratedSet.tsx`)

- [ ] Extend `AdData` interface to include `video_url?: string | null` and `video_scores?: Record<string, number> | null`
- [ ] Replace the image-only preview in card layout: if ad has `video_url`, render a `<video>` element (muted, hover-to-play on thumbnail) instead of `<img>`
- [ ] Add copy-only fallback (film emoji placeholder) for video-session ads missing `video_url` — match `AdLibrary.tsx` pattern
- [ ] Show `video_scores` (composite, attribute %, coherence) instead of 5-dimension quality scores when the ad is a video ad
- [ ] Add "Download MP4" link for video ads in the card actions area
- [ ] Reuse styles from `AdLibrary.tsx` (`adVideo`, `adVideoExpanded`, `noVideoThumb`, `noVideoPlaceholder`, `downloadBtn`)

#### B. Backend — ZIP Export (`app/api/routes/curation.py`)

- [ ] In `export_curated_zip`, check for `video_path` in ad assets alongside `image_path`
- [ ] If a video file exists, include it in the per-ad ZIP folder (e.g., `video.mp4`)
- [ ] Update `metadata.json` to include `video_file` field
- [ ] Update manifest CSV header to include `video_file` column
- [ ] Update `summary` dict to track `videos_included` count
- [ ] Update the `exportInfo` text in frontend to mention "images/videos" instead of just "images"

#### C. Integration Expectations

- [ ] Video rendering must work for ads added to curation from video sessions
- [ ] Image-only sessions must continue to work unchanged (no regressions)
- [ ] Export ZIP must handle mixed sets (some ads with images, some with videos)

#### D. Documentation

- [ ] Add PD-05 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/PD-05-curated-video-support
# ... implement ...
git push -u origin feature/PD-05-curated-video-support
```

Conventional Commits: `feat:`, `fix:`, `docs:`

---

## Important Context

### Files to Modify

| File | Action |
|------|--------|
| `app/frontend/src/tabs/CuratedSet.tsx` | Add video rendering, video_scores display, download button, fallback placeholder |
| `app/api/routes/curation.py` | Include video files in export ZIP, update manifest CSV and metadata |
| `docs/DEVLOG.md` | Add PD-05 entry |

### Files You Should NOT Modify

- `app/frontend/src/tabs/AdLibrary.tsx` — reference only, do not change
- `iterate/batch_processor.py` — unrelated pipeline code
- `evaluate/evaluator.py` — scoring logic is out of scope

### Files You Should READ for Context

| File | Why |
|------|-----|
| `app/frontend/src/tabs/AdLibrary.tsx` | Video rendering pattern to reuse — `<video>` elements, hover play, `video_scores` conditional, download button, fallback placeholders |
| `app/frontend/src/tabs/CuratedSet.tsx` | Current image-only implementation to extend |
| `app/api/routes/curation.py` (lines 267-354) | `export_curated_zip` function — current image bundling logic to extend for video |
| `app/frontend/src/api/curation.ts` | Curation API client — may need `video_url` in types |

---

## Suggested Implementation Pattern

**Frontend — Card video rendering** (mirror AdLibrary.tsx lines 179-201):

```tsx
// In card layout, replace image-only block:
{ad?.video_url ? (
  <video
    src={`/api${ad.video_url}`}
    muted
    style={s.cardVideo}
    onMouseEnter={(e) => (e.target as HTMLVideoElement).play().catch(() => {})}
    onMouseLeave={(e) => { const v = e.target as HTMLVideoElement; v.pause(); v.currentTime = 0 }}
  />
) : ad?.image_url ? (
  <img src={`/api${ad.image_url}`} ... />
) : null}
```

**Backend — Video in ZIP** (after existing image block around line 349):

```python
video_path = asset.get("video_path")
if isinstance(video_path, str) and video_path:
    video_file = Path(video_path)
    if video_file.exists() and video_file.is_file():
        export_name = prefix + f"video{video_file.suffix.lower() or '.mp4'}"
        zf.write(video_file, export_name)
        metadata["video_file"] = Path(export_name).name
        summary["videos_included"] += 1
```

---

## Edge Cases to Handle

1. **Mixed curated set** — some ads have images, some have videos, some have both. Each type should render and export correctly.
2. **Missing video file on disk** — `video_url` exists in ad data but file was deleted. Render copy-only fallback; skip in ZIP without crashing.
3. **No video_scores** — video ad that was not yet scored. Show aggregate_score badge but skip video_scores grid.

---

## Definition of Done

- [ ] Video ads in Curated Set render with `<video>` elements (hover play on card, controls on expanded)
- [ ] Copy-only video ads show film emoji fallback
- [ ] Video scores (composite, attribute %, coherence) display for video ads instead of 5-dimension scores
- [ ] Download MP4 button appears for video ads
- [ ] Export ZIP includes video files in per-ad folders
- [ ] Manifest CSV includes video_file column
- [ ] Image-only sessions still work with no regressions
- [ ] DEVLOG updated

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Frontend video rendering in CuratedSet.tsx | 15 min |
| Backend ZIP export video support | 10 min |
| Testing and edge cases | 5 min |

**Total: ~30 minutes**

---

## After This Ticket: What Comes Next

- PD-06 (Pipeline Iteration Wiring) — unrelated but next in sequence
- With PD-05 complete, the full video workflow is end-to-end: generate, evaluate, display in library, curate, and export
