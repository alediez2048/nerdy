# Ad-Ops-Autopilot — Production Environment

**Last updated:** March 22, 2026

---

## Architecture Overview

```
                    ┌─────────────────────────────────┐
                    │         Clerk (Auth)             │
                    │  assured-ray-60.clerk.accounts   │
                    │  Sign-in gate + user sessions    │
                    └──────────┬──────────────────────┘
                               │ JWT token
                    ┌──────────▼──────────────────────┐
                    │     Vercel (Frontend)            │
                    │  nerdy-7oqg.vercel.app           │
                    │  React SPA (Vite build)          │
                    │  Branch: main                    │
                    │  Root: app/frontend              │
                    └──────────┬──────────────────────┘
                               │ /api/* rewrites
                    ┌──────────▼──────────────────────┐
                    │     Railway (Backend)            │
                    │                                  │
                    │  ┌──────────────────────────┐   │
                    │  │ nerdy (API)               │   │
                    │  │ nerdy-production-290d     │   │
                    │  │ uvicorn on port 8000      │   │
                    │  │ FastAPI + static files    │   │
                    │  └────────┬─────────────────┘   │
                    │           │                      │
                    │  ┌────────▼─────────────────┐   │
                    │  │ zonal-manifestation       │   │
                    │  │ (Celery Worker)           │   │
                    │  │ Processes pipeline jobs   │   │
                    │  └────────┬─────────────────┘   │
                    │           │                      │
                    │  ┌────────▼──┐  ┌───────────┐   │
                    │  │ PostgreSQL│  │   Redis    │   │
                    │  │ (Database)│  │ (Queue +   │   │
                    │  │           │  │  Pub/Sub)  │   │
                    │  └───────────┘  └───────────┘   │
                    └──────────────────────────────────┘
```

---

## Services

### 1. Vercel — Frontend Hosting

| Property | Value |
|----------|-------|
| **URL** | `https://nerdy-7oqg.vercel.app` |
| **Repo** | `alediez2048/nerdy` |
| **Branch** | `main` |
| **Root Directory** | `app/frontend` |
| **Framework** | Vite |
| **Build Command** | `npm run build` |
| **Output** | `dist/` |

**Environment Variables:**
```
VITE_CLERK_PUBLISHABLE_KEY = pk_test_YXNzdXJlZC1yYXktNjAuY2xlcmsuYWNjb3VudHMuZGV2JA
```

**Rewrites** (`app/frontend/vercel.json`):
```
/api/images/*  → Railway /images/*     (static image files)
/api/videos/*  → Railway /videos/*     (static video files)
/api/*         → Railway /api/*        (API endpoints)
/*             → /index.html           (SPA fallback)
```

**Deploy:** Auto-deploys on push to `main`.

---

### 2. Railway — Backend Services

#### API Service ("nerdy")

| Property | Value |
|----------|-------|
| **URL** | `https://nerdy-production-290d.up.railway.app` |
| **Dockerfile** | `Dockerfile.api` |
| **Start Command** | `uvicorn app.api.main:app --host 0.0.0.0 --port 8000` |
| **Port** | 8000 |
| **Branch** | `main` |

**Environment Variables:**
```
DATABASE_URL    = postgresql://postgres:***@postgres.railway.internal:5432/railway
REDIS_URL       = redis://default:***@redis.railway.internal:6379
GEMINI_API_KEY  = AIza***
FAL_KEY         = ***
SECRET_KEY      = nerdy-adops-jwt-secret-2026
PORT            = 8000
```

**What it serves:**
- FastAPI REST API at `/api/*`
- Static images at `/images/*` (from `output/images/`)
- Static videos at `/videos/*` (from `output/videos/`)
- Health check at `/health`

#### Worker Service ("zonal-manifestation")

| Property | Value |
|----------|-------|
| **Dockerfile** | `Dockerfile.api` (same image) |
| **Start Command** | `celery -A app.workers.celery_app worker --loglevel=info` |
| **Port** | None (no HTTP) |

**What it does:**
- Picks up pipeline jobs from Redis queue
- Runs ad generation sessions (image + video pipelines)
- Publishes progress events to Redis pub/sub
- Writes results to PostgreSQL + ledger files

**Environment Variables:** Same as API service.

#### PostgreSQL

| Property | Value |
|----------|-------|
| **Internal Host** | `postgres.railway.internal:5432` |
| **Public Host** | `caboose.proxy.rlwy.net:25560` |
| **Database** | `railway` |
| **User** | `postgres` |

**Tables:** `users`, `sessions`, `campaigns`, `curated_sets`, `curated_ads`, `share_tokens`

#### Redis

| Property | Value |
|----------|-------|
| **Internal Host** | `redis.railway.internal:6379` |

**Used for:**
- Celery task broker (job queue)
- Celery result backend
- SSE progress pub/sub (real-time session updates)
- Progress summary caching

---

### 3. Clerk — Authentication

| Property | Value |
|----------|-------|
| **Dashboard** | `assured-ray-60.clerk.accounts.dev` |
| **Mode** | Development (test keys) |
| **Sign-in Methods** | Email, Google OAuth |

**How it works:**
1. Frontend wraps app in `<ClerkProvider>`
2. Unauthenticated users see sign-in page (Clerk's `<SignIn>` component)
3. After sign-in, Clerk issues a session token
4. Token is cached in frontend and sent as `Authorization: Bearer` header
5. **Backend does NOT verify Clerk tokens** — runs in dev mode (`GOOGLE_CLIENT_ID` empty), defaults all requests to `user_id: test-user`
6. All users see the same data (shared `test-user` namespace)

**To enable per-user isolation (future):**
- Add `CLERK_SECRET_KEY` to Railway
- Update `app/api/deps.py` to verify Clerk JWT with RS256
- Migrate existing sessions to a specific Clerk user ID

---

## Data Flow

### Where Data Lives

| Data | Storage | Persistence |
|------|---------|-------------|
| Session metadata (name, status, config) | PostgreSQL | Persistent (Railway volume) |
| Campaign metadata | PostgreSQL | Persistent |
| User accounts | PostgreSQL | Persistent |
| Curated sets | PostgreSQL | Persistent |
| Session ledgers (ad scores, events) | JSONL files in Docker image | **Ephemeral** — rebuilt from git on each deploy |
| Global ledger | JSONL file in Docker image | **Ephemeral** |
| Generated images | PNG files in Docker image | **Ephemeral** |
| Generated videos | MP4 files in Docker image | **Ephemeral** |
| Competitive data | JSON files in Docker image | **Ephemeral** |

**Important:** Files baked into the Docker image are rebuilt from git on every deploy. If new sessions are created on production, their ledger/media files will be lost on the next deploy unless committed to git first.

### Request Flow

```
Browser → Vercel (SPA) → /api/* rewrite → Railway API → PostgreSQL/Redis/Files
                                         → /images/* → Static file serve
                                         → /videos/* → Static file serve
```

### Session Creation Flow

```
User clicks "Create Session"
  → Frontend POST /api/sessions
  → Railway API creates DB record (status: pending)
  → Fires Celery task: run_pipeline_session(session_id)
  → Returns immediately

Celery Worker picks up task
  → Sets status: running
  → Generates ads (Gemini API)
  → Generates images/videos (Gemini/Fal.ai)
  → Evaluates (5-dimension scoring)
  → Writes to session ledger + saves images
  → Sets status: completed

Frontend polls for progress via SSE
  → Worker publishes events to Redis pub/sub
  → API streams events to frontend via EventSource
```

---

## Deployment Process

### Deploying Code Changes

1. Commit and push to `final-submission` branch
2. Merge to `main`: `git checkout main && git merge final-submission && git push origin main`
3. Railway auto-deploys API + Worker from `main`
4. Vercel auto-deploys frontend from `main`

### Deploying Data Changes

If new sessions were run locally and need to appear on production:

1. Commit session data:
   ```bash
   git add -f data/sessions/ output/images/ output/videos/ data/ledger.jsonl
   git commit -m "data: add new session data"
   ```
2. Push and merge to `main`
3. Railway rebuilds Docker image with new files
4. Re-seed PostgreSQL if new session DB records exist:
   ```bash
   docker compose exec db pg_dump -U postgres nerdy > nerdy_backup.sql
   /opt/homebrew/opt/postgresql@16/bin/psql "postgresql://postgres:***@caboose.proxy.rlwy.net:25560/railway" < nerdy_backup.sql
   ```

### Database Management

**Export local → production:**
```bash
docker compose exec db pg_dump -U postgres nerdy > nerdy_backup.sql
/opt/homebrew/opt/postgresql@16/bin/psql "RAILWAY_PUBLIC_URL" < nerdy_backup.sql
```

**Connect to production DB:**
```bash
/opt/homebrew/opt/postgresql@16/bin/psql "postgresql://postgres:***@caboose.proxy.rlwy.net:25560/railway"
```

---

## Limitations

1. **No persistent file storage:** Railway containers are ephemeral. Generated images/videos/ledgers are baked into the Docker image from git. New sessions created on production will lose their files on the next deploy.

2. **Auth is cosmetic:** Clerk gates the UI but the backend treats all users as `test-user`. No per-user data isolation.

3. **No CDN for media:** Images and videos are served directly from the Railway container via FastAPI static file mount. For production scale, these should be on S3/R2 with a CDN.

4. **Single-region:** Railway API runs in us-west2 only. No multi-region or auto-scaling beyond the single replica.

5. **No automated backups for files:** PostgreSQL has Railway's built-in backups. Ledger/media files depend on git history.

---

## Monitoring

- **Railway Dashboard:** Logs, metrics, deployment history for API + Worker
- **Vercel Dashboard:** Build logs, deployment history, edge network stats
- **Clerk Dashboard:** User sign-ins, session activity
- **Health Check:** `https://nerdy-production-290d.up.railway.app/health`

---

## Costs (Estimated)

| Service | Plan | Est. Monthly |
|---------|------|-------------|
| Railway (API + Worker + PostgreSQL + Redis) | Hobby | ~$10-20 |
| Vercel (Frontend) | Hobby (free) | $0 |
| Clerk (Auth) | Free tier | $0 |
| Gemini API | Pay-per-use | ~$5-10 |
| Fal.ai (Video) | Pay-per-use | ~$5-15 |
