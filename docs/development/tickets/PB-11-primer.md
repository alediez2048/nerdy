# PB-11 Primer: Creative Direction + Key Message Form Fields

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PB-10 (persona flow wired). Session form has persona, audience, campaign goal, ad count. Missing: creative direction, key message, copy-on-image toggle.

---

## What Is This Ticket?

PB-11 adds marketer-focused creative control fields to the New Session form. Currently the form controls pipeline parameters (cycle count, threshold) but not the creative output. A Nerdy marketing employee should be able to specify what kind of ads they want — not just how the pipeline runs.

### Why It Matters

- All generated ads currently look similar (warm educational scenes) because there's no creative direction input
- brand_knowledge.json has a "creative_briefs" section (e.g., "The Gap Report" — McKinsey-style data aesthetic) that's never used
- Persona-specific CTAs exist but aren't surfaced to the user
- The "Key Message" should pre-fill based on persona selection (e.g., selecting Athlete Recruit pre-fills "SAT score needed for scholarship eligibility")

---

## What This Ticket Must Accomplish

### Goal

Add Creative Direction, Key Message, Creative Brief preset, and Copy-on-Image toggle to the session form. Pass these through to the pipeline.

### Deliverables

#### A. New Form Fields (`app/frontend/src/views/NewSessionForm.tsx`)

Add a "Creative Direction" section between the required fields and Advanced Settings:

- [ ] **Key Message** (text input)
  - Placeholder: "What's the core message?"
  - Pre-fills when persona changes:
    - athlete_recruit → "SAT score needed for scholarship eligibility"
    - suburban_optimizer → "Your child's SAT doesn't match their GPA"
    - immigrant_navigator → "Expert guidance through US college admissions"
    - system_optimizer → "Close the score gap in 10 weeks"
    - neurodivergent_advocate → "Tutoring that adapts to how your child learns"
    - burned_returner → "This time will be different — here's why"
    - auto → "" (empty, let pipeline decide)

- [ ] **Creative Brief** (dropdown)
  - Options: Auto, Gap Report (data dashboard), UGC Testimonial, Before/After Score, Lifestyle/Aspirational, Stat-Focused
  - Default: Auto

- [ ] **Copy on Image** (toggle, default off)
  - When enabled, tells image generator to include headline text in the image
  - Label: "Include headline text on generated images"

#### B. Schema Update (`app/api/schemas/session.py`)

- [ ] Add `key_message: str = ""` to SessionConfig
- [ ] Add `creative_brief: str = "auto"` to SessionConfig
- [ ] Add `copy_on_image: bool = False` to SessionConfig

#### C. Pipeline Flow

- [ ] `pipeline_task.py`: extract key_message, creative_brief, copy_on_image from config
- [ ] `batch_processor.py`: pass key_message to brief dict, pass creative_brief to visual spec
- [ ] `generate/visual_spec.py`: when creative_brief is set, use it as primary visual direction instead of generic defaults
- [ ] `generate/image_generator.py`: when copy_on_image=True, append headline text to image generation prompt

#### D. Tests

- [ ] Test key_message pre-fills on persona change (frontend, manual)
- [ ] Test creative_brief flows through to visual spec prompt
- [ ] Test copy_on_image appends text to image prompt
- [ ] Test defaults work (auto creative_brief, no key_message)
- [ ] 6+ tests

---

## Definition of Done

- [ ] New Session form shows Key Message, Creative Brief, Copy on Image fields
- [ ] Key Message pre-fills based on persona selection
- [ ] Creative Brief "Gap Report" produces data-dashboard-style images
- [ ] Copy on Image toggle adds headline text to image generation
- [ ] All defaults produce same output as before (no regression)
- [ ] Tests pass, lint clean, DEVLOG updated
