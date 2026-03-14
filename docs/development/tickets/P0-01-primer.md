# P0-01 Primer: Project Scaffolding

**For:** New Cursor Agent session  
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG  
**Date:** March 2026  
**Previous work:** None — this is the first ticket.

---

## What Is This Ticket?

P0-01 creates the project skeleton: directory structure, dependency management, configuration files, and a working README. After this ticket, any developer should be able to clone the repo and run `pip install -r requirements.txt` without errors.

### Why It Matters

- **One-command setup** is an explicit rubric requirement — `requirements.txt` with pinned versions
- Every subsequent ticket depends on the directory structure existing
- `config.yaml` with tunable parameters prevents hardcoded magic numbers throughout the codebase
- `.env.example` documents required API keys without exposing secrets

---

## What Was Already Done

- `prd.md` — Full PRD with 81 tickets across 7 phases
- `interviews.md` — 50 architectural pressure-test Q&As (R1–R5)
- `requirements.md` — Assignment specification
- `.cursor/rules/` — 12 cursor rules governing implementation
- `.claude/skills/` — 6 Claude skills with reference materials
- `docs/DEVLOG.md` — Development log (empty, ready for entries)

---

## What This Ticket Must Accomplish

### Goal

Create the complete project skeleton with all directories, dependency files, configuration, and README so that the project is runnable from scratch.

### Deliverables Checklist

#### A. Directory Structure

- [ ] Create `generate/` with `__init__.py`
- [ ] Create `evaluate/` with `__init__.py`
- [ ] Create `iterate/` with `__init__.py`
- [ ] Create `output/` with `__init__.py`
- [ ] Create `data/` (no `__init__.py` — not a code module)
- [ ] Create `tests/test_evaluation/` with `__init__.py`
- [ ] Create `tests/test_generation/` with `__init__.py`
- [ ] Create `tests/test_pipeline/` with `__init__.py`
- [ ] Create `tests/test_data/` (no `__init__.py` — data directory)
- [ ] Create `tests/conftest.py` (empty fixture file)
- [ ] Create `docs/` (already exists from DEVLOG)

#### B. Dependency Management (`requirements.txt`)

- [ ] `google-genai` — Gemini API SDK
- [ ] `pandas` — Ledger queries and data analysis
- [ ] `matplotlib` — Quality trend visualization
- [ ] `tiktoken` — Token counting
- [ ] `python-dotenv` — Environment variable management
- [ ] `pyyaml` — Config file parsing
- [ ] `pytest` — Testing framework
- [ ] `ruff` — Linting
- [ ] Pin all versions

#### C. Configuration

- [ ] Create `data/config.yaml` with all tunable parameters from `code-patterns.mdc`:
  - `quality_threshold`, `batch_size`, `max_regeneration_cycles`, `pareto_variants`
  - `ratchet_window`, `ratchet_buffer`, `clarity_floor`, `brand_voice_floor`
  - `improvable_range`, `exploration_plateau_threshold`, `exploration_plateau_batches`
- [ ] Create `.env.example` documenting required environment variables:
  - `GEMINI_API_KEY`
  - `GLOBAL_SEED`
- [ ] Create `.gitignore` covering `.env`, `__pycache__/`, `.venv/`, `.DS_Store`, `data/ledger.jsonl`, `data/cache/`, `*.log`

#### D. README

- [ ] Project name and one-line description
- [ ] Setup instructions (clone, venv, pip install, env vars)
- [ ] Usage (how to run the pipeline — placeholder for now)
- [ ] Project structure overview
- [ ] Link to `docs/DEVLOG.md` for development history

#### E. Documentation

- [ ] Add P0-01 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/P0-01-project-scaffolding
# ... implement ...
git push -u origin feature/P0-01-project-scaffolding
```

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `generate/__init__.py` | Package init for ad generation module |
| `evaluate/__init__.py` | Package init for evaluation module |
| `iterate/__init__.py` | Package init for feedback loop module |
| `output/__init__.py` | Package init for output/export module |
| `tests/conftest.py` | Shared pytest fixtures |
| `requirements.txt` | Dependency management |
| `data/config.yaml` | Tunable parameters |
| `.env.example` | Required env vars documentation |
| `.gitignore` | File exclusion rules |
| `README.md` | Project overview and setup |

### Files to Modify

| File | Action |
|------|--------|
| `docs/DEVLOG.md` | Add P0-01 completion entry |

### Files You Should NOT Modify

- `prd.md`, `interviews.md`, `requirements.md` — reference docs, read-only
- `.cursor/rules/*` — already configured
- `.claude/skills/*` — already configured

### Cursor Rules to Follow

- `.cursor/rules/tech-stack.mdc` — dependency versions and constraints
- `.cursor/rules/code-patterns.mdc` — config pattern and directory structure
- `.cursor/rules/git-workflow.mdc` — branch naming and commit conventions
- `.cursor/rules/devlog.mdc` — DEVLOG update requirements

---

## Definition of Done

- [ ] All directories created with appropriate `__init__.py` files
- [ ] `requirements.txt` with pinned versions installs cleanly
- [ ] `data/config.yaml` contains all tunable parameters
- [ ] `.env.example` documents required API keys
- [ ] `.gitignore` covers secrets, caches, and OS files
- [ ] `README.md` has setup instructions that work
- [ ] One-command setup runs without errors
- [ ] DEVLOG updated with P0-01 entry
- [ ] Feature branch pushed

---

## Estimated Time: 20–30 minutes

| Task | Estimate |
|------|----------|
| Create directory structure | 5 min |
| Write requirements.txt | 5 min |
| Create config.yaml + .env.example + .gitignore | 5 min |
| Write README.md | 5–10 min |
| DEVLOG update | 5 min |

---

## After This Ticket: What Comes Next

- **P0-02** (Append-only decision ledger) — needs `data/` directory and config
- **P0-03** (Per-ad seed chain) — needs project structure
- All subsequent tickets depend on this scaffolding
