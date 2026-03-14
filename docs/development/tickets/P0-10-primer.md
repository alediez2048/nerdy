# P0-10 Primer: Competitive Pattern Query Interface

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot -- Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P0-09 (competitive pattern database -- initial scan) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P0-10 builds the **query interface** for the competitive pattern database created in P0-09. This is a utility module (`generate/competitive.py`) that loads `data/competitive/patterns.json` and provides a `query_patterns()` function to retrieve relevant competitive patterns by audience, campaign goal, hook type, competitor, or tags. Returns top-N ranked results for pipeline consumption.

### Why It Matters

- **Pipeline integration**: Brief expansion (P1-01) needs competitive context to generate differentiated ads
- **Every Token Is an Investment** (Pillar 3): Relevant competitive patterns reduce generation attempts by giving the generator awareness of the landscape
- **Competitive intelligence** (+10 bonus points): The query interface is what makes the pattern database usable -- without it, the data is inert
- **Decomposition Is the Architecture** (Pillar 1): Queryable structured patterns let the pipeline pull exactly the competitive context it needs

---

## What Was Already Done

- P0-09: Competitive pattern database with 48--60 structured pattern records across 6 competitors
- P0-05: Reference ads and structural atom decomposition
- P0-04: Brand knowledge base

---

## What This Ticket Must Accomplish

### Goal

Build a utility function that queries the competitive pattern database by audience, campaign goal, hook type, competitor, and tags. Returns top-N relevant patterns ranked by relevance.

### Deliverables Checklist

#### A. Implementation (`generate/competitive.py`)

- [ ] `load_patterns(path: str = "data/competitive/patterns.json") -> list[dict]`
  - Loads and caches the pattern database
  - Validates JSON structure on load
  - Returns list of pattern records
- [ ] `query_patterns(audience: str | None = None, campaign_goal: str | None = None, hook_type: str | None = None, competitor: str | None = None, tags: list[str] | None = None, top_n: int = 5) -> list[dict]`
  - Filters pattern records by any combination of parameters
  - All filters are optional; no filters returns all records
  - Tags use inclusive matching (any tag matches)
  - Results ranked by relevance (number of matching criteria)
  - Returns top-N results (default 5)
- [ ] `get_competitor_summary(competitor: str) -> dict | None`
  - Returns the strategy summary for a given competitor
  - Loads from `data/competitive/summaries.json`
- [ ] `get_all_competitors() -> list[str]`
  - Returns list of all competitors in the database
- [ ] `get_landscape_context(audience: str, campaign_goal: str, top_n: int = 3) -> str`
  - Returns a formatted string of competitive context suitable for injection into brief expansion prompts
  - Combines top patterns + competitor summaries into a concise landscape overview

#### B. Tests (`tests/test_generation/test_competitive.py`)

- [ ] TDD first
- [ ] Test `load_patterns` loads and returns valid records
- [ ] Test `load_patterns` with missing file raises appropriate error
- [ ] Test `query_patterns(audience="parents")` returns only parent-targeted patterns
- [ ] Test `query_patterns(audience="parents", tags=["conversion"])` returns ranked results
- [ ] Test `query_patterns(competitor="Kaplan")` returns only Kaplan patterns
- [ ] Test `query_patterns(hook_type="question")` filters correctly
- [ ] Test `query_patterns()` with no filters returns all records
- [ ] Test `query_patterns(top_n=3)` returns at most 3 results
- [ ] Test `get_competitor_summary` returns correct summary
- [ ] Test `get_competitor_summary` with unknown competitor returns None
- [ ] Test `get_landscape_context` returns non-empty formatted string
- [ ] Minimum: 10+ tests

#### C. Integration

- [ ] Module importable from pipeline: `from generate.competitive import query_patterns`
- [ ] Works with the actual `data/competitive/patterns.json` from P0-09
- [ ] Results format compatible with brief expansion prompt injection (P1-01)

#### D. Documentation

- [ ] Add P0-10 entry in `docs/DEVLOG.md`
- [ ] Docstrings on all public functions

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/P0-10-competitive-query-interface
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Competitive intelligence | R2-Q2 | Structured pattern extraction -- queryable patterns, not raw ads |
| Brief expansion grounding | R3-Q5 | Competitive context injected into brief expansion for differentiation |
| Cross-campaign transfer | R3-Q8 | Shared structural patterns with isolated content via campaign_scope tags |

### Files to Create

| File | Why |
|------|-----|
| `generate/competitive.py` | Pattern query interface module |
| `tests/test_generation/test_competitive.py` | Query interface tests |

### Files to Modify

| File | Why |
|------|-----|
| `docs/DEVLOG.md` | Add P0-10 entry |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `data/competitive/patterns.json` (P0-09) | The database this module queries |
| `data/competitive/summaries.json` (P0-09) | Competitor strategy summaries |
| `data/competitive/schema.json` (P0-09) | Schema for pattern records |
| `prd.md` (Section 4.8) | Full competitive intelligence architecture spec |
| `interviews.md` (R2-Q2) | Structured pattern extraction rationale |
| `interviews.md` (R3-Q8) | Cross-campaign shared patterns design |

---

## Definition of Done

- [ ] `query_patterns()` returns correct filtered results for all parameter combinations
- [ ] `query_patterns(audience="parents", tags=["conversion"])` returns ranked results
- [ ] `get_landscape_context()` produces formatted competitive context string
- [ ] All 10+ tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 45--60 minutes

---

## After This Ticket: What Comes Next

**P0 is now complete.** The foundation is ready:
- Decision ledger (P0-02)
- Deterministic seeds (P0-03)
- Brand knowledge base (P0-04)
- Reference ads + patterns (P0-05)
- Calibrated evaluator (P0-06)
- Golden set regression tests (P0-07)
- Checkpoint-resume (P0-08)
- Competitive pattern database (P0-09)
- Competitive pattern query interface (P0-10)

**Phase 1 begins:** P1-01 (Brief expansion engine) is the first ticket -- it uses `get_landscape_context()` from this module to inject competitive differentiation guidance into expanded briefs.
