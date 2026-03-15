# PA-12 Primer: Docker Compose Production Deployment

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-01 through PA-11 must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PA-12 wraps the entire application in a **production-ready Docker Compose** setup — Nginx reverse proxy serving static React + proxying to FastAPI, PostgreSQL, Celery worker, Redis, and auto-HTTPS (R5-Q10, Section 4.7.9).

### Why It Matters

- **The Tool Is the Product** (Pillar 9): A product that can't be deployed isn't a product
- Single-command deployment: `docker compose -f docker-compose.prod.yml up` serves the full app
- Nginx handles HTTPS termination, static file serving, and SSE proxying
- Estimated cost: $20–50/month on a single VM (Railway, Render, or bare VPS)

---

## What Was Already Done

- PA-01: Development `docker-compose.yml` with FastAPI, PostgreSQL, Redis, Celery worker
- PA-01: `Dockerfile.api` for API + worker image
- PA-05: React (Vite) frontend project in `app/frontend/`
- All PA tickets: complete application with auth, sessions, dashboard, curation, sharing

---

## What This Ticket Must Accomplish

### Goal

Create a production Docker Compose stack with Nginx, built React frontend, FastAPI, PostgreSQL, Celery, Redis, and HTTPS. One command to deploy.

### Deliverables Checklist

#### A. Production Docker Compose (`docker-compose.prod.yml`)

- [ ] Services:
  - `nginx` — Nginx reverse proxy + static React files
  - `api` — FastAPI via uvicorn (no `--reload`, workers=4)
  - `db` — PostgreSQL 16 with health check
  - `redis` — Redis 7 with health check
  - `worker` — Celery worker
- [ ] Volumes: `postgres_data`, `certbot_conf`, `certbot_www`
- [ ] Networks: shared internal network
- [ ] Environment: production `.env` file with real secrets
- [ ] Restart policy: `restart: unless-stopped` on all services
- [ ] Resource limits on services (optional but recommended)

#### B. Nginx Configuration (`deploy/nginx/nginx.conf`)

- [ ] HTTPS termination (Let's Encrypt via Certbot)
- [ ] HTTP → HTTPS redirect
- [ ] Serve React static files from `/usr/share/nginx/html`
- [ ] Proxy `/api/` to FastAPI backend
- [ ] SSE-specific proxy settings for `/api/sessions/*/progress`:
  - `proxy_buffering off`
  - `proxy_cache off`
  - `proxy_read_timeout 86400s`
  - `X-Accel-Buffering: no`
- [ ] Security headers: `X-Frame-Options`, `X-Content-Type-Options`, `Strict-Transport-Security`
- [ ] Gzip compression for static assets
- [ ] Client max body size (for file uploads if any)

#### C. Frontend Dockerfile (`deploy/Dockerfile.frontend`)

- [ ] Multi-stage build:
  1. Build stage: `node:20-alpine`, `npm ci`, `npm run build`
  2. Production stage: `nginx:alpine`, copy built files to `/usr/share/nginx/html`
- [ ] Or: combine with Nginx service (copy built files into Nginx image)

#### D. Production API Dockerfile (`deploy/Dockerfile.api`)

- [ ] Based on `Dockerfile.api` but production-optimized:
  - No `--reload`
  - `uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --workers 4`
  - Non-root user
  - Health check: `CMD curl -f http://localhost:8000/health || exit 1`

#### E. Database Initialization (`deploy/init-db.sh`)

- [ ] Script to run Alembic migrations on first start
- [ ] Idempotent — safe to run multiple times
- [ ] Called by API service entrypoint before uvicorn starts

#### F. Deploy Script (`deploy/deploy.sh`)

- [ ] Pull latest code
- [ ] Build images: `docker compose -f docker-compose.prod.yml build`
- [ ] Run migrations
- [ ] Start/restart services: `docker compose -f docker-compose.prod.yml up -d`
- [ ] Health check verification
- [ ] Optional: `--init` flag for first-time setup (Certbot, DB init)

#### G. Environment Template (`.env.production.example`)

- [ ] All required production environment variables:
  - `DATABASE_URL` (production PostgreSQL)
  - `REDIS_URL` (production Redis)
  - `GOOGLE_CLIENT_ID` (Google Cloud Console)
  - `SECRET_KEY` (strong random string)
  - `GEMINI_API_KEY` (for pipeline)
  - `DOMAIN` (for Nginx + HTTPS)
  - `CERTBOT_EMAIL` (for Let's Encrypt)

#### H. Tests

- [ ] Test `docker compose -f docker-compose.prod.yml config` validates without errors
- [ ] Test Nginx config syntax: `nginx -t`
- [ ] Test health check endpoint accessible through Nginx
- [ ] Minimum: 3+ tests (can be manual verification steps documented)

#### I. Documentation

- [ ] Add PA-12 entry in `docs/DEVLOG.md`
- [ ] Create `docs/DEPLOYMENT.md` with:
  - Prerequisites (Docker, domain, Google OAuth credentials)
  - First-time setup steps
  - Update/redeploy steps
  - Troubleshooting common issues
  - Backup and restore

---

## Important Context

### Deployment Architecture (PRD Section 4.7.9)

```
┌──────────────────────────────────────────────────┐
│  Docker Compose (Single VM — Railway/Render)     │
│                                                   │
│  ┌─────────────┐  ┌──────────────────────────┐   │
│  │  Nginx       │  │  FastAPI                  │   │
│  │  (reverse    │──│  - REST API               │   │
│  │   proxy)     │  │  - SSE endpoint           │   │
│  │  + React     │  │  - Google SSO             │   │
│  │   (static)   │  │  - Pipeline orchestration │   │
│  └─────────────┘  └──────────────────────────┘   │
│                          │                         │
│  ┌─────────────┐  ┌──────────────────────────┐   │
│  │  PostgreSQL  │  │  Celery Worker            │   │
│  │  - Users     │  │  - Background pipeline    │   │
│  │  - Sessions  │  │    execution              │   │
│  │  - Curation  │  │  - Progress reporting     │   │
│  └─────────────┘  └──────────────────────────┘   │
│                          │                         │
│                   ┌──────────────────────────┐   │
│                   │  Redis                    │   │
│                   │  - Celery broker          │   │
│                   │  - SSE pub/sub            │   │
│                   └──────────────────────────┘   │
└──────────────────────────────────────────────────┘
```

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Single VM | R5-Q10 | No Kubernetes. Docker Compose on one machine. |
| Nginx + static React | R5-Q10 | Nginx serves built React, proxies API. |
| Auto-HTTPS | R5-Q10 | Let's Encrypt via Certbot. |
| SSE through Nginx | R5-Q4 | Requires `proxy_buffering off` for real-time streaming. |

### Files to Create

| File | Why |
|------|-----|
| `docker-compose.prod.yml` | Production stack definition |
| `deploy/nginx/nginx.conf` | Nginx configuration |
| `deploy/Dockerfile.frontend` | React build + Nginx image |
| `deploy/Dockerfile.api` | Production API image |
| `deploy/init-db.sh` | Database migration script |
| `deploy/deploy.sh` | Deployment automation |
| `.env.production.example` | Production env template |
| `docs/DEPLOYMENT.md` | Deployment guide |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `docs/reference/prd.md` (Section 4.7.9) | Deployment architecture spec |
| `docker-compose.yml` | Dev stack to extend for production |
| `Dockerfile.api` | Dev Dockerfile to harden for production |
| `app/api/main.py` | FastAPI app entry point |
| `app/frontend/package.json` | Frontend build configuration |

---

## Definition of Done

- [ ] `docker compose -f docker-compose.prod.yml up` starts full production stack
- [ ] Nginx serves React at `/`, proxies API at `/api/`
- [ ] HTTPS working with Let's Encrypt (or self-signed for demo)
- [ ] SSE streaming works through Nginx (no buffering)
- [ ] Security headers present
- [ ] Database migrations run on startup
- [ ] `deploy/deploy.sh` automates the full deploy flow
- [ ] `docs/DEPLOYMENT.md` written
- [ ] DEVLOG updated

---

## Estimated Time: 60–90 minutes

---

## After This Ticket: What Comes Next

**This is the final PA ticket.** After PA-12, the application layer is complete. The project is fully deployed and ready for demo.
