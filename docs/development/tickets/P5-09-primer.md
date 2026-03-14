# P5-09 Primer: Demo Video

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P5-08 (technical writeup), P5-01 through P5-06 (dashboard) should be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P5-09 produces the **demo video (7 minutes max)** using a Problem-Solution-Proof narrative arc. This is a required submission deliverable. The chosen format is a Narrated Pipeline Replay (R2-Q10 / R4-Q5) — a chronological walkthrough of the system's operation with reasoning visible throughout.

### Why It Matters

- Submission requirements explicitly list "Demo video or live walkthrough"
- The demo is the reviewer's primary window into the system in action
- **The Reviewer Is a User, Too** (Pillar 8): The demo respects their time (R4-Q5)
- A great system that's hard to evaluate will score worse than a good system that makes its value obvious
- Automatic deduction of -10 points for "No working demo"

---

## What Was Already Done

- P5-01 through P5-06: Dashboard with all 8 panels — shown in Act 3
- P5-07: Decision log — referenced for architectural reasoning
- P5-08: Technical writeup — provides the narrative script outline
- All pipeline phases (P0-P4): Working system to demonstrate

---

## What This Ticket Must Accomplish

### Goal

Produce a pre-recorded, edited demo video (7 minutes or less) following a three-act Problem-Solution-Proof structure that showcases the system's capabilities, reasoning, and results.

### Deliverables Checklist

#### A. Video Script / Storyboard

Plan the video before recording. Each act has a time budget:

- [ ] **Act 1: The Problem (~1.5 min)** — Naive approach fails
  - Show what happens when you just ask an LLM to "write a Facebook ad"
  - Demonstrate the output is generic, off-brand, scores poorly on the 5 dimensions
  - Evaluate the naive ad with the calibrated evaluator — show the low scores
  - Key message: "Generation is easy. Knowing what's good is hard."

- [ ] **Act 2: The Architecture (~2 min)** — How the system solves this
  - High-level pipeline overview (brief -> expand -> generate -> evaluate -> iterate)
  - Key architectural decisions: quality ratchet, tiered routing, checkpoint-resume
  - The 5 quality dimensions and how they're scored independently
  - The feedback loop: weakest dimension identification -> targeted regeneration
  - Keep it visual — diagrams, code structure, flow charts

- [ ] **Act 3: The Proof (~3.5 min)** — Results with evidence
  - [ ] **Before/after pair**: Show a specific ad's journey from first generation (low score) through iterations to final publishable version (high score)
  - [ ] **Quality ratchet**: Show the threshold increasing over batches — standards only go up
  - [ ] **Self-healing**: Demonstrate the system detecting a quality drop and auto-correcting (if P4-02 complete)
  - [ ] **Cost dashboard**: Show token economics — cost per ad, cost per publishable ad, model routing breakdown
  - [ ] **Top 3 ads**: Display the three highest-scoring ads with their scores and rationales
  - [ ] **Dashboard walkthrough**: Navigate the live dashboard showing quality trends, dimension deep-dive, ad library

#### B. Recording Guidelines

- [ ] Pre-recorded and edited (not a live demo)
- [ ] 7 minutes maximum — respect the reviewer's time
- [ ] Clear audio narration throughout
- [ ] Screen recordings of actual system output (not mockups)
- [ ] Dashboard must be shown in Act 3 (acceptance criterion)
- [ ] Terminal output visible where relevant (pipeline execution, scores)

#### C. Output

- [ ] Video file or link in `docs/deliverables/` (or hosted externally with link in README)
- [ ] Optional: `docs/deliverables/demo-script.md` with the narration script

#### D. Documentation

- [ ] Add P5-09 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/P5-09-demo-video
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Demo format | R2-Q10, R4-Q5 | Narrated Pipeline Replay — chronological walkthrough with reasoning |
| Three-act structure | PRD P5-09 | Problem (naive fails) -> Solution (architecture) -> Proof (results + dashboard) |
| Time constraint | requirements.md | "Demo video or live walkthrough" — edited to 7 min max |

### Files to Create

| File | Why |
|------|-----|
| `docs/deliverables/demo-script.md` | Optional narration script for recording |
| Video file or external link | The demo video itself |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `docs/deliverables/writeup.md` | Architecture summary for Act 2 narration |
| `docs/deliverables/decisionlog.md` | Key decisions to highlight in the demo |
| Dashboard HTML files | The dashboard to walk through in Act 3 |
| `docs/reference/requirements.md` (line 197) | "Demo video or live walkthrough" requirement |
| `docs/reference/interviews.md` (R2-Q10) | Narrated Pipeline Replay rationale |

---

## Definition of Done

- [ ] Video is pre-recorded and edited
- [ ] Video is 7 minutes or less
- [ ] Three-act structure: Problem -> Solution -> Proof
- [ ] Act 1 shows naive approach failing with low evaluation scores
- [ ] Act 2 explains architecture at a high level
- [ ] Act 3 shows before/after pair, quality ratchet, self-healing, cost dashboard, top 3 ads
- [ ] Dashboard is shown in Act 3
- [ ] Clear audio narration throughout
- [ ] Video file or link is accessible from the repo
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 90–120 minutes (scripting + recording + editing)

---

## After This Ticket: What Comes Next

**P5-10** (Generated ad library export) packages the ad data that the demo references. **P5-11** (README) ties everything together with setup instructions and links to the demo.
