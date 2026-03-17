# PB-07 Primer: Persona Selector in Session Config + Dashboard Updates

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PB-04 (Brief Expansion), PB-05 (Ad Generator) must be complete. See `docs/development/tickets/PB-00-phase-plan.md`.

---

## What Is This Ticket?

PB-07 adds persona selection to the session configuration (backend + frontend) and minor dashboard updates — persona badge on cards, persona filter in Ad Library, persona breakdown in Overview.

### Why It Matters

- Users need to choose which persona to target when creating a session
- The dashboard should show which persona each ad was generated for
- Persona filtering in Ad Library helps users find ads for specific audiences
- This is the frontend surface for all the pipeline work in PB-01 through PB-06

---

## What Was Already Done

- PA-04: `SessionConfig` schema with `audience` (parents/students) and `campaign_goal` (awareness/conversion)
- PA-05: `NewSessionForm` with audience toggle and campaign goal toggle
- PA-06: `SessionCard` with audience/goal badges
- PA-09: `SessionDetail` with 7-tab dashboard, `AdLibrary` tab with status filter
- PB-04: `expand_brief()` accepts `persona` parameter
- PB-05: Ad generator uses persona-aware voice profiles

---

## What This Ticket Must Accomplish

### Deliverables Checklist

#### A. Backend — SessionConfig Schema (`app/api/schemas/session.py`)

- [ ] Add `Persona` enum: `athlete_recruit`, `suburban_optimizer`, `immigrant_navigator`, `cultural_investor`, `system_optimizer`, `neurodivergent_advocate`, `burned_returner`, `auto`
- [ ] Add `persona: Persona = Persona.auto` to `SessionConfig`
- [ ] Persona flows through: SessionConfig → pipeline task → brief expansion → ad generation

#### B. Backend — Pipeline Task Integration

- [ ] Update `app/workers/tasks/pipeline_task.py` to pass `persona` from session config to the pipeline
- [ ] Log persona in ledger events (AdGenerated, AdEvaluated, AdPublished)

#### C. Frontend — NewSessionForm Persona Selector

- [ ] Add persona dropdown to NewSessionForm (in required fields section, after audience)
- [ ] Options: "Auto (recommended)" + 7 persona names with one-line descriptions:
  - "Athlete-Recruit Gatekeeper — Mother of student athlete, scholarship urgency"
  - "Proactive Suburban Optimizer — Upper-middle-class, GPA/SAT mismatch"
  - "Immigrant Family Navigator — First-gen, unfamiliar with US system"
  - "Education-First Cultural Investor — STEM professionals, mastery-focused"
  - "System Optimizer — Corporate father, process/ROI focused"
  - "Neurodivergent Advocate — Mother of child with learning differences"
  - "Burned Returner — Prior negative tutoring experience"
- [ ] Default: "Auto"

#### D. Frontend — SessionCard Persona Badge

- [ ] Show persona badge on SessionCard (e.g., "Athlete" in lightPurple)
- [ ] Only show if persona is not "auto"

#### E. Frontend — AdLibrary Persona Filter

- [ ] Add persona filter dropdown to AdLibrary tab filter bar
- [ ] Filter ads by persona tag (from ledger events)

#### F. Frontend — Overview Persona Breakdown

- [ ] If session has persona set, show persona info in Overview tab header
- [ ] If multi-persona run (future), show per-persona pass rate chart

#### G. Tests

- [ ] Backend: SessionConfig accepts persona field, validates enum
- [ ] Backend: Pipeline task passes persona to expansion
- [ ] Frontend: persona selector renders in NewSessionForm
- [ ] Dashboard: summary endpoint includes persona when set
- [ ] Minimum: 4 tests

#### H. Documentation

- [ ] Add PB-07 entry in `docs/DEVLOG.md`

---

## Files to Modify

| File | Action |
|------|--------|
| `app/api/schemas/session.py` | Add Persona enum + field to SessionConfig |
| `app/workers/tasks/pipeline_task.py` | Pass persona to pipeline |
| `app/frontend/src/views/NewSessionForm.tsx` | Add persona dropdown |
| `app/frontend/src/components/SessionCard.tsx` | Add persona badge |
| `app/frontend/src/tabs/AdLibrary.tsx` | Add persona filter |
| `app/frontend/src/tabs/Overview.tsx` | Add persona info |
| `app/frontend/src/types/session.ts` | Add Persona type |

---

## Definition of Done

- [ ] Persona selectable in session config (backend + frontend)
- [ ] Persona flows through pipeline to brief expansion and generation
- [ ] Persona badge on session cards
- [ ] Persona filter in Ad Library tab
- [ ] Tests pass
- [ ] Lint clean + frontend builds
- [ ] DEVLOG updated

---

## Estimated Time: 60–90 minutes
