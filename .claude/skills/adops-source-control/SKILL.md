---
name: adops-source-control
description: Source control best practices for Ad-Ops-Autopilot — git branching strategy, commit conventions, phase-based delivery, and pre-commit verification. Use when creating branches, committing code, managing PRs, or transitioning between project phases.
---

# Ad-Ops-Autopilot Source Control

## Branch Strategy

**NEVER commit directly to `main`.** All work happens on `develop`.

```
develop  ←── all ticket work goes here (test locally)
   │
   └──▶ main  ←── merge develop when verified (stable)
```

No feature branches. No PRs. Solo developer workflow.

### Workflow

```bash
# 1. Work on develop
git switch develop

# 2. Implement, test, commit (all on develop)
# ... write tests, write code, verify ...

# 3. When verified, merge to main
git switch main && git merge develop && git push origin main

# 4. Switch back to develop
git switch develop
```

## Commit Conventions

Use Conventional Commits. Reference ticket ID in every message.

### Format

```
<type>: <description> (<ticket-id>)
```

### Types

| Type | When |
|------|------|
| `feat:` | New feature or capability |
| `test:` | Adding or modifying tests |
| `fix:` | Bug fix |
| `docs:` | Documentation, decision log updates |
| `refactor:` | Code restructuring without behavior change |
| `chore:` | Config, dependencies, tooling |

### Examples

```
test: add golden set regression tests for evaluator (P0-07)
feat: implement chain-of-thought 5-step evaluator (P1-04)
feat: add campaign-goal-adaptive weighting with floor constraints (P1-05)
fix: prevent dimension collapse via Pareto selection (P1-07)
docs: document weighting rationale in decision log (P1-05)
chore: add ruff config and pre-commit checks (P0-01)
```

### Commit Cadence

Commit in logical increments, in this order:
1. **Tests first** (TDD — write failing tests)
2. **Implementation** (make tests pass)
3. **Documentation** (decision log, updated README)

Small, focused commits > large monolithic ones.

## Pre-Commit Verification Checklist

Run ALL of these before every commit. Do not commit if any fails.

```bash
# 1. All tests pass
python -m pytest tests/ -v

# 2. Lint is clean
ruff check . --fix

# 3. Check what you're staging
git status
git diff --staged

# 4. Verify no secrets or junk
# Must NOT see: .env, __pycache__/, .venv/, .DS_Store, *.pyc
```

### Additional Checks for Pipeline Tickets

```bash
# 5. Decision ledger is valid JSONL
python -c "import json; [json.loads(l) for l in open('data/ledger.jsonl')]"

# 6. Seed reproducibility (if applicable)
python -c "from generate.seeds import get_ad_seed; assert get_ad_seed('s','b',1) == get_ad_seed('s','b',1)"
```

## Phase Boundary Discipline

This project has 7 phases (P0–P5 + P1B). Phases are sequential.

### Rules

- Do NOT start Phase N+1 work until Phase N is merged to main
- When completing the last ticket in a phase, note it:
  ```
  feat: complete P0 foundation phase — all calibration done (P0-10)
  ```

### Phase Overview

| Phase | Tickets | Focus |
|-------|---------|-------|
| P0 | P0-01 – P0-10 (10) | Foundation, infra, calibration, competitive pattern DB |
| P1 | P1-01 – P1-20 (20) | Full-ad pipeline (copy + image via Nano Banana Pro), 50+ ads |
| P1B | PA-01 – PA-12 (12) | Application layer (sessions, auth, brief config, curation) |
| P2 | P2-01 – P2-07 (7) | Testing & validation |
| P3 | P3-01 – P3-13 (13) | A/B variant engine, Veo UGC video |
| P4 | P4-01 – P4-07 (7) | Autonomous engine (v3) |
| P5 | P5-01 – P5-11 (11) | Dashboard, docs & submission |

## .gitignore Essentials

```gitignore
# Environment
.env
.venv/
__pycache__/
*.pyc

# OS
.DS_Store
Thumbs.db

# IDE
.idea/
.vscode/
*.swp

# Data (keep schema, ignore runtime)
data/ledger.jsonl
data/cache/

# API responses (may contain keys in errors)
*.log
```

## What NOT to Do

- Do NOT commit to `main` directly — merge via `develop`
- Do NOT create feature branches — work directly on `develop`
- Do NOT rebase or force-push without explicit approval
- Do NOT commit `.env` or API keys
