# PF-02 Primer: Critical Feature QA — Session Creation & Pipeline Execution

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PF-01 (file cleanup). All pipeline phases complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PF-02 is a systematic QA pass through every user-facing session workflow: creating sessions, running pipelines, viewing results, and managing sessions. The goal is to identify and document every bug, broken feature, and rough edge — not to fix them (that's PF-04/05).

### Why It Matters

- Multiple features were built across 80+ tickets by different agent sessions — integration gaps are expected
- Video pipeline was added after image pipeline — backward compatibility may have issues
- The app hasn't had a dedicated QA pass — this is the first comprehensive one
- Bugs found here feed directly into PF-04 (frontend) and PF-05 (backend) fix sprints

---

## What This Ticket Must Accomplish

### Goal

Test every critical session workflow end-to-end and produce a prioritized bug list.

### QA Test Script

#### 1. Image Session — Full Lifecycle

- [ ] Navigate to `/sessions/new`
- [ ] Fill form: audience=parents, goal=conversion, ad_count=3, persona=auto
- [ ] Submit — verify session created, redirects to detail or list
- [ ] Verify session appears in list with "pending" → "running" status
- [ ] Click into session — verify detail page loads
- [ ] Navigate to Watch Live — verify progress updates appear
- [ ] Wait for completion — verify status changes to "completed"
- [ ] Check Overview tab — verify stats populated (ads generated, published, score, cost)
- [ ] Check Ad Library tab — verify ad cards with images, copy, scores
- [ ] Check Quality tab — verify dimension scores and trends
- [ ] Check Token Economics tab — verify cost breakdown
- [ ] Check Competitive tab — verify competitive intel data
- [ ] Check Curated Set tab — verify curation UI works
- [ ] Check System Health tab — verify health metrics

#### 2. Video Session — Full Lifecycle

- [ ] Navigate to `/sessions/new`
- [ ] Switch to Video session type
- [ ] Fill form: audience=students, goal=awareness, video_count=2, provider=fal
- [ ] Submit — verify session created
- [ ] Verify video-specific badges in session list ("Video", "2 videos")
- [ ] Click into session — verify video-specific Overview (videos generated/selected/blocked)
- [ ] Check Ad Library — verify video player renders (not image placeholder)
- [ ] Verify video plays on hover/click
- [ ] Verify video scores displayed (composite, attribute pass, coherence)
- [ ] Verify video download link works

#### 3. Session List Features

- [ ] Filters: test session_type (image/video), audience, goal, status
- [ ] Pagination: create 5+ sessions, verify Load More works
- [ ] Session card: verify badges, status, preview image/video, relative time
- [ ] Delete session: verify confirmation and removal
- [ ] Polling: verify running sessions update without manual refresh

#### 4. Session Detail Features

- [ ] Inline name editing — click, edit, save, cancel
- [ ] Share button — generate link, verify shared view works
- [ ] Tab navigation — all 7 tabs accessible, URL params persist
- [ ] Breadcrumb navigation — back to session list works

#### 5. Edge Cases

- [ ] Create session with minimum config (just audience + goal)
- [ ] Create session with all advanced options
- [ ] Clone from previous session
- [ ] Session with 0 published ads — verify graceful display
- [ ] Network error during creation — verify error message
- [ ] Refresh page during running session — verify state recovery

### Deliverables

- [ ] Bug report: `docs/development/PF-02-bug-report.md` with:
  - Bug ID, severity (P0-blocking/P1-major/P2-minor/P3-cosmetic)
  - Steps to reproduce
  - Expected vs actual behavior
  - Screenshot or description
  - Suggested fix (if obvious)
- [ ] Summary: count of bugs by severity

---

## Branch & Merge Workflow

Work on `video-implementation-2.0` branch (current branch).

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `docs/development/PF-02-bug-report.md` | QA findings and bug list |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `app/frontend/src/App.tsx` | All routes and views |
| `app/frontend/src/views/NewSessionForm.tsx` | Session creation form |
| `app/frontend/src/views/SessionList.tsx` | Session list view |
| `app/frontend/src/views/SessionDetail.tsx` | Session detail + tabs |
| `app/frontend/src/tabs/AdLibrary.tsx` | Ad Library with video player |
| `app/frontend/src/views/WatchLive.tsx` | Live progress view |

### Files You Should NOT Modify

- Do NOT fix bugs in this ticket — just document them
- All fixes happen in PF-04 (frontend) and PF-05 (backend)

---

## Definition of Done

- [ ] All QA test script items executed
- [ ] Bug report created with all findings
- [ ] Bugs prioritized by severity
- [ ] DEVLOG updated

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Image session QA | 15 min |
| Video session QA | 15 min |
| Session list/detail QA | 10 min |
| Edge cases | 10 min |
| Write bug report | 10 min |
| DEVLOG | 5 min |

---

## After This Ticket: What Comes Next

- **PF-03:** Dashboard & analytics QA
- **PF-04:** Frontend bug fixes (using this bug report)
- **PF-05:** Backend bug fixes (using this bug report)
