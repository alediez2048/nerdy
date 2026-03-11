# P0-02 Primer: Append-Only Decision Ledger

**For:** New Cursor Agent session  
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG  
**Date:** March 2026  
**Previous work:** P0-01 (project scaffolding) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P0-02 implements the **append-only JSONL decision ledger** — the system's single source of truth for every event that happens in the pipeline. Every generation, evaluation, regeneration, and decision is recorded here. It's the foundation for checkpoint-resume (P0-08), token attribution (P1-11), narrated replay (P4-07), and quality trend visualization (P5-03).

### Why It Matters

- **State is Sacred** (Pillar 5): No work is ever lost. Every decision is recoverable.
- **Reproducibility:** Every run can be replayed from the ledger
- **Token tracking:** Cost-per-publishable-ad requires knowing where every token went
- **14 cross-references** in the PRD depend on this component — it's the most referenced module in the architecture

---

## What Was Already Done

- P0-01: Project scaffolding complete — `data/` directory exists, `data/config.yaml` exists
- Ledger schema defined in `.cursor/rules/pipeline-patterns.mdc` and `.cursor/rules/code-patterns.mdc`
- Event types defined in `.claude/skills/adops-constraints/SKILL.md`

---

## What This Ticket Must Accomplish

### Goal

Implement a zero-dependency JSONL event logger that any module can call to record pipeline events, with standardized schema and append-only guarantees.

### Deliverables Checklist

#### A. Ledger Module (`data/ledger.py` or a utility in an appropriate location)

- [ ] `log_event(ledger_path: str, event: dict) -> None` — append a single event
- [ ] `read_events(ledger_path: str) -> list[dict]` — read all events
- [ ] `read_events_filtered(ledger_path: str, **filters) -> list[dict]` — filter by ad_id, brief_id, event_type, etc.
- [ ] `get_ad_lifecycle(ledger_path: str, ad_id: str) -> list[dict]` — all events for a single ad
- [ ] Auto-inject `timestamp` (ISO-8601) and `checkpoint_id` (UUID) on every write
- [ ] Validate event schema before writing (required fields check)
- [ ] Append-only: never modify or delete existing entries
- [ ] Handle concurrent writes safely (file locking or atomic appends)
- [ ] Handle missing/new ledger file gracefully (create on first write)

#### B. Event Schema Validation

Required fields for every event:
```python
REQUIRED_FIELDS = [
    "event_type",    # AdGenerated|AdEvaluated|AdRegenerated|AdPublished|AdDiscarded|BatchCompleted|ThresholdAdjusted
    "ad_id",         # Can be None for batch-level events
    "brief_id",      # Can be None for system events
    "cycle_number",  # 0 for first generation
    "action",        # generation|evaluation|regeneration-attempt-N|brief-expansion|triage|context-distillation
    "tokens_consumed", # 0 if no API call
    "model_used",    # gemini-flash|gemini-pro|none
    "seed",          # Per-ad seed or empty string
]
```

#### C. Tests (`tests/test_pipeline/test_ledger.py`)

- [ ] TDD first: write tests before implementation
- [ ] Test write + read roundtrip (write event, read back, compare)
- [ ] Test append-only behavior (multiple writes, all preserved)
- [ ] Test auto-injected fields (timestamp format, checkpoint_id uniqueness)
- [ ] Test schema validation (missing required field raises error)
- [ ] Test filtering by event_type, ad_id, brief_id
- [ ] Test `get_ad_lifecycle` returns events in chronological order
- [ ] Test missing file creation on first write
- [ ] Test JSONL validity (each line is valid JSON)
- [ ] Minimum: 8+ tests

#### D. Documentation

- [ ] Add P0-02 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/P0-02-decision-ledger
```

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| Ledger module (location TBD — could be `iterate/ledger.py` or a shared utility) | Core event logging |
| `tests/test_pipeline/test_ledger.py` | Ledger unit tests |

### Files to Modify

| File | Action |
|------|--------|
| `docs/DEVLOG.md` | Add P0-02 entry |

### Files You Should NOT Modify

- `generate/*`, `evaluate/*` — not yet implemented
- `data/config.yaml` — unless adding ledger-specific config
- Anything in P0-03+ scope

### Files You Should READ for Context

| File | Why |
|------|-----|
| `prd.md` (line ~414, P0-02) | Acceptance criteria |
| `.cursor/rules/pipeline-patterns.mdc` | Ledger schema definition |
| `.cursor/rules/code-patterns.mdc` | `log_event` pattern and schema |
| `.claude/skills/adops-constraints/SKILL.md` | Event type list |

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Data storage | R2-Q8 | Append-only JSONL — zero-dependency, reproducible, queryable with pandas |
| Checkpoint-resume | R3-Q2 | Every successful API call writes checkpoint_id for resume |

---

## Suggested Implementation Pattern

```python
import json
from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path

REQUIRED_FIELDS = ["event_type", "ad_id", "brief_id", "cycle_number", "action", "tokens_consumed", "model_used", "seed"]

def log_event(ledger_path: str, event: dict) -> None:
    _validate_event(event)
    event["timestamp"] = datetime.now(timezone.utc).isoformat()
    event["checkpoint_id"] = str(uuid4())
    path = Path(ledger_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(event, default=str) + "\n")

def read_events(ledger_path: str) -> list[dict]:
    path = Path(ledger_path)
    if not path.exists():
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]
```

---

## Definition of Done

- [ ] Ledger module implemented with `log_event`, `read_events`, `read_events_filtered`, `get_ad_lifecycle`
- [ ] Events written to JSONL with auto-injected timestamp and checkpoint_id
- [ ] Schema validation catches missing required fields
- [ ] Pandas can filter by ad_id and reconstruct ad lifecycle
- [ ] Tests pass (`python -m pytest tests/ -v`)
- [ ] Lint clean (`ruff check . --fix`)
- [ ] DEVLOG updated with P0-02 entry
- [ ] Feature branch pushed

---

## Estimated Time: 30–45 minutes

| Task | Estimate |
|------|----------|
| Write failing tests | 10–15 min |
| Implement ledger module | 10–15 min |
| Test fixes and edge cases | 5–10 min |
| DEVLOG update | 5 min |

---

## After This Ticket: What Comes Next

- **P0-03** (Per-ad seed chain) — will use ledger to log seeds
- **P0-08** (Checkpoint-resume) — depends directly on checkpoint_id in ledger
- **P1-11** (Token attribution) — queries ledger for cost analysis
- Every pipeline ticket writes to this ledger
