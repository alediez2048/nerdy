# PA-01 Primer: FastAPI Backend Scaffold

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P1-02 (ad copy generator) should be functional. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PA-01 sets up the **FastAPI backend scaffold** with all infrastructure services needed for the application layer. This is the foundation for the entire web application: API server, database, task queue, and container orchestration.

### Why It Matters

- **The Tool Is the Product** (Pillar 9): The pipeline must become an internal product, not just a CLI tool
- FastAPI + React matches the existing Nerdy tech stack (R5-Q7)
- Single-VM Docker Compose keeps deployment simple and reproducible (R5-Q10)
- Celery + Redis enables long-running pipeline jobs without blocking the API
- Every subsequent PA ticket depends on this scaffold being solid

---

## What Was Already Done

- P0-01: Project scaffolding with directory structure
- P1-02: Ad copy generator (pipeline is functional)
- PRD defines directory structure: `app/api/`, `app/models/`, `app/workers/`, `app/frontend/`

---

## What This Ticket Must Accomplish

### Goal

Stand up a FastAPI project with CORS, PostgreSQL via SQLAlchemy, Celery + Redis for background jobs, and Docker Compose for local development. One command starts everything.

### Deliverables Checklist

#### A. FastAPI Application (`app/api/main.py`)

- [ ] FastAPI app with CORS middleware (allow `localhost:5173` for Vite dev server)
- [ ] Health check endpoint: `GET /health` returns `{"status": "ok"}`
- [ ] OpenAPI docs available at `/docs`
- [ ] Environment-based configuration (`.env` file with `DATABASE_URL`, `REDIS_URL`, `GOOGLE_CLIENT_ID`, `SECRET_KEY`)
- [ ] Proper app factory pattern or module-level app instance

#### B. Database Setup (`app/models/`)

- [ ] SQLAlchemy async engine + session factory
- [ ] Alembic for migrations (initialized, first migration = empty baseline)
- [ ] `app/models/base.py` with declarative base
- [ ] Database URL from environment variable

#### C. Celery Worker (`app/workers/`)

- [ ] Celery app configured with Redis as broker and result backend
- [ ] `app/workers/celery_app.py` — Celery instance
- [ ] Placeholder task to verify worker is functional: `tasks.ping()` returns `"pong"`
- [ ] Task autodiscovery from `app/workers/tasks/`

#### D. Docker Compose (`docker-compose.yml`)

- [ ] Services: `api` (FastAPI via uvicorn), `db` (PostgreSQL 16), `redis` (Redis 7), `worker` (Celery)
- [ ] Volumes: `postgres_data` for DB persistence
- [ ] Networks: shared network for inter-service communication
- [ ] Environment variables passed via `.env` file
- [ ] API hot-reloads on code changes (volume mount + `--reload`)
- [ ] Health checks on `db` and `redis` services
- [ ] Worker depends on `db` and `redis`

#### E. Configuration Files

- [ ] `app/requirements.txt` — FastAPI, uvicorn, SQLAlchemy, asyncpg, alembic, celery, redis, python-jose, passlib
- [ ] `.env.example` — Template with all required environment variables
- [ ] `app/config.py` — Pydantic Settings class loading from environment

#### F. Tests (`tests/test_app/test_scaffold.py`)

- [ ] TDD first
- [ ] Test health check endpoint returns 200
- [ ] Test CORS headers present on responses
- [ ] Test Celery ping task executes and returns "pong"
- [ ] Test database connection succeeds
- [ ] Minimum: 4+ tests

#### G. Documentation

- [ ] Add PA-01 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/PA-01-fastapi-scaffold
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Tech stack | R5-Q7 | FastAPI + React + PostgreSQL + Celery + Redis — matches Nerdy's existing stack |
| Deployment | R5-Q10 | Single-VM Docker Compose. No Kubernetes. Keep it simple. |
| Background jobs | R5-Q4 | Celery processes pipeline runs asynchronously; Redis for broker + pub/sub progress |

### Files to Create

| File | Why |
|------|-----|
| `app/api/main.py` | FastAPI application entry point |
| `app/api/__init__.py` | Package init |
| `app/config.py` | Pydantic Settings for environment config |
| `app/models/base.py` | SQLAlchemy declarative base |
| `app/models/__init__.py` | Package init |
| `app/workers/celery_app.py` | Celery instance configuration |
| `app/workers/tasks/__init__.py` | Task autodiscovery package |
| `app/workers/tasks/ping.py` | Placeholder ping task |
| `docker-compose.yml` | Local dev stack |
| `.env.example` | Environment variable template |
| `app/requirements.txt` | Python dependencies |
| `tests/test_app/test_scaffold.py` | Scaffold tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `docs/reference/prd.md` (Section 4.7) | Application layer architecture spec |
| `docs/reference/prd.md` (Section 4.2) | Directory structure showing app/ layout |
| `.cursor/rules/pipeline-patterns.mdc` | Pipeline architecture patterns |

---

## Definition of Done

- [ ] `docker compose up` starts API, DB, Redis, and Celery worker
- [ ] `GET /health` returns 200 with `{"status": "ok"}`
- [ ] Celery ping task executes successfully
- [ ] Database connection established
- [ ] CORS configured for local dev
- [ ] Alembic initialized with baseline migration
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**PA-02 (Database schema — users & sessions)** defines the PostgreSQL tables for users, sessions, and curated sets. It depends on the SQLAlchemy base and Alembic setup from this ticket.
