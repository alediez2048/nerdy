# PB-04 Primer: Persona-Aware Brief Expansion

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PB-01 (Brand KB), PB-02 (Hook Library) must be complete. See `docs/development/tickets/PB-00-phase-plan.md`.

---

## What Is This Ticket?

PB-04 updates `generate/brief_expansion.py` to accept an optional persona parameter, inject persona-specific psychology/triggers/hooks into the expanded brief, and include offer positioning context for conversion campaigns.

### Why It Matters

- The brief is the seed of everything downstream — a persona-aware brief produces persona-relevant ads
- Injecting proven hooks gives the generator a head start vs. inventing from scratch
- Offer positioning (membership model, pricing, results claims) makes conversion ads specific and credible
- Without persona context, the generator falls back to generic "parents want SAT help" framing

---

## What Was Already Done

- `generate/brief_expansion.py`: `expand_brief(brief)` loads brand KB, fetches competitive context, calls Gemini Flash, returns `ExpandedBrief` dataclass
- `ExpandedBrief` has: `original_brief`, `audience_profile`, `brand_facts`, `competitive_context`, `emotional_angles`, `value_propositions`, `key_differentiators`, `constraints`
- PB-01: brand_knowledge.json now has 7 persona profiles with psychology, trigger, funnel_position
- PB-02: `generate/hooks.py` with `get_hooks_for_persona(persona, n, seed)`

---

## What This Ticket Must Accomplish

### Goal

Make brief expansion persona-aware — when a persona is specified, inject its psychology, proven hooks, and offer context into the expansion.

### Deliverables Checklist

#### A. Accept Persona in Brief Input

- [ ] `expand_brief(brief: dict, persona: str | None = None) -> ExpandedBrief`
- [ ] If `persona` is provided, load persona profile from brand_knowledge.json
- [ ] If `persona` is "auto" or None, default to audience-based selection (parents → suburban_optimizer, students → keep generic)

#### B. Inject Persona Context into Expansion Prompt

- [ ] Add persona section to the grounding prompt:
  ```
  TARGET PERSONA: {persona.description}
  PSYCHOLOGY: {persona.psychology}
  TRIGGER: {persona.trigger}
  FUNNEL POSITION: {persona.funnel_position}
  KEY NEEDS: {persona.key_needs}
  ```
- [ ] Instruct the LLM: "Tailor emotional angles and value propositions to this specific persona's psychology and needs."

#### C. Inject Proven Hooks

- [ ] Call `get_hooks_for_persona(persona, n=3, seed=brief_seed)` from PB-02
- [ ] Add to prompt: "PROVEN HOOKS FOR THIS PERSONA (use as inspiration, do not copy verbatim): {hook_texts}"
- [ ] Store selected hooks in ExpandedBrief for downstream attribution

#### D. Inject Offer Positioning (Conversion Goals)

- [ ] When `campaign_goal == "conversion"`, add offer context to prompt:
  - Membership model description
  - Pricing comparison vs competitors
  - Results claims (10X self-study, 2.6X group, ~100pts/month)
  - Recommended CTA for this persona
- [ ] Load from brand_knowledge.json `offer` section (PB-01)

#### E. Inject Nerdy Messaging Rules

- [ ] Add language constraints to prompt:
  - "ALWAYS use 'your child' — NEVER 'your student'"
  - "ALWAYS use 'SAT Tutoring' — NEVER 'SAT Prep'"
  - "Use specific mechanisms, not vague promises"
  - "Use calendar urgency (test dates), not fake scarcity"
- [ ] Load from brand_knowledge.json `messaging_rules` section (PB-01)

#### F. Extend ExpandedBrief Dataclass

- [ ] Add fields:
  - `persona: str | None` — the persona key used
  - `suggested_hooks: list[dict]` — hooks from the library
  - `offer_context: dict | None` — offer positioning (conversion only)
  - `messaging_rules: dict | None` — do's/don'ts injected

#### G. Tests (`tests/test_generation/test_persona_expansion.py`)

- [ ] TDD first
- [ ] Brief with `persona="athlete_recruit"` includes athlete psychology in expanded brief
- [ ] Expanded brief has `persona` field matching input
- [ ] Expanded brief has `suggested_hooks` (list, length >= 1)
- [ ] Conversion brief has `offer_context` (not None)
- [ ] Awareness brief has `offer_context` as None
- [ ] Brief with `persona=None` uses default persona selection
- [ ] Messaging rules injected into constraints
- [ ] Minimum: 7 tests

#### H. Documentation

- [ ] Add PB-04 entry in `docs/DEVLOG.md`

---

## Important Context

### Expansion Prompt Structure (after PB-04)

```
SYSTEM: You are a creative strategist for Varsity Tutors SAT Tutoring.

VERIFIED BRAND FACTS:
{brand_facts from brand_knowledge.json}

TARGET PERSONA: {persona.description}
PSYCHOLOGY: {persona.psychology}
TRIGGER: {persona.trigger}
KEY NEEDS: {persona.key_needs}

PROVEN HOOKS FOR THIS PERSONA:
1. "{hook_1}"
2. "{hook_2}"
3. "{hook_3}"

COMPETITIVE LANDSCAPE:
{competitive_context from patterns.json}

OFFER CONTEXT (conversion only):
{membership model, pricing, results claims}

MESSAGING RULES:
- ALWAYS: "your child", "SAT Tutoring", specific mechanisms
- NEVER: "your student", "SAT Prep", fake urgency, corporate jargon

BRIEF TO EXPAND:
{original_brief}
```

### Files to Modify

| File | Action |
|------|--------|
| `generate/brief_expansion.py` | Add persona param, inject persona/hooks/offer/rules into prompt, extend ExpandedBrief |
| `tests/test_generation/test_persona_expansion.py` | Create — persona expansion tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `generate/brief_expansion.py` | Current expansion logic to extend |
| `generate/hooks.py` | Hook query function (PB-02) |
| `data/brand_knowledge.json` | Persona profiles, messaging rules, offer (PB-01) |
| `generate/competitive.py` | `get_landscape_context()` already used |

---

## Definition of Done

- [ ] `expand_brief(brief, persona="athlete_recruit")` injects athlete-specific context
- [ ] Proven hooks injected into expansion prompt
- [ ] Offer positioning included for conversion goals
- [ ] Messaging rules (do's/don'ts) injected as constraints
- [ ] ExpandedBrief has persona, suggested_hooks, offer_context, messaging_rules fields
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time: 60–90 minutes

---

## After This Ticket: What Comes Next

**PB-05 (Ad Generator)** consumes the persona-enriched ExpandedBrief to generate ads with Nerdy-approved language, hooks, and CTAs.
