# PA-10 Primer: Curation Layer + Curated Set Tab

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-09 (Dashboard Integration) must be complete — session detail with 7 tabs. PA-02 provided CuratedSet/CuratedAd models. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PA-10 builds the **curation layer** — the 7th dashboard tab where users select, reorder, annotate, lightly edit, and export their best ads as a Meta-ready zip (R5-Q6, Section 4.7.7).

### Why It Matters

- **The Reviewer Is a User, Too** (Pillar 8): Curation is where human judgment meets system output
- Immutable generation + mutable curation: edits are tracked separately, dashboard metrics always show original scores
- The export zip is the final deliverable — what actually gets uploaded to Meta Ads Manager
- Diff tracking on edits creates an audit trail

---

## What Was Already Done

- PA-02: `CuratedSet` and `CuratedAd` models in `app/models/curation.py`
- PA-09: Session detail page with "Curated Set" tab placeholder
- PA-09: `GET /sessions/{session_id}/ads` returns all ads for the session
- P5-10: `output/export_ad_library.py` — exports ads to JSON/CSV (reference for export logic)

---

## What This Ticket Must Accomplish

### Goal

Build curation API endpoints, the Curated Set tab UI, and the Meta-ready zip export.

### Deliverables Checklist

#### A. Curation API (`app/api/routes/curation.py`)

- [ ] `POST /sessions/{session_id}/curated` — create curated set for session
- [ ] `GET /sessions/{session_id}/curated` — get curated set with all curated ads
- [ ] `POST /sessions/{session_id}/curated/ads` — add ad to curated set
  - Body: `{ "ad_id": "...", "position": 1 }`
- [ ] `DELETE /sessions/{session_id}/curated/ads/{ad_id}` — remove ad from curated set
- [ ] `PATCH /sessions/{session_id}/curated/ads/{ad_id}` — update ad in curated set
  - Reorder: `{ "position": 3 }`
  - Annotate: `{ "annotation": "Great hook, needs shorter CTA" }`
  - Edit: `{ "edited_copy": { "primary_text": "new text..." } }`
- [ ] `POST /sessions/{session_id}/curated/reorder` — batch reorder: `{ "ad_ids": ["id1", "id2", ...] }`
- [ ] `GET /sessions/{session_id}/curated/export` — download Meta-ready zip
- [ ] Register router in `app/api/main.py`
- [ ] Per-user isolation on all endpoints

#### B. Edit Diff Tracking

- [ ] When `edited_copy` is provided, store both original and edited versions
- [ ] `CuratedAd.edited_copy` JSON format: `{ "field": { "original": "...", "edited": "..." } }`
- [ ] Dashboard metrics always use original scores, never recalculate from edits

#### C. Meta-Ready Zip Export

- [ ] ZIP structure:
  ```
  curated_export/
  ├── manifest.csv          (one row per ad: position, headline, primary_text, description, cta, score)
  ├── ads/
  │   ├── 01_ad_<id>/
  │   │   ├── copy.json     (primary_text, headline, description, cta — edited version if edited)
  │   │   ├── metadata.json (scores, status, original copy if edited)
  │   │   └── image.png     (winning image if available)
  │   ├── 02_ad_<id>/
  │   │   └── ...
  └── summary.json          (total ads, avg score, export timestamp)
  ```
- [ ] Return as streaming ZIP response
- [ ] Use edited copy in export if edits exist, original otherwise

#### D. Curated Set Tab (`src/tabs/CuratedSet.tsx`)

- [ ] **Empty state:** "No curated ads yet. Browse the Ad Library tab and select ads to curate."
- [ ] **Selection mode:** In Ad Library tab, each ad gets a "Add to Curated Set" button
- [ ] **Curated list view:**
  - Drag-and-drop reorder (or up/down arrows)
  - Each ad shows: position number, copy preview, scores, status badges
  - Inline annotation field
  - "Edit" button opens light edit modal
- [ ] **Light edit modal:**
  - Editable fields: primary_text, headline, description
  - Side-by-side diff view (original vs edited)
  - Save / discard buttons
- [ ] **Export button:** "Export Meta-Ready ZIP" → triggers download
- [ ] **Counter:** "5 ads curated" in tab header

#### E. Tests (`tests/test_app/test_curation.py`)

- [ ] TDD first
- [ ] Test create curated set
- [ ] Test add ad to curated set
- [ ] Test remove ad from curated set
- [ ] Test reorder ads
- [ ] Test annotate ad
- [ ] Test edit ad with diff tracking (original preserved)
- [ ] Test export zip contains correct structure
- [ ] Test per-user isolation
- [ ] Minimum: 8+ tests

#### F. Documentation

- [ ] Add PA-10 entry in `docs/DEVLOG.md`

---

## Important Context

### Curation Spec (PRD Section 4.7.7)

> Immutable generation + mutable curation:
> 1. Select ads for curated set
> 2. Reorder within curated set
> 3. Annotate — add notes per ad
> 4. Light edit — minor copy polish with before/after diff tracking
> 5. Export curated set as Meta-ready zip
>
> Dashboard metrics always reflect original pipeline output, never curated edits.

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Immutable generation | R5-Q6 | Pipeline output never modified. Curation is a separate layer. |
| Diff tracking | R5-Q6 | Edits stored as original → edited pairs. Full audit trail. |
| Dashboard shows originals | R5-Q6 | Metrics always reflect pipeline output, not curated edits. |

### Files to Create

| File | Why |
|------|-----|
| `app/api/routes/curation.py` | Curation CRUD + export endpoints |
| `app/api/schemas/curation.py` | Curation Pydantic schemas |
| `src/tabs/CuratedSet.tsx` | Curated Set tab (replace placeholder from PA-09) |
| `tests/test_app/test_curation.py` | Curation tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `docs/reference/prd.md` (Section 4.7.7) | Curation layer spec |
| `app/models/curation.py` | CuratedSet/CuratedAd models from PA-02 |
| `output/export_ad_library.py` | Reference for ad export logic |
| `output/exporter.py` | Reference for file export structure |

---

## Definition of Done

- [ ] Curation CRUD API: create, add, remove, reorder, annotate, edit
- [ ] Diff tracking preserves original copy alongside edits
- [ ] Meta-ready ZIP export with manifest, copy, metadata, images
- [ ] Curated Set tab with drag-and-drop reorder, annotation, light edit modal
- [ ] Dashboard metrics always show original pipeline scores
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time: 90–120 minutes

---

## After This Ticket: What Comes Next

**PA-11 (Share Session Link)** adds the ability to share a read-only session link with a time-limited token.
