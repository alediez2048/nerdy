# Environment Guide

Quick reference for running, testing, and troubleshooting the Ad-Ops-Autopilot pipeline.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│  LOCAL (Development)                                                 │
│                                                                      │
│  Python venv                                                         │
│    └─ Pipeline (generate → evaluate → iterate)                       │
│         ↕                                                             │
│  Gemini API (Flash + Pro)                                            │
│    └─ Generation, evaluation, brief expansion, context distillation  │
│         ↕                                                             │
│  Append-only JSONL ledger (data/ledger.jsonl)                        │
│    └─ Decision log, checkpoints, token attribution                   │
│         ↕                                                             │
│  Local data: brand_knowledge.json, reference_ads.json, config.yaml   │
│                                                                      │
│  v2: Imagen / Flux (image generation)                                │
│  v3: Meta Ad Library (competitive intelligence — manual/semi-auto)   │
└──────────────────────────────────────────────────────────────────────┘
```

**The pipeline runs entirely locally. No database, no deployed API. All state lives in the append-only ledger and data files.**

---

## 0. API Keys & External Services

### Required Accounts (Sign Up Before Starting)

| Service | Sign Up URL | What You Get | Cost |
|---|---|---|---|
| Google AI (Gemini) | https://ai.google.dev/ | `GEMINI_API_KEY` — generation + evaluation | Free tier: 15 RPM (Flash), 2 RPM (Pro) |
| Meta Ad Library | https://facebook.com/ads/library | Competitor ad research | Free (no API — manual collection) |

### Optional (v2+)

| Service | Sign Up URL | What You Get | Cost |
|---|---|---|---|
| Imagen / Flux / Nano Banana | Varies | Image generation for v2 | Pay-per-use |

### Verifying API Keys

```bash
# Gemini API — should return a response
curl -sS "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=$GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Say hello"}]}]}' | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK' if 'candidates' in d else f'ERROR: {d.get(\"error\", d)}")"
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

### 1.3 Verify Setup

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

### 1.4 Run Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific category
python -m pytest tests/test_evaluation/ -v
python -m pytest tests/test_pipeline/ -v

# With short traceback
python -m pytest tests/ -v --tb=short
```

### 1.5 Lint

```bash
ruff check . --fix
```

### 1.6 Generate Quality Report

```bash
# After pipeline run — visualize quality trends
python -m output.visualize  # or equivalent script
# Output: quality trend charts, cost per ad, correlation matrix
```

---

## 2. Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | Yes | — | Google AI API key for Gemini (Flash + Pro) |
| `GLOBAL_SEED` | No | From config | Reproducibility seed; overrides config if set |
| `LEDGER_PATH` | No | `data/ledger.jsonl` | Path to append-only decision ledger |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |

---

## 3. Config Reference (`data/config.yaml`)

| Key | Default | Description |
|---|---|---|
| `quality_threshold` | 7.0 | Minimum weighted average to publish |
| `batch_size` | 10 | Ads per batch (parallel within stage) |
| `max_regeneration_cycles` | 3 | Max attempts before brief mutation / escalation |
| `pareto_variants` | 5 | Variants per regeneration cycle |
| `ratchet_window` | 5 | Batches for rolling high-water mark |
| `ratchet_buffer` | 0.5 | Buffer below rolling avg for effective threshold |
| `clarity_floor` | 6.0 | Hard minimum — violation = reject |
| `brand_voice_floor` | 5.0 | Hard minimum — violation = reject |
| `improvable_range` | [5.5, 7.0] | Ads in this range escalate to Gemini Pro |

---

## 4. Key Files

| File | Purpose |
|---|---|
| `.env` | Local environment variables (gitignored — never commit) |
| `.env.example` | Template for `.env` — copy and fill in |
| `data/config.yaml` | Tunable pipeline parameters |
| `data/brand_knowledge.json` | Verified Varsity Tutors facts (P0-04) |
| `data/reference_ads.json` | Labeled reference ads (P0-05) |
| `data/pattern_database.json` | Structural atoms for generation (P0-05) |
| `data/ledger.jsonl` | Append-only decision log (created on first run) |
| `requirements.txt` | Python dependencies |
| `prd.md` | Product requirements document |
| `interviews.md` | 30 architectural pressure-test Q&As |
| `docs/development/DEVLOG.md` | Development log — updated after every ticket |
| `docs/development/tickets/*-primer.md` | Ticket primers |
| `docs/deliverables/decisionlog.md` | Decision log — design rationale and trade-offs |
| `docs/deliverables/systemsdesign.md` | Systems design — architecture documentation |
| `docs/reference/ENVIRONMENT.md` | This file |

---

## 5. Common Pitfalls and Fixes

### Gemini Rate Limiting (429)

**Symptom:** `429 Too Many Requests` or `ResourceExhausted`.

**Cause:** Free tier limits — 15 RPM (Flash), 2 RPM (Pro). Batch processing can hit these quickly.

**Fix:**
- Pipeline uses checkpoint-resume: interrupt, wait, run `python run_pipeline.py --resume`
- Configurable delay between API calls in config
- Reduce `batch_size` to 5 if needed
- Tiered routing (P1-06) reduces Pro calls by concentrating on improvable-range ads only

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

---

## 6. Quick Reference Card

```
SETUP:     python3.10 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
CONFIG:    cp .env.example .env  (then add GEMINI_API_KEY)
RUN:       python run_pipeline.py
RESUME:    python run_pipeline.py --resume
TEST:      python -m pytest tests/ -v
LINT:      ruff check . --fix
REPORT:    python -m output.visualize  (or equivalent)
```

---

## 7. Pre-Demo Checklist

Before any demo or submission, run these checks:

### 7.1 Pipeline Completes

```bash
python run_pipeline.py
# Should complete without crash; 50+ ads with evaluation scores
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

### 7.3 Tests Pass

```bash
python -m pytest tests/ -v
```

### 7.4 One-Command Setup Works

```bash
# Fresh clone, new venv
pip install -r requirements.txt
# Should complete without errors
```

### 7.5 Summary

| Check | Blocking for Demo? |
|---|---|
| Pipeline runs end-to-end | Yes |
| 50+ ads generated and evaluated | Yes |
| Quality trend shows improvement | Yes |
| Tests pass | Yes |
| Decision log complete | Yes |
| Narrated replay generated | Recommended |
