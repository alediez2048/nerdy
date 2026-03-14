# P1-03 Primer: Audience-Specific Brand Voice Profiles

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P0-04 (brand knowledge base) must be complete. P1-01 (brief expansion) and P1-02 (ad generator) should be complete or in progress. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P1-03 implements **audience-specific brand voice profiles** so the generator and evaluator can adapt tone based on who the ad is targeting. Varsity Tutors speaks differently to anxious parents ("authoritative, reassuring — your child is in expert hands") than to stressed students ("relatable, motivating — you've got this, here's your edge"). Each profile includes distinct tone descriptors, emotional drivers, vocabulary guidance, and few-shot examples of on-brand copy.

### Why It Matters

- **The System Knows What It Doesn't Know** (Pillar 4): A single "brand voice" is insufficient — a parent-facing ad that sounds student-facing is off-brand even if the words are technically correct. Audience-specific profiles encode this nuance.
- Brand Voice is one of the 5 evaluation dimensions with a hard floor of 5.0 (R1-Q3). Without audience-specific profiles, the evaluator has no rubric to judge voice appropriateness.
- Few-shot examples do the heavy lifting for tonal nuance (R1-Q6) — explicit rules alone are brittle. Examples demonstrate what "empowering but not arrogant" actually sounds like for each audience.
- The generator (P1-02) and evaluator (P1-04) both consume these profiles, making this a shared dependency for the entire generate-evaluate loop.

---

## What Was Already Done

- P0-04: Brand knowledge base (`data/brand_knowledge.json`) — includes brand voice attributes, audience segments, and compliance rules
- P0-05: Reference ads (`data/reference_ads.json`) — 42 real ads, many labeled by audience segment, usable as few-shot examples
- P0-06: Evaluator calibration (`evaluate/evaluator.py`) — `evaluate_ad()` and `EvaluationResult` dataclass exist; Brand Voice is already a scored dimension
- P1-01: Brief expansion (`generate/brief_expansion.py`) — `ExpandedBrief` includes `audience_profile` field
- P1-02: Ad generator (`generate/ad_generator.py`) — consumes voice profile for prompt construction

---

## What This Ticket Must Accomplish

### Goal

Build the brand voice profile module that provides audience-specific voice profiles with few-shot examples, selectable by audience segment from the brief. Both the generator and evaluator consume these profiles.

### Deliverables Checklist

#### A. Brand Voice Module (`generate/brand_voice.py`)

- [ ] `get_voice_profile(audience: str) -> VoiceProfile`
  - Input: audience segment string (e.g., "parents", "students", "families")
  - Loads audience data from the `audiences` section of `data/brand_knowledge.json`
  - Returns the matching `VoiceProfile` or falls back to a default profile with a logged warning
- [ ] `VoiceProfile` dataclass:
  - `audience`: the target audience segment
  - `tone`: list of tone descriptors (e.g., ["authoritative", "reassuring", "empathetic"] for parents)
  - `emotional_drivers`: what motivates this audience (e.g., parent worry about college admissions, student test anxiety)
  - `vocabulary_guidance`: words/phrases to prefer and avoid for this audience
  - `few_shot_examples`: 3-5 on-brand ad copy snippets demonstrating the voice for this audience
  - `anti_examples`: 1-2 off-brand examples showing what to avoid (too salesy, too casual, wrong tone)
  - `brand_constants`: core brand attributes that apply across ALL audiences (empowering, knowledgeable, approachable, results-focused)
- [ ] `get_voice_for_prompt(audience: str) -> str`
  - Convenience function that formats the `VoiceProfile` into a prompt-injectable string
  - Used by the generator (P1-02) to embed voice guidance in the generation prompt
  - Includes few-shot examples formatted as labeled examples
- [ ] `get_voice_for_evaluation(audience: str) -> str`
  - Convenience function that formats the `VoiceProfile` into an evaluator-friendly rubric string
  - Used by the evaluator (P1-04) to score Brand Voice against audience-specific criteria
  - Includes examples of 1-score (off-brand) and 10-score (perfectly on-brand) for the audience
- [ ] Parent-facing profile:
  - Tone: authoritative, reassuring, empathetic, results-focused
  - Drivers: anxiety about college admissions, desire for expert guidance, value for money
  - Examples: drawn from parent-targeted reference ads in `data/reference_ads.json`
- [ ] Student-facing profile:
  - Tone: relatable, motivating, confident, peer-level
  - Drivers: test anxiety, desire for quick results, competitive edge, social proof from peers
  - Examples: drawn from student-targeted reference ads in `data/reference_ads.json`
- [ ] Default/family profile for briefs that target both or specify "families"

#### B. Tests (`tests/test_generation/test_brand_voice.py`)

- [ ] TDD first
- [ ] Test parent audience returns parent-facing profile
- [ ] Test student audience returns student-facing profile
- [ ] Test unknown audience falls back to default profile (not crash)
- [ ] Test profile contains all required VoiceProfile fields
- [ ] Test few-shot examples are non-empty
- [ ] Test `get_voice_for_prompt()` returns a non-empty formatted string
- [ ] Test `get_voice_for_evaluation()` returns a non-empty formatted string
- [ ] Test brand constants are present in all profiles regardless of audience
- [ ] Minimum: 7+ tests

#### C. Integration

- [ ] Generator (P1-02): update `_build_generation_prompt()` to call `get_voice_for_prompt(audience)` and embed the result
- [ ] Evaluator (P1-04): prepare the voice profile interface so the evaluator can call `get_voice_for_evaluation(audience)` when scoring Brand Voice
- [ ] Log profile selection events to decision ledger via `log_event()` from `iterate/ledger.py`

#### D. Documentation

- [ ] Add P1-03 entry in `docs/DEVLOG.md`

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
| Audience-specific brand voice profiles | R1-Q6 | "Parent-facing" (authoritative, reassuring) and "Student-facing" (relatable, motivating) with few-shot examples. Few-shot does the heavy lifting for tonal nuance. |
| Brand Voice floor constraint | R1-Q3 | Brand Voice has a hard floor of 5.0 — ads below this are rejected regardless of other scores. |
| Shared patterns, isolated content | R3-Q8 | Voice profiles are structural (shared). Specific ad content is isolated per campaign. |

### Files to Create

| File | Why |
|------|-----|
| `generate/brand_voice.py` | Audience-specific voice profiles with few-shot examples |
| `tests/test_generation/test_brand_voice.py` | Voice profile tests |

### Files to Modify

| File | Why |
|------|-----|
| `generate/ad_generator.py` | Integrate voice profile into generation prompt |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `data/brand_knowledge.json` | `audiences` section — source of audience data, tone attributes, brand voice rules |
| `data/reference_ads.json` | Source of few-shot examples (filter by audience segment) |
| `generate/brief_expansion.py` | `ExpandedBrief.audience_profile` — how audience is passed through the pipeline |
| `generate/ad_generator.py` | Where the voice profile will be injected into generation prompts |
| `evaluate/evaluator.py` | How Brand Voice is currently scored — will consume the evaluation rubric |
| `docs/reference/prd.md` (R1-Q6, R1-Q3) | Full rationale for audience profiles and floor constraints |

---

## Definition of Done

- [ ] `get_voice_profile("parents")` returns a parent-facing profile with correct tone and few-shot examples
- [ ] `get_voice_profile("students")` returns a student-facing profile with correct tone and few-shot examples
- [ ] Unknown audience falls back gracefully to a default profile
- [ ] `get_voice_for_prompt()` produces a string ready for generator prompt injection
- [ ] `get_voice_for_evaluation()` produces a string ready for evaluator rubric
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Committed on `develop`

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**P1-04 (Chain-of-thought evaluator)** will call `get_voice_for_evaluation()` when scoring the Brand Voice dimension, giving it audience-specific rubric criteria.

**P1-05 (Campaign-goal-adaptive weighting)** defines the weight profiles that include the Brand Voice floor of 5.0 — the voice profiles from this ticket provide the evaluator the context to score that dimension accurately.

The generator (P1-02) should be updated to call `get_voice_for_prompt()` once this ticket is complete, if it was not wired in during this session.
