# Environment Guide

Quick reference for running, testing, and troubleshooting the Ad-Ops-Autopilot pipeline.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│  PIPELINE (CLI — runs locally)                                           │
│                                                                          │
│  Python venv                                                             │
│    └─ Pipeline (generate → evaluate → iterate → output)                  │
│         ↕                                                                │
│  Gemini API                                                              │
│    ├─ Flash — generation, evaluation, brief expansion, distillation      │
│    ├─ Pro — improvable-range regeneration (5.5–7.0 score)                │
│    └─ Nano Banana Pro (Gemini 3 Pro Image) — ad image generation (P1)    │
│         ↕                                                                │
│  Append-only JSONL ledger (data/ledger.jsonl)                            │
│    └─ Decision log, checkpoints, token attribution, snapshots            │
│         ↕                                                                │
│  Local data files                                                        │
│    ├─ brand_knowledge.json, reference_ads.json, config.yaml              │
│    └─ competitive/patterns.json (Meta Ad Library extraction, P0-09)      │
│                                                                          │
│  v2 (P3): Veo 3.1 Fast (UGC video), Nano Banana 2 (cheap image tier)    │
├──────────────────────────────────────────────────────────────────────────┤
│  APPLICATION LAYER (P1B — optional web wrapper)                          │
│                                                                          │
│  FastAPI + Celery + Redis (background pipeline execution)                │
│  PostgreSQL (users, sessions, curation state)                            │
│  React (brief config, session list, progress view, dashboard)            │
│  Docker Compose (local dev + production deployment)                      │
└──────────────────────────────────────────────────────────────────────────┘
```

**The pipeline runs entirely locally via CLI.** The application layer (P1B) is an optional web wrapper — the pipeline is always CLI-testable regardless.

---

## 0. API Keys & External Services

### Required Accounts (Sign Up Before Starting)

| Service | Sign Up URL | What You Get | Cost |
|---|---|---|---|
| Google AI (Gemini) | https://ai.google.dev/ | `GEMINI_API_KEY` — text generation, evaluation, image generation (Nano Banana Pro uses same key) | Free tier: 15 RPM (Flash), 2 RPM (Pro) |
| Meta Ad Library | https://facebook.com/ads/library | Competitor ad research (P0-09) | Free (no API — manual/semi-auto via Claude in Chrome) |

### Additional Services (by phase)

| Service | Phase | What You Get | Cost |
|---|---|---|---|
| Nano Banana Pro (Gemini 3 Pro Image) | P1 | Ad image generation — same `GEMINI_API_KEY` | ~$0.13/image |
| Nano Banana 2 (Gemini 3.1 Flash Image) | P3 | Cheap image tier for A/B variant volume | ~$0.02–0.05/image |
| Veo 3.1 Fast | P3 | UGC video for Stories/Reels — same `GEMINI_API_KEY` | ~$0.15/sec (~$0.90/6-sec video) |
| PostgreSQL + Redis | P1B | Application layer state | Local (Docker) |

### Verifying API Keys

```bash
# Gemini API — should return a response
curl -sS "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=$GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Say hello"}]}]}' | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK' if 'candidates' in d else f'ERROR: {d.get(\"error\", d)}')"
```

---

## 1. Local Development Environment

### 1.1 Initial Setup (First Time Only)

```bash
# 1. Clone the repo
git clone <repo-url>
cd nerdy

# 2. Create Python virtual environment
python3.10 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your API keys (see section 0)

# 5. Verify setup
python -c "import os; from dotenv import load_dotenv; load_dotenv(); k=os.getenv('GEMINI_API_KEY'); print('GEMINI_API_KEY loaded:', bool(k))"
```

### 1.2 Run the Pipeline

```bash
# From repo root, with venv activated
python run_pipeline.py

# With checkpoint resume (after interruption)
python run_pipeline.py --resume

# Limit ads for testing
python run_pipeline.py --max-ads 10
```

### 1.3 Run the Dashboard (after P5)

```bash
# Export dashboard data from ledger
python export_dashboard.py

# Open the dashboard
open output/dashboard.html   # macOS
# or: xdg-open output/dashboard.html   # Linux
```

### 1.4 Run the Application Layer (P1B — optional)

```bash
# Start all services (FastAPI, PostgreSQL, Redis, Celery)
docker compose up

# Production deployment
docker compose -f docker-compose.prod.yml up
```

### 1.5 Verify Setup

```bash
# Config loads correctly
python -c "
import yaml
with open('data/config.yaml') as f:
    cfg = yaml.safe_load(f)
print('Config OK:', 'quality_threshold' in cfg)
"

# Ledger exists and is valid JSONL (after first run)
python -c "
import json
try:
    with open('data/ledger.jsonl') as f:
        [json.loads(l) for l in f if l.strip()]
    print('Ledger OK')
except FileNotFoundError:
    print('Ledger not yet created (run pipeline first)')
"
```

### 1.6 Run Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific category
python -m pytest tests/test_evaluation/ -v
python -m pytest tests/test_pipeline/ -v

# With short traceback
python -m pytest tests/ -v --tb=short
```

### 1.7 Lint

```bash
ruff check . --fix
```

---

## 2. Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | Yes | — | Google AI API key for Gemini Flash, Pro, Nano Banana Pro, and Veo |
| `GLOBAL_SEED` | No | From config | Reproducibility seed; overrides config.yaml if set |
| `LEDGER_PATH` | No | `data/ledger.jsonl` | Path to append-only decision ledger |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |

---

## 3. Config Reference (`data/config.yaml`)

| Key | Default | Description |
|---|---|---|
| `quality_threshold` | 7.0 | Minimum weighted average to publish |
| `clarity_floor` | 6.0 | Hard minimum — violation = reject regardless of aggregate |
| `brand_voice_floor` | 5.0 | Hard minimum — violation = reject regardless of aggregate |
| `batch_size` | 10 | Ads per batch (parallel within stage) |
| `max_regeneration_cycles` | 3 | Max attempts before brief mutation / escalation |
| `pareto_variants` | 5 | Variants per regeneration cycle |
| `ratchet_window` | 5 | Batches for rolling high-water mark |
| `ratchet_buffer` | 0.5 | Buffer below rolling avg for effective threshold |
| `improvable_range` | [5.5, 7.0] | Ads in this range escalate to Gemini Pro |
| `exploration_plateau_threshold` | 0.1 | Score improvement below which = plateau |
| `exploration_plateau_batches` | 3 | Consecutive plateau batches before exploring |
| `global_seed` | "nerdy-p0-default" | Root seed for deterministic reproducibility |
| `api_delay_seconds` | 1.5 | Delay between API calls (rate limiting) |
| `retry_max_attempts` | 3 | API call retry ceiling before raising |
| `ledger_path` | data/ledger.jsonl | Path to append-only event ledger |
| `cache_path` | data/cache/ | Path to result-level cache directory |

---

## 4. Key Files

| File | Purpose |
|---|---|
| `.env` | Local environment variables (gitignored — never commit) |
| `.env.example` | Template for `.env` — copy and fill in |
| `data/config.yaml` | Tunable pipeline parameters |
| `data/brand_knowledge.json` | Verified Varsity Tutors facts (P0-04) |
| `data/reference_ads.json` | Labeled reference ads for calibration (P0-05) |
| `data/competitive/patterns.json` | Competitive pattern database from Meta Ad Library (P0-09) |
| `data/ledger.jsonl` | Append-only decision log (created on first run) |
| `data/cache/` | Result-level cache with version TTL (P1-12) |
| `requirements.txt` | Python dependencies |
| `docs/reference/prd.md` | Product requirements document (81 tickets, 9 pillars, 50 Q&As) |
| `docs/reference/interviews.md` | 30 architectural Q&As (R1–R3, 10 each) |
| `docs/reference/requirements.md` | Assignment spec (scoring rubric, deliverables) |
| `docs/reference/ENVIRONMENT.md` | This file |
| `docs/development/DEVLOG.md` | Development log — updated after every ticket |
| `docs/development/tickets/*-primer.md` | Ticket primers (81 tickets across 7 phases) |
| `docs/deliverables/decisionlog.md` | Decision log — design rationale, trade-offs, failures |
| `docs/deliverables/systemsdesign.md` | Systems design — architecture documentation |
| `docs/deliverables/writeup.md` | Technical writeup (1–2 pages) |
| `docs/deliverables/ai-tools.md` | AI tools and prompts used in development |
| `output/dashboard.html` | 8-panel quality dashboard (P5-01–P5-06) |
| `output/ad_library.json` | Generated ad library with scores and rationales (P5-10) |

---

## 5. Common Pitfalls and Fixes

### Gemini Rate Limiting (429)

**Symptom:** `429 Too Many Requests` or `ResourceExhausted`.

**Cause:** Free tier limits — 15 RPM (Flash), 2 RPM (Pro). Batch processing can hit these quickly.

**Fix:**
- Pipeline uses checkpoint-resume: interrupt, wait, run `python run_pipeline.py --resume`
- Configurable delay between API calls (`api_delay_seconds` in config)
- Reduce `batch_size` to 5 if needed
- Tiered routing (P1-06) reduces Pro calls by concentrating on improvable-range ads only

### Nano Banana Pro Rate Limits

**Symptom:** Image generation stalls or returns 429.

**Cause:** Image generation shares Gemini API quota. Generating 3 variants per ad at 50 ads = 150+ image requests.

**Fix:**
- Images generate only for ads scoring ≥5.5 (post-text-triage, not all ads)
- Cache generated images by visual spec hash
- Batch image requests with `api_delay_seconds` between calls
- `--resume` recovers from mid-batch image failures

### "Module not found" Errors

**Symptom:** `ModuleNotFoundError: No module named 'generate'`

**Cause:** Running from wrong directory or without venv activated.

**Fix:**
```bash
cd /path/to/nerdy
source .venv/bin/activate
python run_pipeline.py
```

### Ledger Corruption / Invalid JSONL

**Symptom:** `json.JSONDecodeError` when reading ledger.

**Cause:** Interrupted write or manual edit.

**Fix:**
- Ledger is append-only — never edit manually
- If corrupted, backup and truncate at last valid line, or restore from backup
- Use `--resume` to avoid re-running completed work

### Evaluator Scores Everything 6–8 (Halo Effect)

**Symptom:** All dimensions correlate highly; evaluator can't distinguish good from bad.

**Cause:** Holistic scoring instead of forced decomposition; calibration drift.

**Fix:**
- Ensure 5-step chain-of-thought prompt (R3-Q6) with decomposition before scoring
- Re-run calibration (P0-06) against labeled reference ads
- Run correlation analysis (P2-02) — if r > 0.7 between dimensions, fix prompt

### Pipeline Hangs or Stalls

**Symptom:** Pipeline appears stuck with no output.

**Cause:** Rate limit backoff, network timeout, or long LLM response.

**Fix:**
- Check logs for retry messages
- Wait 60s — exponential backoff may be in progress
- If truly stuck, Ctrl+C and run with `--resume` — no work lost

### No Ads Passing Threshold

**Symptom:** All ads score below 7.0; nothing published.

**Cause:** Evaluator too strict, generator producing low-quality copy, or brief expansion missing context.

**Fix:**
- Verify evaluator calibration (P0-06): excellent reference ads should score ≥7.5
- Check brief expansion output — is it grounded and rich?
- Review contrastive rationales — are they actionable?
- Ensure reference-decompose-recombine uses proven structural atoms from pattern database

### AI Image Artifacts

**Symptom:** Generated images have distorted faces, extra fingers, warped text.

**Cause:** Known limitation of current image generation models.

**Fix:**
- Multi-variant generation (3 per ad) means artifacts in one variant don't block the ad — Pareto selection picks a clean sibling
- Attribute checklist (P1-15) catches artifacts automatically
- Targeted regen (P1-17) appends "no distortions" diagnostic
- Max 5 images per ad before flagging as "image-blocked"

---

## 6. Quick Reference Card

```
SETUP:      python3.10 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
CONFIG:     cp .env.example .env  (then add GEMINI_API_KEY)
RUN:        python run_pipeline.py
RESUME:     python run_pipeline.py --resume
TEST:       python -m pytest tests/ -v
LINT:       ruff check . --fix
DASHBOARD:  python export_dashboard.py && open output/dashboard.html
APP (P1B):  docker compose up
```

---

## 7. Pre-Demo Checklist

Before any demo or submission, run these checks:

### 7.1 Pipeline Completes

```bash
python run_pipeline.py
# Should complete without crash; 50+ full ads (copy + image) with evaluation scores
```

### 7.2 Quality Threshold Met

```bash
# Check ledger for published ads
python -c "
import json
with open('data/ledger.jsonl') as f:
    events = [json.loads(l) for l in f if l.strip()]
published = [e for e in events if e.get('event_type') == 'AdPublished']
print(f'Published ads: {len(published)}')
scores = [e.get('scores', {}).get('aggregate_score') for e in published if e.get('scores')]
if scores:
    print(f'Avg score: {sum(scores)/len(scores):.2f}')
"
```

### 7.3 Dashboard Renders

```bash
python export_dashboard.py
open output/dashboard.html
# All 8 panels should render with data
```

### 7.4 Tests Pass

```bash
python -m pytest tests/ -v
# Target: 15+ tests, all green
```

### 7.5 One-Command Setup Works

```bash
# Fresh clone, new venv
pip install -r requirements.txt
# Should complete without errors
```

### 7.6 Submission Deliverables

| Deliverable | File | Blocking? |
|---|---|---|
| Pipeline runs end-to-end | `run_pipeline.py` | Yes |
| 50+ full ads (copy + image) with scores | `output/ad_library.json` | Yes |
| Quality trend shows improvement | `output/dashboard.html` (Panel 3) | Yes |
| Tests pass (≥10) | `tests/` | Yes |
| Decision log | `docs/deliverables/decisionlog.md` | Yes |
| Technical writeup (1-2 pages) | `docs/deliverables/writeup.md` | Yes |
| AI tools and prompts documented | `docs/deliverables/ai-tools.md` | Yes |
| Demo video (≤7 min) | Recorded separately | Yes |
| 8-panel dashboard | `output/dashboard.html` | Recommended |
| README with one-command setup | `README.md` | Yes |
