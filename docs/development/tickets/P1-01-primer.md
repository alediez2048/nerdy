# P1-01 Primer: Brief Expansion Engine

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P0-01 through P0-10 (foundation phase) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P1-01 implements the **LLM-powered brief expansion engine** that transforms minimal campaign briefs into rich, grounded creative briefs. A minimal brief might say "SAT prep for parents, awareness campaign." The expansion engine enriches this with verified brand facts, audience insights, competitive landscape context, and emotional angles — all without hallucinating a single claim.

### Why It Matters

- **Prevention Over Detection Over Correction** (Pillar 2): Grounding constraints prevent hallucinated claims at the source, before they reach the generator or evaluator.
- **Every Token Is an Investment** (Pillar 3): A well-expanded brief means the generator produces higher-quality first drafts, reducing costly regeneration cycles.
- Brief expansion is the first step in the pipeline flow: Brief -> **Expand (R3-Q5)** -> Generate -> Evaluate. Everything downstream depends on the quality of this expansion.
- Competitive context injection (Section 4.8.6) ensures generated ads differentiate from competitor patterns rather than accidentally mimicking them.

---

## What Was Already Done

- P0-04: Brand knowledge base (`data/brand_knowledge.json`) — verified facts about Varsity Tutors, audiences, compliance rules
- P0-05: Reference ad collection (`data/reference_ads.json`) — 42 real ads with baseline scores
- P0-09/P0-10: Competitive pattern database (`data/competitive/patterns.json`) — 40 structured pattern records from 4 competitors, with query interface in `generate/competitive.py`
- P0-08: Retry infrastructure (`iterate/retry.py`) — `retry_with_backoff()` for resilient API calls
- P0-01: Config (`data/config.yaml`) — all tunable parameters
- P0-02: Decision ledger (`iterate/ledger.py`) — `log_event()` for tracking all pipeline events

---

## What This Ticket Must Accomplish

### Goal

Build the brief expansion module that takes a minimal brief and produces a rich, grounded creative brief by combining verified brand knowledge with competitive landscape context, ready for the ad copy generator (P1-02).

### Deliverables Checklist

#### A. Brief Expansion Module (`generate/brief_expansion.py`)

- [ ] `expand_brief(brief: dict) -> ExpandedBrief`
  - Input: minimal brief with fields like `campaign_goal` (awareness/conversion), `audience` (parents/students), `product` (e.g., "SAT prep"), optional `angle` or `hook`
  - Loads verified facts from `data/brand_knowledge.json` relevant to the audience and product
  - Calls `get_landscape_context(audience, product)` from `generate/competitive.py` to inject competitive positioning
  - Sends grounded expansion prompt to Gemini (Flash) via `retry_with_backoff()`
  - Output: `ExpandedBrief` dataclass with:
    - `original_brief`: the input brief unchanged
    - `audience_profile`: audience segment details (pain points, motivations)
    - `brand_facts`: list of verified facts used (traceability)
    - `competitive_context`: landscape summary from pattern database
    - `emotional_angles`: 2-3 emotional hooks grounded in audience psychology
    - `value_propositions`: 2-3 specific, factual value props (no invented statistics)
    - `key_differentiators`: what separates VT from competitors identified in landscape
    - `constraints`: any compliance rules from brand KB
- [ ] `_build_expansion_prompt(brief: dict, brand_facts: dict, competitive_context: dict) -> str`
  - Constructs the grounding-constrained prompt
  - Explicitly instructs: "Use ONLY the following verified facts. Do NOT invent statistics, testimonials, or claims."
  - Includes competitive landscape as "market context" section
  - Includes audience-specific pain points from brand KB
- [ ] `_parse_expansion_response(response: str) -> ExpandedBrief`
  - Parses structured JSON response from Gemini
  - Validates all brand facts against source (no hallucinated claims)
  - Falls back gracefully if response is malformed (returns partial expansion with warning)
- [ ] `ExpandedBrief` dataclass definition with all fields above

#### B. Tests (`tests/test_generation/test_brief_expansion.py`)

- [ ] TDD first
- [ ] Test expansion includes only verified brand facts (no hallucination)
- [ ] Test competitive context is included in expanded brief
- [ ] Test audience-appropriate facts selected (parent brief gets parent-relevant facts)
- [ ] Test malformed API response handled gracefully (partial expansion)
- [ ] Test retry logic is invoked on API failure
- [ ] Test minimal brief with only required fields expands successfully
- [ ] Test expanded brief contains all required ExpandedBrief fields
- [ ] Minimum: 7+ tests

#### C. Integration

- [ ] Wire into pipeline flow: brief expansion is the entry point after brief intake
- [ ] Ensure `ExpandedBrief` output is compatible with P1-02 generator input format
- [ ] Log expansion events to decision ledger via `log_event()` from `iterate/ledger.py`

#### D. Documentation

- [ ] Add P1-01 entry in `docs/DEVLOG.md`

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
| LLM expansion with grounding | R3-Q5 | Expand using ONLY verified facts. Creative framing around verified facts. Separate what the system knows from how it frames it. |
| Competitive landscape injection | Section 4.8.6 | Inject top competitive patterns as "landscape context" during brief expansion. |
| Distilled context objects | R2-Q4 | Pass focused context objects between stages, not raw data dumps. |

### Files to Create

| File | Why |
|------|-----|
| `generate/brief_expansion.py` | Brief expansion engine with grounding constraints |
| `tests/test_generation/test_brief_expansion.py` | Expansion tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `generate/competitive.py` | `get_landscape_context()` — the competitive context you inject |
| `data/brand_knowledge.json` | The verified facts source — your grounding constraint |
| `data/competitive/patterns.json` | Raw pattern data (competitive.py wraps this) |
| `iterate/retry.py` | `retry_with_backoff()` for resilient Gemini calls |
| `iterate/ledger.py` | `log_event()` for logging expansion events |
| `data/config.yaml` | Model selection, temperature, and other parameters |
| `docs/reference/prd.md` (R3-Q5, Section 4.8.6) | Full rationale for grounding and competitive injection |

---

## Definition of Done

- [ ] `expand_brief()` produces a rich `ExpandedBrief` from a minimal input brief
- [ ] All brand facts in the expansion are traceable to `brand_knowledge.json` (no hallucination)
- [ ] Competitive landscape context from `get_landscape_context()` is included
- [ ] Malformed API responses handled gracefully
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Committed on `develop`

---

## Estimated Time: 60–90 minutes

---

## After This Ticket: What Comes Next

**P1-02 (Ad copy generator)** consumes the `ExpandedBrief` output from this ticket. The generator uses reference-decompose-recombine (R2-Q1) to produce ad copy from the expanded brief + structural atoms from the pattern database.

**P1-03 (Audience-specific brand voice profiles)** builds the voice profiles that the generator will use — but the brief expansion already selects audience-appropriate facts, so P1-03 and P1-01 are complementary rather than sequential.
