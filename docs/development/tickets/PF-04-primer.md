# PF-04 Primer: Bug Fix Sprint — Frontend Issues

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PF-02 (session QA), PF-03 (dashboard QA) — bug reports produced. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PF-04 fixes all frontend bugs identified in PF-02 and PF-03. Work through the bug report, fix each issue by severity (P0→P1→P2→P3), verify the fix, and mark it resolved.

### Why It Matters

- PF-02/03 identified specific, documented bugs — this is where they get fixed
- Frontend bugs are the most visible to users — broken UX undermines confidence in the tool
- Fixing by severity ensures blocking issues are resolved first

---

## What This Ticket Must Accomplish

### Goal

Fix all P0 (blocking) and P1 (major) frontend bugs. Fix P2 (minor) bugs if time permits. Document any P3 (cosmetic) bugs deferred.

### Common Frontend Bug Categories

#### A. Video Display Issues

- [ ] Video player not rendering in Ad Library
- [ ] Video thumbnail/poster not showing
- [ ] Video hover-to-play not working consistently
- [ ] Video scores not displayed alongside player
- [ ] Video download link broken

#### B. Light/Dark Mode Issues

- [ ] Elements not properly counter-inverted in light mode
- [ ] Text contrast insufficient in one mode
- [ ] Toggle state not persisted across page navigations
- [ ] Charts/visualizations breaking in light mode

#### C. Navigation & Routing

- [ ] Breadcrumb links broken or incorrect
- [ ] Tab state lost on page refresh
- [ ] Back button behavior unexpected
- [ ] Deep links not working (direct URL to session tab)

#### D. Forms & Inputs

- [ ] Session form validation errors not displayed
- [ ] Clone-from-previous not populating all fields
- [ ] Video form advanced section toggle broken
- [ ] Number inputs allowing invalid values

#### E. Data Display

- [ ] Scores showing 0.0 when data exists
- [ ] Relative time display incorrect
- [ ] Session status badge not updating
- [ ] Empty state messages not shown when appropriate
- [ ] Loading spinners missing or stuck

#### F. API Error Handling

- [ ] Network errors showing raw error messages
- [ ] 401/403 errors not redirecting to login
- [ ] 500 errors crashing the page instead of showing error UI

### Process

1. Read `docs/development/PF-02-bug-report.md` (and PF-03 if separate)
2. Sort bugs by severity
3. For each bug:
   - Reproduce the issue
   - Identify the root cause in frontend code
   - Fix the issue
   - Verify the fix
   - Mark as resolved in the bug report
4. Run `npm run build` to verify no build errors
5. Test in both dark and light modes

---

## Branch & Merge Workflow

Work on `video-implementation-2.0` branch (current branch).

---

## Important Context

### Files to Modify

Depends on bugs found. Common files:

| File | Likely Issues |
|------|--------|
| `app/frontend/src/tabs/AdLibrary.tsx` | Video display, filters, download |
| `app/frontend/src/components/SessionCard.tsx` | Preview rendering, status badges |
| `app/frontend/src/views/SessionDetail.tsx` | Tab navigation, breadcrumbs |
| `app/frontend/src/views/NewSessionForm.tsx` | Form validation, clone |
| `app/frontend/src/views/SessionList.tsx` | Filters, pagination, polling |
| `app/frontend/src/index.css` | Light/dark mode |
| `app/frontend/src/views/GlobalDashboard.tsx` | Dashboard tab rendering |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `docs/development/PF-02-bug-report.md` | Bug list to fix |
| `app/frontend/src/design/tokens.ts` | Design system tokens |
| `app/frontend/src/api/sessions.ts` | API client (error handling) |

### Files You Should NOT Modify

- Backend code (backend bugs are PF-05)
- Pipeline code (`generate/`, `evaluate/`, `iterate/`)

---

## Definition of Done

- [ ] All P0 (blocking) bugs fixed
- [ ] All P1 (major) bugs fixed
- [ ] P2 (minor) bugs fixed where feasible
- [ ] P3 (cosmetic) bugs documented if deferred
- [ ] `npm run build` succeeds with zero errors
- [ ] Dark and light modes both work
- [ ] Bug report updated with resolution status
- [ ] DEVLOG updated

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Read bug report + prioritize | 5 min |
| Fix P0 bugs | 15–30 min |
| Fix P1 bugs | 15–30 min |
| Fix P2 bugs | 10–20 min |
| Verify all fixes | 10 min |
| DEVLOG | 5 min |

---

## After This Ticket: What Comes Next

- **PF-05:** Backend bug fixes
- **PF-06:** Test coverage audit
