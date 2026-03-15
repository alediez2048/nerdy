# P5-04 Primer: Dashboard HTML — Ad Library (Panel 5)

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P5-03 (Dashboard Panels 3–4) should be complete. See `docs/DEVLOG.md`.

## What Is This Ticket?

P5-04 adds Panel 5 to the existing `output/dashboard.html`:

- **Panel 5: Ad Library** — Filterable browser with per-ad cards, scores, expandable rationales, and before/after pairs

## Why It Matters

- The ad library is the primary evidence of system output quality — reviewers will browse individual ads
- "All 50+ ads browsable; rationales expand" is the explicit acceptance criterion
- Before/after pairs prove the feedback loop works at the individual ad level
- Expandable rationales show visible reasoning — **Pillar 7: Visible Reasoning Is a First-Class Output**
- Automatic deduction of -15 points for "No evaluation scores on generated ads" and -5 for "Fewer than 50 ads generated"

## What Already Exists

- `output/dashboard.html` from P5-02/P5-03 — Panel 5 is a placeholder tab
- `output/dashboard_data.json` from P5-01 — contains `ad_library` array with all ads
- `output/assembler.py` — `AssembledAd` with copy, scores, rationales
- `output/exporter.py` — `export_ad()` writes structured ad folders

## What This Ticket Must Accomplish

**Goal:** Replace Panel 5 placeholder with a filterable, browsable ad library.

### Deliverables Checklist

#### A. Panel 5: Ad Library Browser

**Filter Bar** (top of panel):
- **Score range**: Slider or dropdown (e.g., 0–5, 5–7, 7–8, 8–10, All)
- **Status**: Dropdown (Published, Discarded, All)
- **Audience**: Dropdown populated from data (e.g., "parents", "students", All)
- **Campaign Goal**: Dropdown populated from data (e.g., "awareness", "conversion", All)
- **Search**: Text search across ad copy
- **Sort by**: Aggregate score (desc), cycle count, ad ID

**Ad Cards** (grid or list layout):

Each ad card shows:
- **Ad ID** and status badge (green "Published" or red "Discarded")
- **Aggregate score** as a prominent number with color (green ≥ 7.0, amber 5–7, red < 5)
- **Copy preview**: First 100 chars of primary text, truncated with "..."
- **Dimension scores**: 5 mini-bars or numbers (clarity, VP, CTA, BV, ER)
- **Cycle count**: "3 cycles" indicator
- **Expand button**: Reveals full details

**Expanded View** (when card is clicked/expanded):
- **Full ad copy**: Headline, primary text, description, CTA button text
- **Per-dimension scores** with contrastive rationale text for each
- **Before/after pair**: If the ad was regenerated, show first-cycle copy + score vs. final copy + score side by side
- **Lifecycle timeline**: Generated → Evaluated (score) → Regenerated → Re-evaluated → Published/Discarded
- **Image thumbnail** if available (or placeholder)
- **Token cost** for this ad
- **Model used** (Flash vs. Pro)
- **Collapse button** to return to card view

**Responsive**: Cards in a 2–3 column grid on desktop, single column on narrow screens.

#### B. Tests (`tests/test_output/test_dashboard_ad_library.py`)

- Test all 50+ ads are rendered in the ad library
- Test filter by status (Published vs Discarded) reduces visible cards
- Test filter by score range works correctly
- Test expanded view contains full copy and rationale text
- Test before/after pair is shown for regenerated ads

Minimum: 5 tests

#### C. Documentation

- Add P5-04 entry in `docs/DEVLOG.md`

### Architectural Decisions

- **Client-side filtering**: All data is in `dashboard_data.json` — filter in JavaScript, no server needed
- **Expandable cards**: Use CSS transitions with JavaScript toggle — no accordion library needed
- **Before/after pairs**: Reconstruct from lifecycle events in the ad data — first evaluation vs. final evaluation
- **Performance**: 50+ cards is fine for client-side rendering; no pagination needed unless 200+

### Files to Modify

| File | Why |
|------|-----|
| `output/dashboard.html` | Add Panel 5 content |

### Files to Create

| File | Why |
|------|-----|
| `tests/test_output/test_dashboard_ad_library.py` | Ad library tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `output/dashboard.html` | Existing dashboard structure |
| `output/dashboard_data.json` | `ad_library` array structure |
| `output/assembler.py` | AssembledAd fields — what's available per ad |

### Definition of Done

- All 50+ ads are browsable in the ad library panel
- Filter bar works: score range, status, audience, campaign goal, search, sort
- Rationales expand when clicking an ad card
- Before/after pairs visible for regenerated ads
- Tests pass
- Lint clean
- DEVLOG updated

**Estimated Time:** 60–90 minutes

### After This Ticket: What Comes Next

**P5-05** adds Panel 6 (Token Economics) — cost attribution and marginal analysis visualization.
