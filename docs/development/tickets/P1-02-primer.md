# P1-02 Primer: Ad Copy Generator

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P1-01 (brief expansion) must be complete. P0-03 (seeds), P0-05 (reference ads), P0-09/P0-10 (competitive patterns) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P1-02 implements the **ad copy generator** using the reference-decompose-recombine approach (R2-Q1). Instead of prompting an LLM to "write a good ad," the generator decomposes high-performing ads into structural atoms (hook type, body pattern, CTA style, emotional angle), then recombines proven elements with the expanded brief and brand voice profile to produce complete Meta ad copy.

### Why It Matters

- **Learning Is Structural** (Pillar 6): The system learns what works by decomposing successful patterns, not by vague "write better" prompts. Structural atoms are reusable and measurable.
- **Every Token Is an Investment** (Pillar 3): Reference-decompose-recombine produces higher-quality first drafts than naive generation, reducing regeneration cycles and token spend.
- This is the core generation step in the pipeline: Expand -> **Generate (R2-Q1)** -> Evaluate. The generator produces the actual ad creative that users see.
- Competitive intelligence feeds directly into the generator (Section 4.8.6) — structural atoms drawn from the pattern database ensure ads are competitive-aware.

---

## What Was Already Done

- P1-01: Brief expansion engine (`generate/brief_expansion.py`) — `expand_brief()` produces `ExpandedBrief` with grounded facts and competitive context
- P0-03: Seed infrastructure (`generate/seeds.py`) — `get_ad_seed()` for deterministic generation, `load_global_seed()`
- P0-05: Reference ads (`data/reference_ads.json`) — 42 real ads with baseline scores and structural labels
- P0-09/P0-10: Competitive patterns (`data/competitive/patterns.json`) — 40 structured pattern records; `generate/competitive.py` provides `load_patterns()`, `query_patterns()`
- P0-08: Retry infrastructure (`iterate/retry.py`) — `retry_with_backoff()` for resilient API calls
- P0-02: Decision ledger (`iterate/ledger.py`) — `log_event()` for tracking generation events
- P0-01: Config (`data/config.yaml`) — model selection, temperature, token limits

---

## What This Ticket Must Accomplish

### Goal

Build the ad copy generator that takes an `ExpandedBrief`, selects structural atoms from the pattern database, and produces complete Meta ad copy (primary text, headline, description, CTA button) using reference-decompose-recombine.

### Deliverables Checklist

#### A. Ad Generator Module (`generate/ad_generator.py`)

- [ ] `generate_ad(expanded_brief: ExpandedBrief, seed: int | None = None) -> GeneratedAd`
  - Takes the expanded brief from P1-01
  - Calls `_select_structural_atoms()` to pick proven patterns matching the brief's campaign goal and audience
  - Builds a recombination prompt that instructs the LLM to combine atoms with brief context
  - Calls Gemini (Flash) via `retry_with_backoff()`
  - Uses `get_ad_seed()` for deterministic generation when seed is provided
  - Returns `GeneratedAd` dataclass
- [ ] `GeneratedAd` dataclass:
  - `ad_id`: unique identifier (derived from seed chain)
  - `primary_text`: main copy above the image — the scroll-stopper
  - `headline`: bold text below image — short, punchy
  - `description`: secondary text below headline
  - `cta_button`: one of the standard Meta CTA options ("Learn More", "Sign Up", "Get Started", etc.)
  - `structural_atoms_used`: list of atom references (traceability)
  - `expanded_brief_id`: reference back to the brief
  - `generation_metadata`: model used, token count, seed, timestamp
- [ ] `_select_structural_atoms(campaign_goal: str, audience: str) -> list[dict]`
  - Queries `competitive/patterns.json` via `query_patterns()` for patterns matching goal and audience
  - Selects 2-3 diverse structural atoms (hook type, body pattern, CTA style)
  - Prefers atoms from high-scoring reference ads and successful competitor patterns
  - Returns structured atom list for prompt injection
- [ ] `_build_generation_prompt(expanded_brief: ExpandedBrief, atoms: list[dict]) -> str`
  - Constructs the recombination prompt
  - Includes: expanded brief context, selected structural atoms as "proven patterns to draw from," brand voice guidelines, Meta ad format constraints (character limits, mobile truncation awareness)
  - Instructs: "Recombine these proven structural elements with the brief context. Do NOT copy verbatim — adapt and recombine."
- [ ] `_parse_generation_response(response: str, ad_id: str) -> GeneratedAd`
  - Parses structured JSON response into `GeneratedAd`
  - Validates all 4 required components are present and non-empty
  - Validates character limits (primary_text reasonable for Meta, headline concise)
  - Falls back with partial output + warning if response is malformed

#### B. Tests (`tests/test_generation/test_ad_generator.py`)

- [ ] TDD first
- [ ] Test generated ad contains all 4 components (primary_text, headline, description, cta_button)
- [ ] Test all components are non-empty strings
- [ ] Test structural atoms are selected and recorded in output
- [ ] Test seed determinism: same seed + same brief = same ad_id
- [ ] Test different campaign goals select different structural atoms
- [ ] Test malformed API response handled gracefully
- [ ] Test CTA button is a valid Meta CTA option
- [ ] Test generation metadata is populated (model, tokens, timestamp)
- [ ] Minimum: 8+ tests

#### C. Integration

- [ ] Wire P1-01 output (`ExpandedBrief`) as input to `generate_ad()`
- [ ] Log `AdGenerated` events to decision ledger via `log_event()` with ad_id, seed, structural atoms used
- [ ] Ensure output `GeneratedAd` is compatible with P1-04 evaluator input format

#### D. Documentation

- [ ] Add P1-02 entry in `docs/DEVLOG.md`

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
| Reference-decompose-recombine | R2-Q1 | Decompose high-performing ads into structural atoms (hook type, body pattern, CTA style). Recombine proven elements. Creates a repeatable, improvable system. |
| Competitive structural atoms | Section 4.8.6 | Generation draws from competitive structural atoms in the pattern database. |
| Per-ad seed chains | R3-Q4 | `seed = hash(global_seed + brief_id + cycle_number)`. Deterministic generation for reproducibility. |
| Shared structural patterns | R3-Q8 | Structural learning (hook types, CTA styles) shared across campaigns. Content isolated per campaign. |

### Files to Create

| File | Why |
|------|-----|
| `generate/ad_generator.py` | Core ad copy generator with reference-decompose-recombine |
| `tests/test_generation/test_ad_generator.py` | Generator tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `generate/brief_expansion.py` | `ExpandedBrief` dataclass — your input format |
| `generate/competitive.py` | `query_patterns()` — how to query structural atoms |
| `generate/seeds.py` | `get_ad_seed()` — seed-based determinism |
| `data/competitive/patterns.json` | Raw pattern records with structural atoms |
| `data/reference_ads.json` | Reference ads — source of proven structural patterns |
| `iterate/retry.py` | `retry_with_backoff()` for resilient Gemini calls |
| `iterate/ledger.py` | `log_event()` for logging generation events |
| `data/config.yaml` | Model selection, temperature, token limits |
| `docs/reference/prd.md` (R2-Q1, Section 4.8.6) | Full rationale for decompose-recombine and competitive integration |

---

## Definition of Done

- [ ] `generate_ad()` produces a complete `GeneratedAd` with all 4 Meta ad components
- [ ] Structural atoms from pattern database are selected and recorded
- [ ] Seed-based determinism works (same inputs = same ad_id)
- [ ] Generation events logged to decision ledger
- [ ] Malformed API responses handled gracefully
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Committed on `develop`

---

## Estimated Time: 60–90 minutes

---

## After This Ticket: What Comes Next

**P1-03 (Audience-specific brand voice profiles)** adds audience-aware voice profiles that the generator can use for tonal guidance. Once P1-03 is done, the generator prompt can include the selected voice profile.

**P1-04 (Chain-of-thought evaluator)** takes the `GeneratedAd` output and evaluates it across 5 quality dimensions. The generator and evaluator together form the core generate-evaluate loop.

**P1-06 (Tiered model routing)** will later wrap the generator to use Flash for first drafts and Pro for borderline regeneration, but the generator itself should be model-agnostic (accept model as a parameter from config).
