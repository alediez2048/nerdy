# PA-10 Primer: Curation Layer + Curated Set Tab

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-09 (session detail dashboard), PA-02 (database schema with curated_sets table) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PA-10 adds the **curation layer** — a 6th dashboard tab where users select, reorder, annotate, and lightly edit generated ads before export. The curation state lives in its own database table (separate from the immutable session/ledger data) to preserve metric integrity. Edits are tracked with before/after diffs. The curated set can be exported as a Meta-ready zip containing ad copy JSON and images.

### Why It Matters

- **The Reviewer Is a User, Too** (Pillar 8): The curated showcase tells the quality story — raw pipeline output needs human refinement before presentation
- Curation is where autonomous generation meets human judgment — the last mile before Meta Ad Manager
- Strict separation between generated metrics and curated edits ensures dashboard data stays honest
- Export as a zip with Meta-ready formatting makes the output immediately actionable

---

## What Was Already Done

- PA-02: Database schema includes `curated_sets` table (per-session curation state)
- PA-09: Session detail page with 5-tab dashboard shell
- P5-04: Ad Library tab (panel 5) — filterable ad browser that this tab extends
- P1-18: Full ad assembly + export (Meta-ready file naming, copy JSON + images)

---

## What This Ticket Must Accomplish

### Goal

Build a 6th dashboard tab for ad curation with select/deselect, reorder, annotate, light edit with diff tracking, and zip export — all persisted in the `curated_sets` database table.

### Deliverables Checklist

#### A. Curation API (`app/api/routes/curation.py`)

- [ ] `GET /sessions/{sessionId}/curated` — returns current curated set (selected ads, order, annotations, edits)
- [ ] `PUT /sessions/{sessionId}/curated` — updates curated set (batch update: selections, order, annotations)
- [ ] `PATCH /sessions/{sessionId}/curated/{adId}` — update single ad curation (select/deselect, annotate, edit)
- [ ] `POST /sessions/{sessionId}/curated/export` — generates and returns zip file
- [ ] All curation state stored in `curated_sets` table, never in the ledger or session data
- [ ] Edit tracking: store `original_text` and `edited_text` with timestamp for every field change

#### B. Curation Data Model (`app/models/curation.py`)

- [ ] `CuratedAd` model:
  - `session_id`, `ad_id`, `selected: bool`, `sort_order: int`
  - `annotation: str | None` (user notes)
  - `edits: JSON` — list of `{ field, original, edited, edited_at }`
  - `created_at`, `updated_at`
- [ ] Database migration for `curated_ads` table (extends PA-02 schema)

#### C. Curated Set Tab (`frontend/src/components/dashboard/CuratedSetTab.tsx`)

- [ ] 6th tab in the dashboard: "Curated Set"
- [ ] Two-panel layout: left = available ads (from Ad Library), right = curated set (selected + ordered)
- [ ] **Select/Deselect:** Checkbox or click-to-add on available ads; click-to-remove on curated set
- [ ] **Reorder:** Drag-and-drop reordering within curated set (use a library like `@dnd-kit/core`)
- [ ] **Annotate:** Inline text field on each curated ad for user notes
- [ ] **Light Edit:** Click-to-edit on ad copy fields (primary text, headline, description, CTA)
  - Edited fields visually marked (e.g., yellow highlight or "edited" badge)
  - "View diff" toggle shows before/after for each edited field
  - Edits auto-save on blur
- [ ] **Export button:** "Export Curated Set" triggers zip download
- [ ] **Clear labels:** "As Generated" vs "As Edited" clearly distinguished throughout

#### D. Zip Export (`app/services/export.py`)

- [ ] Generate zip containing:
  - `ads/` folder with one subfolder per ad (named by ad_id)
  - Each ad folder: `copy.json` (Meta-formatted fields), image files (if available), `metadata.json` (scores, rationales, edit history)
  - `manifest.json` at root: ordered list of ads with summary metadata
  - `annotations.json`: all user annotations keyed by ad_id
- [ ] Use edited text (not original) in `copy.json` if edits exist
- [ ] Include edit history in `metadata.json` for audit trail
- [ ] Meta-ready formatting: primary_text, headline, description, call_to_action fields

#### E. Tests (`tests/test_app/test_curation.py`)

- [ ] TDD first
- [ ] Test select/deselect persists in database
- [ ] Test reorder updates sort_order correctly
- [ ] Test annotation saves and retrieves
- [ ] Test edit tracking stores original and edited text with timestamp
- [ ] Test export zip contains correct structure
- [ ] Test export uses edited text, not original, when edits exist
- [ ] Test curation data is isolated from session/ledger data (no cross-contamination)
- [ ] Test curated set for nonexistent session returns 404
- [ ] Minimum: 8+ tests

#### F. Frontend Tests (`tests/test_frontend/test_curated_set.test.tsx`)

- [ ] Test tab renders in dashboard
- [ ] Test select/deselect toggles ad in curated set
- [ ] Test drag-and-drop reorder updates order
- [ ] Test edit mode shows diff view
- [ ] Test export button triggers download
- [ ] Minimum: 5+ tests

#### G. Documentation

- [ ] Add PA-10 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/PA-10-curation-layer
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Curation layer | R5-Q6 | 6th tab: select, reorder, annotate, light edit with diff tracking, export as zip |
| Data isolation | Risk Register | Curation lives in its own DB table; dashboard metrics always read from immutable session data; curated edits never pollute generated metrics |
| Export format | P1-18 | Meta-ready file naming and copy JSON structure |

### Files to Create

| File | Why |
|------|-----|
| `app/api/routes/curation.py` | Curation CRUD + export API |
| `app/models/curation.py` | CuratedAd data model |
| `app/services/export.py` | Zip export service |
| `frontend/src/components/dashboard/CuratedSetTab.tsx` | Curated Set tab component |
| `tests/test_app/test_curation.py` | Backend tests |
| `tests/test_frontend/test_curated_set.test.tsx` | Frontend tests |

### Files to Modify

| File | Action |
|------|--------|
| `frontend/src/components/Dashboard.tsx` | Add 6th "Curated Set" tab |
| `app/api/main.py` | Register curation router |
| `docs/DEVLOG.md` | Add ticket entry |

### Files You Should NOT Modify

- Session ledger files — curation state is strictly separate
- Dashboard panels 1-5 — they must continue to show unedited generated data
- `export_dashboard.py` — this is for dashboard data, not curated exports

### Files You Should READ for Context

| File | Why |
|------|-----|
| PA-02 primer | Database schema including `curated_sets` table |
| PA-09 primer | Dashboard shell and tab structure |
| P5-04 primer | Ad Library tab — curation source data |
| P1-18 primer | Full ad assembly and Meta-ready export format |
| `interviews.md` (R5-Q6) | Full rationale for curation layer design |

---

## Suggested Implementation Pattern

```python
# app/models/curation.py
class CuratedAd(Base):
    __tablename__ = "curated_ads"
    id = Column(UUID, primary_key=True, default=uuid4)
    session_id = Column(UUID, ForeignKey("sessions.id"), nullable=False)
    ad_id = Column(String, nullable=False)
    selected = Column(Boolean, default=True)
    sort_order = Column(Integer, nullable=False)
    annotation = Column(Text, nullable=True)
    edits = Column(JSON, default=list)  # [{"field": "headline", "original": "...", "edited": "...", "edited_at": "..."}]
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

```tsx
// frontend/src/components/dashboard/CuratedSetTab.tsx (simplified)
function CuratedSetTab({ sessionId }) {
  const { data: curated, mutate } = useCuratedSet(sessionId);
  const { data: allAds } = useSessionAds(sessionId);

  const handleSelect = (adId) => mutate({ adId, selected: true });
  const handleRemove = (adId) => mutate({ adId, selected: false });
  const handleReorder = (newOrder) => mutate({ reorder: newOrder });

  return (
    <DndContext onDragEnd={handleReorder}>
      <div className="two-panel">
        <AvailableAds ads={allAds} onSelect={handleSelect} />
        <CuratedList ads={curated} onRemove={handleRemove} onEdit={handleEdit} />
      </div>
      <ExportButton sessionId={sessionId} />
    </DndContext>
  );
}
```

---

## Edge Cases to Handle

1. No ads published yet — tab shows "No ads available for curation" with explanation
2. User edits an ad, then the pipeline regenerates it — curated edits reference the original ad_id; regenerated versions are separate entries
3. Export with zero ads selected — show validation error, don't generate empty zip
4. Concurrent edits (two tabs open) — last-write-wins with `updated_at` timestamp; no real-time collaboration needed for v1
5. Very large curated set (50+ ads) — drag-and-drop must remain performant; virtualize list if needed
6. Ad has images but image files are missing on disk — export includes copy.json with note about missing images

---

## Definition of Done

- [ ] Curated selections persist across page reloads
- [ ] Edits tracked with before/after diff for every changed field
- [ ] Export produces Meta-ready zip with correct structure
- [ ] Dashboard metrics (tabs 1-5) remain unaffected by curation edits
- [ ] "As Generated" vs "As Edited" clearly labeled
- [ ] Tests pass (`python -m pytest tests/ -v`)
- [ ] Lint clean (`ruff check . --fix`)
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Curation data model + migration | 15 min |
| Curation API endpoints | 30 min |
| Zip export service | 25 min |
| CuratedSetTab component (select, reorder, annotate) | 40 min |
| Edit mode + diff tracking UI | 30 min |
| Backend tests | 25 min |
| Frontend tests | 20 min |
| DEVLOG update | 5–10 min |

---

## After This Ticket: What Comes Next

**PA-11 (Share session link)** adds read-only sharing for session dashboards. Shared viewers see the full dashboard (including the curated set) but cannot modify curation or start new sessions.
