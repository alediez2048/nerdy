# PD-09: Standalone Competitive Intel Page — Profiles & Analytics

## Goal
Create a standalone `/competitive` page separate from the global dashboard, with its own nav link. Shows competitor profile cards and landscape analytics without any dashboard chrome.

## Deliverables
1. **`app/frontend/src/views/CompetitiveIntelPage.tsx`** — Standalone page
2. **`app/frontend/src/App.tsx`** — Add `/competitive` route
3. **`app/frontend/src/components/NavBar.tsx`** — Add "Competitive" nav item

## Sections

### Competitor Profiles
- Card per competitor from `competitor_summaries` in `data/competitive/patterns.json`
- Each card shows: strategy summary, dominant hooks (badges), emotional levers (badges), gaps
- 4 competitors: Chegg, Wyzant, Kaplan, Varsity Tutors

### Landscape Analytics
- Hook distribution bar chart (existing)
- Per-competitor strategy radar / side-by-side hook breakdown
- Gap analysis list (underutilized hooks = differentiation opportunities)
- Temporal trends table (rising/falling/stable)

## Data Source
- `GET /api/competitive/summary` (already exists, no backend changes needed)

## Acceptance Criteria
- `/competitive` loads independently with no dashboard header/tabs/timeframe selectors
- All 4 competitors display with strategy cards
- Analytics charts render correctly
- Nav bar shows "Competitive" link with active state

## Dependencies
- None (independent of other PD tickets)

## Estimate
~1 hour
