# PB-10 Primer: Pipeline Config → Persona Flow

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PB-01–PB-09 complete. Session form has persona dropdown. brand_knowledge.json has 7 personas with psychology, triggers, preferred CTAs. Brief expansion accepts persona_profile param but pipeline_task.py doesn't pass it.

---

## What Is This Ticket?

PB-10 completes the wiring from session form → pipeline task → brief expansion → ad generator → visual spec. The persona selected by the user on the session form currently stops at the database — it never reaches the pipeline modules. This ticket makes the persona selection flow end-to-end.

### Why It Matters

- Without this, persona selection is cosmetic — it appears on the form but doesn't change the output
- This is the keystone ticket: once persona flows through, all downstream modules (hooks, messaging, visual spec) can use it
- Enables the marketer experience: select "Athlete Recruit" → get ads about scholarship urgency, not generic SAT prep

---

## What Was Already Done

- PB-07: Session form has persona dropdown (8 options including auto)
- PB-01: brand_knowledge.json has 7 persona profiles with full data
- PB-04: brief_expansion.py `_build_expansion_prompt()` accepts persona_profile, hooks, offer, messaging params
- PB-04: `expand_brief()` accepts persona parameter
- Pipeline task extracts ad_count, cycle_count, quality_threshold, image_enabled from session config

---

## What This Ticket Must Accomplish

### Goal

Make the persona selected on the session form flow through pipeline_task → batch_processor → expand_brief → generate_ad → extract_visual_spec.

### Deliverables

#### A. Pipeline Task (`app/workers/tasks/pipeline_task.py`)

- [ ] Extract `persona` from `session_row.config` (default: "auto")
- [ ] Add `persona` to `pipeline_config` dict passed to `process_batch()`
- [ ] When persona is "auto", don't pass persona (let pipeline use defaults)

#### B. Batch Processor (`iterate/batch_processor.py`)

- [ ] Read `persona` from config dict
- [ ] Load persona profile from brand_knowledge.json when persona is set
- [ ] Pass persona_profile to `expand_brief(brief, persona=persona_name)`
- [ ] Pass persona to `generate_ad()` (for voice profile selection)
- [ ] Pass persona to `extract_visual_spec()` (for persona-specific imagery)

#### C. Visual Spec (`generate/visual_spec.py`)

- [ ] Update `extract_visual_spec()` to accept optional `persona` parameter
- [ ] When persona is set, inject persona-specific visual direction into prompt:
  - athlete_recruit → sports/recruiting/campus imagery, competitive energy
  - suburban_optimizer → organized study space, professional, clean
  - immigrant_navigator → diverse family, warm, welcoming
  - cultural_investor → modern study setup, technology, multiple resources
  - system_optimizer → data dashboard aesthetic, minimal, McKinsey-style
  - neurodivergent_advocate → warm, inclusive, adaptive learning, comfortable setting
  - burned_returner → transformation, fresh start, new beginning

#### D. Tests

- [ ] Test persona extracted from session config
- [ ] Test persona=auto doesn't inject persona context
- [ ] Test persona=athlete_recruit changes visual spec prompt
- [ ] Test persona flows through to expand_brief
- [ ] 6+ tests

---

## Definition of Done

- [ ] Creating session with persona="athlete_recruit" produces persona-aware ads
- [ ] Visual spec reflects persona (athlete imagery, not generic tutoring)
- [ ] Brief expansion includes persona psychology and preferred CTA
- [ ] persona="auto" produces same output as before (no regression)
- [ ] Tests pass, lint clean, DEVLOG updated
