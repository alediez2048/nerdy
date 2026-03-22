# PD-15: Dashboard Redesign — Unified Multi-Content Scoring Panels

## Goal
Redesign the global dashboard to display scoring data across all content types (copy, image, video, brief adherence) side by side. Replaces the current copy-only panels with a unified view that shows the full 20-dimension scoring framework from PD-12/13/14.

## The Problem
The dashboard was built for copy scoring only. Every panel hardcodes `DIMENSIONS = ("clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance")`. After PD-12/13/14, the ledger contains 4 categories × 5 dimensions = 20 dimensions of scoring data, but the dashboard can't display any of it.

## Approach: Option C — Side-by-Side Comparison

Show all content types simultaneously rather than toggling between them. Users see the full picture at a glance.

## Panel-by-Panel Redesign

### Pipeline Summary (hero metrics)
**Today:** Single row of KPIs (generated, published, discarded, avg score, tokens, cost)
**After:** Three-column layout showing per-type stats:

```
           Copy                 Image                Video
   85 ads generated        58 with images         9 with videos
   70 published            avg 7.5 image score    avg 7.0 video score
   7.4 avg copy score      7.1 avg adherence      0.75 composite
```

**Backend changes:**
- `_build_pipeline_summary()` computes stats per content type
- Reads `ImageScored`, `VideoScored`, `BriefAdherenceScored` event counts and averages

### Dimension Deep-Dive
**Today:** 5 copy dimension averages + 5×5 correlation matrix
**After:** 4 sections, each with their own 5 dimensions:

```
Copy Quality (5)          Brief Adherence (5)
├─ Clarity: 7.8          ├─ Audience Match: 9.0
├─ Value Prop: 7.1       ├─ Goal Alignment: 8.5
├─ CTA: 6.9              ├─ Persona Fit: 7.0
├─ Brand Voice: 7.6      ├─ Message Delivery: 8.5
└─ Emotional Res: 7.3    └─ Format Adherence: 7.5

Image Quality (5)         Video Quality (5)
├─ Visual Clarity: 7.2   ├─ Hook Strength: 6.8
├─ Brand Consistency: 7.5├─ Visual Quality: 7.4
├─ Emotional Impact: 6.8 ├─ Narrative Flow: 7.0
├─ Coherence: 7.3        ├─ Coherence: 7.1
└─ Platform Fit: 8.1     └─ UGC Authenticity: 6.5
```

**Correlation Matrix:** Sub-tabs — Copy | Image | Video | Adherence (5×5 each, not 20×20)

**Backend changes:**
- `_build_dimension_deep_dive()` accepts dimension set parameter
- New constants: `IMAGE_DIMENSIONS`, `VIDEO_DIMENSIONS`, `ADHERENCE_DIMENSIONS`
- Reads scores from `ImageScored`, `VideoScored`, `BriefAdherenceScored` events

### Quality Trends
**Today:** Single line of batch avg scores (copy only)
**After:** Multi-line chart with one trend per category

- Copy avg score over time (existing)
- Image avg score over time (from `ImageScored` events)
- Video avg score over time (from `VideoScored` events)
- Brief adherence avg over time (from `BriefAdherenceScored` events)

**Backend changes:**
- `_build_quality_trends()` computes per-category time series
- Returns `{ copy_trends: [...], image_trends: [...], video_trends: [...], adherence_trends: [...] }`

### Iteration Cycles
**Today:** Shows copy regeneration before/after scores
**After:** Add adherence delta — did regeneration improve brief adherence too?

```
ad_001  Copy: 6.2 → 7.6 (+1.4)  Adherence: 7.0 → 8.2 (+1.2)
```

**Backend changes:**
- Match `BriefAdherenceScored` events to regeneration cycles
- Include adherence before/after alongside copy before/after

### Ad Library Cards
**Today:** Single score badge (copy aggregate)
**After:** Multi-score badges on each card

```
[published] [Copy 7.3] [Adherence 8.1] [Image 7.5]
```

Or for video ads:
```
[published] [Copy 7.3] [Adherence 8.1] [Video 7.0]
```

**Frontend only** — data already returned by `_build_ad_library()`, just needs rendering

### System Health
**Today:** SPC on copy batch averages
**After:** SPC per content type (tab selector within panel)

- Copy SPC (existing)
- Image SPC (batch averages of image scores)
- Video SPC (batch averages of video scores)
- Adherence SPC (batch averages of adherence scores)

**Backend changes:**
- `_build_system_health()` computes SPC per category

## Backend Changes Summary

### `output/export_dashboard.py`

```python
# New dimension constants
COPY_DIMENSIONS = ("clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance")
IMAGE_DIMENSIONS = ("visual_clarity", "brand_consistency", "emotional_impact", "copy_image_coherence", "platform_fit")
VIDEO_DIMENSIONS = ("hook_strength", "visual_quality", "narrative_flow", "copy_video_coherence", "ugc_authenticity")
ADHERENCE_DIMENSIONS = ("audience_match", "goal_alignment", "persona_fit", "message_delivery", "format_adherence")

# Updated functions
def _build_pipeline_summary(events, ...) -> dict:
    # Add: image_avg, video_avg, adherence_avg, counts per type

def _build_dimension_deep_dive(events, ...) -> dict:
    # Add: image_dimensions, video_dimensions, adherence_dimensions
    # Each with trends + correlation matrix

def _build_quality_trends(events, ...) -> dict:
    # Add: per-category time series

def _build_ad_library(events) -> list[dict]:
    # Add: image_scores, video_scores, adherence_scores per ad entry
```

### New ledger event types read

| Event | Source | Dimensions |
|-------|--------|-----------|
| `BriefAdherenceScored` | PD-12 | audience_match, goal_alignment, persona_fit, message_delivery, format_adherence |
| `ImageScored` | PD-13 | visual_clarity, brand_consistency, emotional_impact, copy_image_coherence, platform_fit |
| `VideoScored` | PD-14 | hook_strength, visual_quality, narrative_flow, copy_video_coherence, ugc_authenticity |

## Frontend Changes Summary

### `GlobalDashboard.tsx`

- `PipelineSummaryTab` — Three-column layout for per-type stats
- `DimensionDeepDiveTab` — 4 dimension sections (2×2 grid) + tabbed correlation matrices
- `QualityTrendsTab` — Multi-series score chart
- `IterationCyclesTab` — Add adherence delta
- `SystemHealthTab` — Tabbed SPC per content type

### `GlobalAdLibrary.tsx`

- Ad cards show multi-score badges: `[Copy 7.3] [Adherence 8.1] [Image 7.5]`
- Expanded view shows all 4 dimension breakdowns

### Session-Level Dashboard (`SessionDetail.tsx` + tabs)

The session dashboard uses the same `_build_*` backend functions via `/sessions/{id}/summary`, `/sessions/{id}/dimensions`, etc. All changes propagate automatically. Frontend tabs need updates:

**`tabs/Overview.tsx`** (session summary)
- Add per-type score averages: Copy avg, Image avg, Video avg, Adherence avg
- Show which scoring categories are available for this session (image sessions won't have video scores)

**`tabs/AdLibrary.tsx`** (session ad library)
- Ad cards show multi-score badges: `[Copy 7.3] [Adherence 8.1] [Image 7.5]`
- Expanded view shows all available dimension breakdowns (copy + adherence always, image/video if present)
- Update `Ad` interface to include new score fields

**`tabs/QualityTrends.tsx`** (if exists) or quality section in overview
- Multi-series trends showing copy + image + video + adherence over cycles
- Adapt to session type: image sessions show copy + image + adherence; video sessions show copy + video + adherence

**`tabs/DimensionDeepDive.tsx`** or dimension section
- Show dimension averages for all available categories (same 2×2 grid as global, but scoped to this session)
- Correlation matrix with category sub-tabs

**`tabs/CompetitiveIntel.tsx`** (session-level)
- No changes — competitive data is global, not session-scoped

### Session API Endpoints (backend)

The session dashboard API already calls the same `_build_*` functions:
```
GET /sessions/{id}/summary    → _build_pipeline_summary()
GET /sessions/{id}/dimensions → _build_dimension_deep_dive()
GET /sessions/{id}/ads        → _build_ad_library()
GET /sessions/{id}/cycles     → iteration cycles
GET /sessions/{id}/costs      → token economics
GET /sessions/{id}/spc        → system health
```

Since these all read from the session's own ledger and PD-12/13/14 write scoring events to that same ledger, the backend changes are shared — update the `_build_*` functions once and both global + session dashboards get the data.

### TypeScript Types

```typescript
// Shared Ad interface (used by GlobalAdLibrary, AdLibrary, CuratedSet)
interface Ad {
  // existing fields...
  adherence_scores?: Record<string, number> | null
  adherence_avg?: number | null
  image_scores_detailed?: Record<string, number> | null
  image_avg?: number | null
  video_scores_detailed?: Record<string, number> | null
  video_avg?: number | null
}
```

## What Doesn't Change
- Copy scoring panels still work exactly as today (backward compatible)
- Panels gracefully handle missing data (image/video sections show "No scored images/videos yet" if PD-13/14 haven't run)
- Session-type awareness: image sessions don't show empty video panels, video sessions don't show empty image panels
- Existing dashboard URL and tab structure preserved
- Session-level dashboard follows same pattern (uses same `_build_*` functions)

## Dependencies
- **PD-12** (brief adherence scorer) — provides `BriefAdherenceScored` events
- **PD-13** (image scorer) — provides `ImageScored` events
- **PD-14** (video scorer) — provides `VideoScored` events
- Dashboard works without PD-12/13/14 data (empty sections) but is meaningless without scores

## Estimate
~4 hours (backend panel builders + frontend redesign + TypeScript types)

## Status: ⏳ NOT STARTED
