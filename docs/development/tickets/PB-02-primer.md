# PB-02 Primer: Persona-Specific Hook Library

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PB-01 (Brand KB) must be complete. See `docs/development/tickets/PB-00-phase-plan.md`.

---

## What Is This Ticket?

PB-02 creates a structured hook library (`data/hooks_library.json`) with all 80+ proven hooks from the Nerdy supplementary, organized by persona, and a query module (`generate/hooks.py`) to inject relevant hooks into brief expansion.

### Why It Matters

- The supplementary doc contains 80+ field-tested hooks that convert real parents — these aren't generic AI output
- Each hook targets a specific persona psychology (fear, control, frustration, overwhelm, etc.)
- Injecting proven hooks into brief expansion gives the generator a head start vs. inventing hooks from scratch
- Seed-based selection ensures diversity across pipeline runs

---

## What Was Already Done

- `data/competitive/patterns.json`: 40 competitive pattern records with hook_type, hook_text, emotional_register
- `generate/competitive.py`: `load_patterns()`, `query_patterns()` — queries competitive DB
- `generate/ad_generator.py`: `_select_structural_atoms()` already selects hook patterns from the competitive DB
- PB-01: brand_knowledge.json now has 7 persona profiles with psychology and funnel_position

---

## What This Ticket Must Accomplish

### Goal

Create the hook library data file and a query module that returns persona-specific hooks with deterministic diversity.

### Deliverables Checklist

#### A. Hook Library Data (`data/hooks_library.json`)

- [ ] Array of hook objects, each with:
  - `hook_id`: unique identifier (e.g., "hook_athlete_01")
  - `persona`: persona key matching brand_knowledge.json (e.g., "athlete_recruit")
  - `category`: broader category (e.g., "athlete", "scholarship", "test_anxiety")
  - `hook_text`: the exact hook line from the supplementary
  - `psychology`: the emotional lever (e.g., "Fear of missed window + urgency")
  - `cta_text`: the recommended CTA for this hook
  - `cta_style`: "micro_commitment", "direct_action", "information_seeking"
  - `funnel_position`: "early", "mid", "late"

- [ ] All hooks from supplementary sections:
  - Athlete Families (8 hooks)
  - Proactive Suburban Optimizer (9 hooks)
  - Scholarship / Financial (7 hooks)
  - Khan Academy Failures (7 hooks)
  - Online Skeptic Reframe (7 hooks)
  - Urgency / Bad Score (6 hooks)
  - Immigrant Family (8 hooks)
  - Neurodivergent / Learning Differences (8 hooks)
  - Test Anxiety (8 hooks)
  - Accountability (9 hooks)
  - School Failed Them (8 hooks)
  - Education-First Cultural Investor (6 hooks)
  - Parent-Child Relationship (6 hooks)
  - Sibling / Second Child (4 hooks)
  - Burned Returner (8 hooks)

- [ ] Total: 80+ hooks

#### B. Hook Query Module (`generate/hooks.py`)

- [ ] `load_hooks() -> list[dict]` — loads hooks_library.json, caches in memory
- [ ] `get_hooks_for_persona(persona: str, n: int = 3, seed: int = 0) -> list[dict]`
  - Filters hooks by persona key
  - Falls back to category match if persona has no exact matches
  - Seed-based shuffle for deterministic diversity
  - Returns top `n` hooks
- [ ] `get_hooks_for_category(category: str, n: int = 3, seed: int = 0) -> list[dict]`
  - Filters by category (for broader searches)
- [ ] `get_all_personas() -> list[str]` — returns list of unique persona keys in the library

#### C. Tests (`tests/test_generation/test_hooks.py`)

- [ ] TDD first
- [ ] All hooks loaded (count >= 80)
- [ ] Each hook has required fields (hook_id, persona, hook_text, psychology, cta_text)
- [ ] `get_hooks_for_persona("athlete_recruit")` returns only athlete hooks
- [ ] `get_hooks_for_persona()` with different seeds returns different orderings
- [ ] `get_hooks_for_persona()` with same seed returns same result (deterministic)
- [ ] No duplicate hook_ids in the library
- [ ] Every persona in brand_knowledge.json has at least 3 hooks
- [ ] Minimum: 7 tests

#### D. Documentation

- [ ] Add PB-02 entry in `docs/DEVLOG.md`

---

## Important Context

### Hook-to-Persona Mapping

Some hooks map to multiple personas. The `category` field handles this:

| Category | Primary Persona | Also Relevant To |
|----------|----------------|-----------------|
| athlete | athlete_recruit | — |
| suburban_optimizer | suburban_optimizer | — |
| scholarship | athlete_recruit, immigrant_navigator | All parent personas |
| khan_failures | suburban_optimizer, cultural_investor | All parent personas |
| online_skeptic | All parent personas | — |
| urgency | All parent personas | — |
| immigrant | immigrant_navigator | — |
| neurodivergent | neurodivergent_advocate | — |
| test_anxiety | suburban_optimizer, neurodivergent_advocate | All parent personas |
| accountability | suburban_optimizer, burned_returner | All parent personas |
| school_failed | All parent personas | — |
| education_investor | cultural_investor | — |
| parent_relationship | All parent personas | — |
| sibling | suburban_optimizer | All parent personas |
| burned_returner | burned_returner | — |

### Files to Create

| File | Why |
|------|-----|
| `data/hooks_library.json` | Structured hook data |
| `generate/hooks.py` | Hook query module |
| `tests/test_generation/test_hooks.py` | Hook tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `/Users/jad/Downloads/C4_Automatic_Ad_Generator_Supplementary.md` | Source hooks (lines 226–467) |
| `data/brand_knowledge.json` | Persona keys to match against |
| `generate/competitive.py` | Pattern for loading/querying structured data |
| `generate/seeds.py` | Seed-based deterministic selection pattern |

---

## Definition of Done

- [ ] 80+ hooks in hooks_library.json with all required fields
- [ ] `get_hooks_for_persona()` returns persona-filtered, seed-diverse hooks
- [ ] Every persona has at least 3 hooks
- [ ] No duplicate hook_ids
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**PB-04 (Brief Expansion)** will inject hooks from this library into the expanded brief, giving the generator proven starting points.
