# P0-09 Primer: Competitive Pattern Database -- Initial Scan

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot -- Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P0-05 (reference ad collection) should be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P0-09 builds the **competitive pattern database** by analyzing 6 competitors' active Facebook ads via the Meta Ad Library. Using Claude in Chrome, extract structured pattern records from 8--10 ads per competitor and store them in `data/competitive/patterns.json`. This is not raw ad collection -- it is structured intelligence extraction: hook types, value proposition structures, CTA styles, emotional registers, and visual patterns.

### Why It Matters

- **Competitive intelligence** (+10 bonus points): One of the highest-value bonus opportunities in the project
- **Decomposition Is the Architecture** (Pillar 1): Competitor ads become queryable structural patterns, not opaque blobs
- **Cold-start bootstrapping** (R1-Q8): Pattern data supplements reference ads for calibration and generation grounding
- **Brief expansion differentiation** (P1-01): The generator needs competitive landscape context to produce ads that stand out
- Without this, the pipeline generates in a vacuum with no awareness of what competitors are doing

---

## What Was Already Done

- P0-05: Reference ad collection (20--30 competitor ads collected, structural atoms decomposed)
- P0-04: Brand knowledge base with verified Varsity Tutors facts
- Competitor list defined: Varsity Tutors, Kaplan, Princeton Review, Khan Academy, Chegg, Sylvan Learning

---

## What This Ticket Must Accomplish

### Goal

Analyze 6 competitors' active Facebook ads via Meta Ad Library. Extract structured pattern records (8--10 ads each). Write competitor strategy summaries. Store everything in a validated JSON file.

### Deliverables Checklist

#### A. Implementation -- Pattern Extraction (`data/competitive/patterns.json`)

- [ ] Visit Meta Ad Library for each of 6 competitors: Varsity Tutors, Kaplan, Princeton Review, Khan Academy, Chegg, Sylvan Learning
- [ ] Extract 8--10 active ads per competitor (48--60 ads total)
- [ ] For each ad, create a structured pattern record containing:
  - `competitor`: brand name
  - `ad_id`: unique identifier
  - `hook_type`: question, stat, story, fear, testimonial, etc.
  - `value_prop_structure`: how the value proposition is framed
  - `cta_style`: free-trial, sign-up, learn-more, book-now, etc.
  - `emotional_register`: anxiety, aspiration, urgency, empowerment, etc.
  - `visual_patterns`: image style, color palette, layout approach
  - `audience_target`: parents, students, or both
  - `campaign_goal_guess`: awareness, conversion, retargeting
  - `primary_text_summary`: condensed version of the ad copy
  - `tags`: searchable tags for query interface (P0-10)
- [ ] JSON validates against a defined schema
- [ ] Schema file created at `data/competitive/schema.json`

#### B. Competitor Strategy Summaries

- [ ] One strategy summary per competitor covering:
  - Dominant hook types used
  - Recurring value propositions
  - CTA patterns
  - Emotional positioning
  - Visual identity patterns
  - Audience targeting approach
- [ ] Summaries stored in `data/competitive/summaries.json` or as a section within `patterns.json`

#### C. Tests

- [ ] Validate JSON structure against schema
- [ ] Verify all 6 competitors have 8--10 records each
- [ ] Verify all required fields are populated (no nulls in required fields)
- [ ] Verify tags field is non-empty for all records

#### D. Documentation

- [ ] Add P0-09 entry in `docs/DEVLOG.md`
- [ ] Document extraction methodology (which prompts used, how ads were selected)

---

## Branch & Merge Workflow

All work is done directly on `develop`. No feature branches.

```bash
git switch develop && git pull
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Competitive intelligence | R2-Q2 | Structured pattern extraction -- queryable patterns, not raw ads |
| Decomposition | Pillar 1 | Competitor ads decomposed into structural patterns (hook, CTA, emotion, visual) |
| Cold-start | R1-Q8 | Competitive patterns bootstrap the pipeline before generation begins |

### Files to Create

| File | Why |
|------|-----|
| `data/competitive/patterns.json` | Structured pattern records for all 6 competitors |
| `data/competitive/schema.json` | JSON schema for pattern record validation |
| `data/competitive/summaries.json` | Per-competitor strategy summaries |

### Files to Modify

| File | Why |
|------|-----|
| `docs/DEVLOG.md` | Add P0-09 entry |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `data/reference_ads.json` (P0-05) | Existing reference ad structure for consistency |
| `data/pattern_database.json` (P0-05) | Structural atom format to align with |
| `prd.md` (Section 4.8) | Full competitive intelligence architecture spec |
| `docs/reference/prd.md` (R2-Q2) | Structured pattern extraction rationale |

---

## Definition of Done

- [ ] Pattern records for all 6 competitors (8--10 ads each, 48--60 total)
- [ ] JSON validates against schema
- [ ] All required fields populated
- [ ] Competitor strategy summaries written
- [ ] Extraction methodology documented
- [ ] DEVLOG updated
- [ ] Committed on `develop`

---

## Estimated Time: 90--120 minutes

(Semi-automated process: browsing Meta Ad Library + Claude extraction + manual review)

---

## After This Ticket: What Comes Next

- **P0-10** (Competitive pattern query interface) -- builds the `query_patterns()` function that queries this database
- **P1-01** (Brief expansion engine) -- injects competitive landscape context from the pattern database into expanded briefs
- **P4-03** (Competitive intelligence -- automated refresh) -- extends this database with trend tracking and automated refresh
