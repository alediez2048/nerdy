# TICKET-ID Primer: [Title]

**For:** New Cursor Agent session  
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG  
**Date:** [Date]  
**Previous work:** [Prerequisites]. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

[1–2 paragraphs: what this ticket implements and why it matters in the pipeline.]

### Why It Matters

- [Bullet 1]
- [Bullet 2]
- [Bullet 3]

---

## What Was Already Done

- [List of completed prerequisite tickets and what they provide]
- [Existing files, contracts, or configs this ticket depends on]

---

## What This Ticket Must Accomplish

### Goal

[Single sentence: the concrete outcome.]

### Deliverables Checklist

#### A. Implementation (`path/to/module.py`)

- [ ] [Specific deliverable 1]
- [ ] [Specific deliverable 2]
- [ ] [...]

#### B. Tests (`tests/test_module.py`)

- [ ] TDD first: write tests before implementation
- [ ] [Specific test 1]
- [ ] [Specific test 2]
- [ ] [...]

#### C. Integration Expectations

- [ ] [What this module must be compatible with]
- [ ] [Contracts it must preserve]

#### D. Documentation

- [ ] Add ticket entry in `docs/DEVLOG.md`
- [ ] Update decision log if architectural choices were made
- [ ] [Other doc requirements]

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/TICKET-ID-short-description
# ... implement ...
git push -u origin feature/TICKET-ID-short-description
```

Conventional Commits: `test:`, `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `path/to/new_file.py` | [Purpose] |

### Files to Modify

| File | Action |
|------|--------|
| `path/to/file.py` | [What to change] |
| `docs/DEVLOG.md` | Add ticket entry |

### Files You Should NOT Modify

- [List of files outside scope]

### Files You Should READ for Context

| File | Why |
|------|-----|
| `prd.md` | Ticket acceptance criteria |
| `interviews.md` | Architectural decisions [R#-Q#] |
| `docs/DEVLOG.md` | Prior ticket status |

### Cursor Rules to Follow

- `.cursor/rules/[relevant-rule].mdc`

---

## Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| [Topic] | R#-Q# | [One-line summary of the chosen approach] |

---

## Suggested Implementation Pattern

[Code examples, function signatures, data flow diagrams]

---

## Edge Cases to Handle

1. [Edge case 1]
2. [Edge case 2]

---

## Definition of Done

- [ ] [Acceptance criterion 1 from prd.md]
- [ ] [Acceptance criterion 2]
- [ ] Tests pass (`python -m pytest tests/ -v`)
- [ ] Lint clean (`ruff check . --fix`)
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time

| Task | Estimate |
|------|----------|
| [Phase 1] | X min |
| [Phase 2] | X min |
| DEVLOG update | 5–10 min |

---

## After This Ticket: What Comes Next

- [What tickets this unblocks]
- [Dependencies it satisfies]
