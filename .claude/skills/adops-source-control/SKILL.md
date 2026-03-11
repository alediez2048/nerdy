---
name: adops-source-control
description: Source control best practices for Ad-Ops-Autopilot — git branching strategy, commit conventions, phase-based delivery, and pre-commit verification. Use when creating branches, committing code, managing PRs, or transitioning between project phases.
---

# Ad-Ops-Autopilot Source Control

## Branch Strategy

**NEVER commit directly to `main`.** Every ticket uses a dedicated feature branch.

### Branch Naming

```
feature/<ticket-id>-<short-description>
```

Examples:
- `feature/P0-01-project-scaffolding`
- `feature/P0-06-evaluator-calibration`
- `feature/P1-04-cot-evaluator`
- `feature/P1-07-pareto-regeneration`
- `feature/P2-01-inversion-tests`
- `feature/P4-03-competitive-intelligence`

### Branch Lifecycle

```bash
# 1. Start from up-to-date main
git switch main && git pull

# 2. Create feature branch
git switch -c feature/P1-04-cot-evaluator

# 3. Do ALL work on this branch
# ... implement, test, commit ...

# 4. Push when done
git push -u origin feature/P1-04-cot-evaluator

# 5. Open PR against main (or notify for review)
# 6. Do NOT merge yourself — wait for review
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

This project has 6 phases (P0–P5). Phases are sequential.

### Rules

- Do NOT create branches for tickets in future phases
- Do NOT start Phase N+1 work until Phase N is merged to main
- When completing the last ticket in a phase, note it:
  ```
  feat: complete P0 foundation phase — all calibration done (P0-08)
  ```

### Phase Overview

| Phase | Tickets | Focus |
|-------|---------|-------|
| P0 | P0-01 – P0-08 | Foundation, infra, calibration |
| P1 | P1-01 – P1-14 | Core text pipeline, 50+ ads |
| P2 | P2-01 – P2-07 | Testing & validation |
| P3 | P3-01 – P3-06 | Multi-modal (v2) |
| P4 | P4-01 – P4-07 | Autonomous engine (v3) |
| P5 | P5-01 – P5-06 | Documentation & submission |

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

- Do NOT commit to `main` directly
- Do NOT skip creating a branch "to save time"
- Do NOT rebase or force-push without explicit approval
- Do NOT commit `.env` or API keys
- Do NOT delete branches after merging (let the reviewer handle cleanup)
- Do NOT squash commits without approval — the commit history tells the implementation story
- Do NOT create branches for tickets in future phases
