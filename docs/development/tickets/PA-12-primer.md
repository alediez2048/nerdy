# PA-12 Primer: Docker Compose Production Deployment

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-01 (dev Docker Compose), all PA-01 through PA-11 tickets should be complete or near-complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PA-12 creates the **production Docker Compose configuration** that deploys the full application on a single VM. The stack includes: Nginx reverse proxy serving the static React build with auto-HTTPS (via Let's Encrypt), FastAPI application server, PostgreSQL database, Celery worker, and Redis. All configuration is driven by environment variables for portability across environments.

### Why It Matters

- **One-command deployment** is an acceptance criterion: `docker compose -f docker-compose.prod.yml up` must serve the full application
- Production needs differ from development: static file serving, HTTPS, process management, health checks, restart policies
- Environment variable configuration enables deployment to any VM without code changes
- The reviewer must be able to run the entire system — a broken deployment means zero points for the application layer

---

## What Was Already Done

- PA-01: Development Docker Compose (`docker-compose.yml`) with FastAPI, PostgreSQL, Celery, Redis
- All PA-01 through PA-11: Complete application layer (auth, sessions, progress, dashboard, curation, sharing)
- Frontend: React app (Vite) with all pages and components

---

## What This Ticket Must Accomplish

### Goal

Create a production Docker Compose configuration that serves the full application with Nginx, auto-HTTPS, and environment variable configuration on a single VM.

### Deliverables Checklist

#### A. Production Docker Compose (`docker-compose.prod.yml`)

- [ ] Services:
  - **nginx** — Reverse proxy + static file server
  - **api** — FastAPI application (Gunicorn + Uvicorn workers)
  - **db** — PostgreSQL with persistent volume
  - **worker** — Celery worker (same image as api, different entrypoint)
  - **redis** — Redis with persistent volume
- [ ] All services use `restart: unless-stopped`
- [ ] Health checks on all services
- [ ] Named volumes for PostgreSQL data and Redis data
- [ ] Internal network for inter-service communication
- [ ] Only Nginx exposes ports (80, 443)

#### B. Nginx Configuration (`deploy/nginx/nginx.conf`)

- [ ] HTTPS termination with auto-renewal (Let's Encrypt via Certbot or acme-companion)
- [ ] HTTP -> HTTPS redirect
- [ ] Serve static React build from `/usr/share/nginx/html`
- [ ] Reverse proxy `/api/*` to FastAPI container
- [ ] Reverse proxy `/api/sessions/*/progress` with SSE-specific settings (no buffering, long timeouts)
- [ ] Security headers: HSTS, X-Content-Type-Options, X-Frame-Options, CSP
- [ ] Gzip compression for static assets
- [ ] Client-side caching for static assets (1 year for hashed files)

#### C. API Dockerfile (`Dockerfile.prod`)

- [ ] Multi-stage build:
  - Stage 1: Install Python dependencies
  - Stage 2: Copy app code + dependencies into slim runtime image
- [ ] Run as non-root user
- [ ] Gunicorn with Uvicorn workers: `gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker`
- [ ] Health check endpoint: `GET /health`
- [ ] Expose port 8000 (internal only)

#### D. Frontend Build (`Dockerfile.frontend`)

- [ ] Multi-stage build:
  - Stage 1: `npm install && npm run build` (Vite production build)
  - Stage 2: Copy `dist/` into Nginx image
- [ ] Environment variable injection at build time for API URL
- [ ] Output: Nginx image serving static files + reverse proxy config

#### E. Environment Configuration (`.env.example`)

- [ ] All secrets and configuration via environment variables:
  - `DOMAIN` — production domain name (for HTTPS cert)
  - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
  - `REDIS_URL`
  - `SECRET_KEY` — JWT signing key
  - `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` — OAuth credentials
  - `GEMINI_API_KEY` — Gemini API key
  - `ALLOWED_EMAIL_DOMAIN` — SSO domain restriction (default: `nerdy.com`)
  - `API_URL` — internal API URL for frontend build
  - `CERTBOT_EMAIL` — email for Let's Encrypt registration
- [ ] `.env.example` with placeholder values and comments
- [ ] `.env` in `.gitignore` (should already be)

#### F. Database Initialization (`deploy/init-db.sh`)

- [ ] Run Alembic migrations on first startup
- [ ] Idempotent — safe to re-run on restarts
- [ ] Waits for PostgreSQL to be ready before running migrations

#### G. Deployment Script (`deploy/deploy.sh`)

- [ ] Pull latest code
- [ ] Build images: `docker compose -f docker-compose.prod.yml build`
- [ ] Run migrations
- [ ] Start/restart services: `docker compose -f docker-compose.prod.yml up -d`
- [ ] Verify health checks pass
- [ ] Print status summary

#### H. Tests

- [ ] Test `docker compose -f docker-compose.prod.yml config` validates without errors
- [ ] Test health check endpoints respond
- [ ] Test Nginx serves static files
- [ ] Test Nginx proxies API requests
- [ ] Test HTTPS redirect works (manual verification documented)
- [ ] Smoke test documented in deployment guide

#### I. Documentation

- [ ] Add PA-12 entry in `docs/DEVLOG.md`
- [ ] Deployment instructions in `docs/DEPLOYMENT.md`:
  - Prerequisites (Docker, domain, DNS)
  - Configuration (copy `.env.example`, fill values)
  - First deployment steps
  - Update/redeploy steps
  - Backup and restore
  - Troubleshooting

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/PA-12-production-deployment
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Production deployment | R5-Q10 | Docker Compose on single VM: Nginx + FastAPI + PostgreSQL + Celery + Redis with auto-HTTPS |
| Environment config | R5-Q10 | All secrets and configuration via environment variables — no hardcoded values |
| One-command deploy | Acceptance | `docker compose -f docker-compose.prod.yml up` must serve the full application |

### Files to Create

| File | Why |
|------|-----|
| `docker-compose.prod.yml` | Production Docker Compose configuration |
| `Dockerfile.prod` | Production API image (multi-stage) |
| `Dockerfile.frontend` | Frontend build + Nginx image |
| `deploy/nginx/nginx.conf` | Nginx reverse proxy + HTTPS configuration |
| `deploy/init-db.sh` | Database migration script |
| `deploy/deploy.sh` | Deployment automation script |
| `.env.example` | Environment variable template |
| `docs/DEPLOYMENT.md` | Deployment guide |

### Files to Modify

| File | Action |
|------|--------|
| `app/main.py` | Add `/health` endpoint if not present |
| `.gitignore` | Ensure `.env` is ignored |
| `docs/DEVLOG.md` | Add ticket entry |

### Files You Should NOT Modify

- `docker-compose.yml` — keep the development compose file unchanged
- `Dockerfile` (if exists) — keep the development Dockerfile unchanged; create `Dockerfile.prod` separately

### Files You Should READ for Context

| File | Why |
|------|-----|
| PA-01 primer | Development Docker Compose structure |
| `docker-compose.yml` | Existing dev compose configuration to mirror and extend |
| PA-07 primer | SSE endpoint — Nginx needs special proxy settings for SSE |
| `docs/reference/ENVIRONMENT.md` | Existing setup/config guide |

---

## Suggested Implementation Pattern

```yaml
# docker-compose.prod.yml
version: "3.8"

services:
  nginx:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./deploy/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - certbot-data:/etc/letsencrypt
    depends_on:
      api:
        condition: service_healthy
    restart: unless-stopped

  api:
    build:
      context: .
      dockerfile: Dockerfile.prod
    env_file: .env
    command: gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  worker:
    build:
      context: .
      dockerfile: Dockerfile.prod
    env_file: .env
    command: celery -A app.workers.celery_app worker -l info
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    env_file: .env
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres-data:
  redis-data:
  certbot-data:
```

```nginx
# deploy/nginx/nginx.conf (key SSE proxy section)
location /api/sessions/ {
    proxy_pass http://api:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;

    # SSE-specific settings for progress endpoints
    location ~ /api/sessions/.+/progress$ {
        proxy_pass http://api:8000;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }
}
```

---

## Edge Cases to Handle

1. First deployment with no SSL cert — Nginx must start in HTTP-only mode, obtain cert, then reload with HTTPS
2. Database not ready when API starts — `depends_on` with health check + migration script with retry loop
3. Celery worker crashes — `restart: unless-stopped` auto-restarts; checkpoint-resume (P0-08) recovers pipeline state
4. Redis data lost on restart — progress events are ephemeral; ledger (JSONL) is the source of truth
5. Disk full on PostgreSQL volume — health check fails; alert via container logs
6. SSE connections through Nginx — must disable proxy buffering and set long read timeouts
7. Frontend environment variables — must be injected at build time (not runtime) since Vite bakes them in

---

## Definition of Done

- [ ] `docker compose -f docker-compose.prod.yml up` serves the full application with HTTPS
- [ ] Nginx serves static React build and proxies API requests
- [ ] SSE streaming works through Nginx reverse proxy
- [ ] All services have health checks and restart policies
- [ ] PostgreSQL and Redis data persists across restarts
- [ ] Environment variable configuration — no hardcoded secrets
- [ ] `.env.example` documents all required variables
- [ ] Database migrations run automatically on first startup
- [ ] Deployment guide written
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time

| Task | Estimate |
|------|----------|
| docker-compose.prod.yml | 25 min |
| Dockerfile.prod (API) | 20 min |
| Dockerfile.frontend (React + Nginx) | 20 min |
| Nginx configuration (HTTPS, proxy, SSE) | 25 min |
| Database init + deploy scripts | 15 min |
| .env.example + docs/DEPLOYMENT.md | 20 min |
| Smoke testing + verification | 15 min |
| DEVLOG update | 5–10 min |

---

## After This Ticket: What Comes Next

**PA-12 completes the Application Layer (Phase 1B).** The full stack is now deployable:
- FastAPI backend (PA-01) with auth (PA-03), sessions (PA-04), progress (PA-07), curation (PA-10), sharing (PA-11)
- React frontend with brief config (PA-05), session list (PA-06), Watch Live (PA-08), dashboard (PA-09)
- PostgreSQL + Redis + Celery infrastructure
- Production Nginx + HTTPS deployment

The application layer is ready to wrap the pipeline. Continue with Phase 2 (Testing & Validation) and Phase 3 (A/B Variants) on the pipeline track.
