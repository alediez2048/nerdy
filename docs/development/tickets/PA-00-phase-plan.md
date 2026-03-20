# Phase PA: Application Layer (Sessions, Auth & Real-Time UX)

## Context

PA wraps the CLI pipeline in a multi-user web application: FastAPI backend, React frontend, Google SSO, PostgreSQL for sessions, Celery/Redis for background pipeline execution, and real-time SSE progress updates. This is the "tool is the product" (Pillar 9) vision — but scores zero direct rubric points.

## Tickets (13)

### PA-01: FastAPI Backend Scaffold
- FastAPI + CORS + PostgreSQL + Celery + Redis, Docker Compose
- **AC:** `docker compose up` starts all services

### PA-02: Database Schema — Users & Sessions
- PostgreSQL tables: users, sessions, curated_sets
- **AC:** Migrations run, schema matches PRD Section 4.7.2

### PA-03: Google SSO Authentication
- Google OAuth 2.0, @nerdy.com restriction, JWT tokens
- **AC:** Only @nerdy.com emails can sign in

### PA-04: Session CRUD API
- POST /sessions, GET /sessions, GET /sessions/:id
- **AC:** Session creation triggers Celery job, list supports filters

### PA-05: Brief Configuration Form (React)
- Progressive disclosure: required fields visible, advanced in accordion
- Clone-from-previous for repeat users
- **AC:** Form submits to POST /sessions, clone works

### PA-06: Session List UI (React)
- Flat reverse-chronological cards with sparklines, badges, filters
- **AC:** Cards render with metadata, running sessions show progress

### PA-07: Background Job Progress Reporting
- Celery writes to Redis pub/sub, FastAPI SSE endpoint, 30s polling
- **AC:** Running sessions update in real time

### PA-08: "Watch Live" Progress View (React)
- Cycle indicator, ad count bar, live score feed, cost accumulator, trend chart, latest ad preview
- **AC:** All 6 elements update via SSE

### PA-09: Session Detail — Dashboard Integration
- Wrap 7-tab dashboard in session context, breadcrumbs, back button
- Scope data to session's ledger
- **AC:** Clicking session opens dashboard filtered to that session

### PA-10: Curation Layer + Curated Set Tab
- Select, reorder, annotate, light-edit with diff tracking, export zip
- **AC:** Selections persist, edits tracked, Meta-ready zip export

### PA-11: Share Session Link
- Read-only URL with time-limited token (7-day expiry)
- **AC:** Shared link opens read-only session

### PA-12: Docker Compose Production Deployment
- Nginx + static React + FastAPI + PostgreSQL + Celery + Redis, auto-HTTPS
- **AC:** `docker compose -f docker-compose.prod.yml up` serves full app

### PA-13: Frontend Component Build — Mockup-to-Production
- Decompose `NerdyAdGen_Dashboard_v3.jsx` into production React components
- Extract design tokens, split views/tabs, wire API, wire SSE
- **AC:** All views match mockup, zero mock data, SSE works, Lighthouse a11y ≥ 80

## Dependency Graph

```
PA-01 (FastAPI) → PA-02 (DB Schema) → PA-03 (Google SSO)
                                            │
PA-04 (Session CRUD) → PA-05 (Brief Config Form)
                            │
PA-06 (Session List) → PA-07 (Progress Reporting) → PA-08 (Watch Live)
                                                          │
PA-13 (Frontend Build) → PA-09 (Dashboard Integration) → PA-10 (Curation)
                                                               │
PA-11 (Share Link) → PA-12 (Production Deploy)
```

## Rubric Impact

- **Zero direct rubric points** — the rubric evaluates pipeline quality, evaluation, iteration, and documentation
- **High effort** — 13 tickets spanning FastAPI, React, PostgreSQL, Celery, Redis, Docker, OAuth
- **Recommendation: CUT** — invest time in P2 (validates claims) and P5 (submission deliverables) instead

## Status: ⏳ NOT STARTED (recommended to cut)
