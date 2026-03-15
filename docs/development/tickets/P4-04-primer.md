# P4-04 Primer: Cross-Campaign Transfer

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P0–P3 complete. Pattern DB and competitive query interface exist. See `docs/development/DEVLOG.md`.

---

## What Is This Ticket?

P4-04 implements **cross-campaign learning** — structural patterns (hook types, CTA styles, body structure) transfer across campaigns, while content (specific claims, proof points, pricing) stays campaign-specific. A `campaign_scope` tag separates craft from substance.

### Why It Matters

- **Pillar 6: Learning Is Structural** — The system learns "question hooks work 2x for parents" (transferable), not "mention SAT prep" (campaign-specific)
- **R3-Q8:** Shared Structural Patterns, Isolated Content — craft transfers, substance doesn't
- Enables the system to get smarter with each campaign without leaking content across brands

---

## What Was Already Done

- `data/competitive/patterns.json` — 40 pattern records with `hook_type`, `emotional_angle`, `cta_style`, `target_audience`
- `generate/competitive.py` — `query_patterns()` filters by audience, goal, hook_type; `get_landscape_context()` formats for prompts
- `generate/ab_variants.py` — `track_variant_win()` records wins per audience/element to ledger; `get_segment_patterns()` extracts win rates
- `generate/ab_image_variants.py` — `track_image_variant_win()` and `get_visual_patterns()` for image variant tracking
- `iterate/ledger.py` — All generation/evaluation events logged with scores, enabling win rate calculation
- `generate/style_library.py` — Style presets with audience mapping (structural, transferable)

---

## What This Ticket Must Accomplish

### Goal

Add `campaign_scope` tagging to pattern records and variant wins, enabling structural patterns to transfer across campaigns while keeping content isolated.

### Deliverables Checklist

#### A. Campaign Scope Tagging

Create `iterate/campaign_transfer.py`:

- [ ] `CampaignScope` constants — `UNIVERSAL = "universal"`, function to create campaign-specific scope: `campaign_scope(name) -> str` returning `"campaign:{name}"`
- [ ] `PatternRecord` dataclass — `pattern_type: str`, `pattern_value: str`, `campaign_scope: str`, `win_rate: float`, `sample_size: int`, `audience: str`, `source: str`
- [ ] `classify_scope(pattern: dict) -> str` — Determine if a pattern is universal (structural) or campaign-specific (content)
  - Universal: hook_type, cta_style, body_structure, emotional_angle, composition, color_palette
  - Campaign-specific: claims, proof_points, pricing, testimonials, brand-specific language

#### B. Pattern Library

- [ ] `PatternLibrary` class:
  - `add_pattern(record: PatternRecord)` — Add or update pattern with scope tag
  - `get_universal_patterns(audience: str | None, top_n: int) -> list[PatternRecord]` — Return only universal patterns, ranked by win rate
  - `get_campaign_patterns(campaign: str, audience: str | None) -> list[PatternRecord]` — Return campaign-specific patterns
  - `get_transferable_insights(source_campaign: str, target_audience: str) -> list[PatternRecord]` — Universal patterns from source applicable to target
  - `save(path: str)` / `load(path: str)` — JSON persistence
- [ ] Backed by `data/pattern_library.json`

#### C. Win Rate Aggregation

- [ ] `aggregate_wins_from_ledger(ledger_path: str) -> list[PatternRecord]` — Extract structural pattern win rates from variant tracking events
- [ ] Group by: `pattern_type` + `pattern_value` + `audience`
- [ ] Tag each with `campaign_scope` based on `classify_scope()`

#### D. Transfer Query Interface

- [ ] `get_transfer_recommendations(target_audience: str, target_goal: str) -> list[PatternRecord]` — High-win-rate universal patterns relevant to the target
- [ ] Sort by win_rate descending, filter by minimum `sample_size >= 3`
- [ ] Format as injectable context for brief expansion

### What Transfers vs. What Doesn't

| Transfers (Universal) | Stays Isolated (Campaign-Specific) |
|----------------------|-----------------------------------|
| "Question hooks work 2x for parents" | "SAT scores improve 200+ points" |
| "Urgency CTAs outperform soft CTAs" | "Spring enrollment deadline March 15" |
| "Warm color palettes for student ads" | Varsity Tutors logo placement |
| "Social proof body structure" | Specific testimonial quotes |

### Files to Create/Modify

| File | Action |
|------|--------|
| `iterate/campaign_transfer.py` | **Create** — Scope tagging, pattern library, transfer queries |
| `data/pattern_library.json` | **Create** — Persistent pattern storage (initially empty `[]`) |
| `tests/test_pipeline/test_campaign_transfer.py` | **Create** — Tests |

### Files to READ for Context

| File | Why |
|------|-----|
| `generate/competitive.py` | Existing pattern query interface |
| `generate/ab_variants.py` | Copy variant win tracking (`track_variant_win`, `get_segment_patterns`) |
| `generate/ab_image_variants.py` | Image variant win tracking |
| `iterate/ledger.py` | Source of win/loss data |
| `data/competitive/patterns.json` | Existing pattern schema for reference |

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Shared structure, isolated content | R3-Q8 | Hook types transfer; claims don't |
| campaign_scope tag | R3-Q8 | "universal" or "campaign:{name}" |
| Structural learning | Pillar 6 | System learns craft, not substance |

---

## Definition of Done

- [ ] campaign_scope classification correctly separates structural from content patterns
- [ ] PatternLibrary stores and retrieves patterns by scope
- [ ] Universal patterns queryable across campaigns
- [ ] Campaign-specific patterns isolated to their campaign
- [ ] Transfer recommendations rank by win rate with min sample size
- [ ] Tests verify: scope classification, library CRUD, transfer isolation

---

## Estimated Time: 40–50 minutes
