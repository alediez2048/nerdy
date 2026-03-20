# PF-08 Primer: Production Readiness — Environment & Config

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PF-01 through PF-07. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PF-08 verifies the app can be deployed and run in a production-like environment. This covers Docker Compose, environment validation, database setup, secrets management, and deployment documentation.

### Why It Matters

- Development-only configs break in production (hardcoded localhost, missing env vars)
- Docker Compose must start all services cleanly: API, worker, Redis, PostgreSQL, frontend
- Missing env var validation causes cryptic runtime errors
- PA-12 (Docker Compose production) was marked ⏳ — this ticket closes the gap

---

## What This Ticket Must Accomplish

### Goal

`docker compose up` starts the full app with zero manual steps beyond setting `.env`.

### Deliverables Checklist

#### A. Docker Compose Verification

- [ ] `docker-compose.yml` starts all services: api, worker, redis, postgres, frontend
- [ ] All services reach healthy state (health checks if configured)
- [ ] Frontend accessible at configured port
- [ ] API accessible at `/api/` prefix
- [ ] Worker connects to Redis and starts processing tasks
- [ ] PostgreSQL initializes with correct schema (init_db or Alembic)

#### B. Environment Variable Validation

- [ ] Add startup validation in FastAPI app: check all required env vars present
- [ ] Required: `GEMINI_API_KEY`, `DATABASE_URL`, `REDIS_URL`
- [ ] Optional with defaults: `FAL_KEY` (only for video), `SECRET_KEY`
- [ ] Log clear error message if required var is missing (not a cryptic traceback)
- [ ] `.env.example` contains all vars with placeholder values

#### C. Secrets Management

- [ ] No hardcoded API keys in source code (grep for key patterns)
- [ ] No `.env` file committed to repo (in `.gitignore`)
- [ ] No API keys in `docker-compose.yml` (only `env_file: .env` references)
- [ ] No keys in test files (use mocks or env-based skip)

#### D. Database Setup

- [ ] `init_db()` creates all tables on first run
- [ ] Tables: sessions, users, curated_sets, share_tokens + campaigns (when PC-04 done)
- [ ] Migrations strategy documented (Alembic or auto-create)
- [ ] Database URL configurable via env var

#### E. Dockerfile Verification

- [ ] `Dockerfile.api` builds successfully
- [ ] Build uses caching effectively (requirements installed before code copy)
- [ ] No unnecessary files in image (check `.dockerignore`)
- [ ] Frontend build included or served separately

#### F. Documentation

- [ ] Deployment guide in README or separate doc
- [ ] Step-by-step: clone → create .env → docker compose up → verify
- [ ] Troubleshooting section for common issues

---

## Branch & Merge Workflow

Work on `video-implementation-2.0` branch (current branch).

---

## Important Context

### Files to Modify

| File | Action |
|------|--------|
| `docker-compose.yml` | Verify all services, health checks |
| `Dockerfile.api` | Verify build, caching |
| `.dockerignore` | Verify completeness |
| `.env.example` | Update with all required vars |
| `app/config.py` | Add env var validation |
| `README.md` | Add deployment section |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `docker-compose.yml` | Current service definitions |
| `Dockerfile.api` | Current build config |
| `.env.example` | Current env var list |
| `app/config.py` | Current settings |
| `app/db.py` | Database setup |

### Files You Should NOT Modify

- Pipeline code
- Frontend source code (unless build config)
- Test files

---

## Definition of Done

- [ ] `docker compose up` starts all services
- [ ] Missing env vars produce clear error messages
- [ ] No hardcoded secrets in source
- [ ] Database initializes on first run
- [ ] Deployment docs complete
- [ ] DEVLOG updated

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Docker Compose verification | 15 min |
| Env var validation | 10 min |
| Secrets audit | 10 min |
| Database setup verification | 10 min |
| Documentation | 10 min |
| DEVLOG | 5 min |

---

## After This Ticket: What Comes Next

- **PF-09:** Performance & monitoring
- **PF-10:** Final verification
