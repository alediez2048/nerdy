# PJ-03 Primer

**Source plan:** [`PJ-00-phase-plan.md`](PJ-00-phase-plan.md) — §9.2 (Vision pass details) and §3 decision 14 (GRILL Q4 — async vision pass).
**For:** New Cursor Agent session
**Date:** 2026-06-08
**Previous work:** PJ-01 (models), PJ-02 (assets API + storage) merged. See `docs/development/DEVLOG.md`.
**Status:** ⏳ Not started

---

# Ticket PJ-03: Vision pass module (Celery task)

## What Is This Ticket?

A user drops a logo into the onboarding chat; the agent needs to know what color palette and fonts that logo carries before it asks the user "are these the right brand colors?" This ticket builds the **vision pass**: a Gemini 2.5 Flash multimodal call that takes a `brand_asset` row, probes it (palette hex codes, dominant background, detected fonts, OCR text for style-guide PDFs), and writes structured JSON into `brand_assets.extracted_facts`.

Per GRILL Q4 (PJ-00 §3 decision 14), the chat path stays synchronous but the vision pass runs **asynchronously** as a Celery task triggered by `POST /api/brand-assets/{id}/extract`. The frontend polls until ready, then includes the enriched `asset_id` in the next `/converse` call.

### Why It Matters

- Vision probes typically take 15–25s; running them inline would torpedo the chat UX.
- Decoupling vision from chat keeps the `/api/agent/converse` endpoint's p95 inside the 5–8s sync budget.
- Sets up `ingest_asset` (PJ-05 tool) to be a fast lookup rather than a slow inference.

---

## What Was Already Done

- **PJ-01** — `BrandAsset.extracted_facts JSONB` column ready to be populated.
- **PJ-02** — assets stored at `output/brand_assets/<user_id>/<uuid>.<ext>` reachable from the worker.
- `app/workers/tasks/pipeline_task.py` — pattern for a Celery task that loads a row, calls an external service, writes results back.
- `generate/` modules already wrap Gemini multimodal calls — find a shared `call_gemini_multimodal` helper or write one if absent.
- New env var `AGENT_GEMINI_API_KEY` (PJ-00 §3 decision 11 / GRILL Q1) — vision pass runs on the **host-side** key, not BYO. Document the env var here.

---

## What This Ticket Must Accomplish

### Goal

Land an async vision pass: a Celery task that probes a `brand_asset` via Gemini multimodal, writes structured `extracted_facts`, and an endpoint to trigger + poll it.

### Deliverables Checklist

#### A. Implementation

- [ ] `app/api/vision.py` — vision probe functions for each asset_type:
  - `probe_logo(file_bytes, mime) -> {dominant_colors: [hex...], background: 'transparent'|'solid'|'photo', detected_fonts: [...]}`
  - `probe_style_guide(file_bytes) -> {palette_hex: [...], font_names: [...], do_dont_rules: {...}, ocr_text_excerpt: str}`
  - `probe_reference(file_bytes, mime) -> {color_tone: str, mood_descriptors: [str...]}`
  - `probe_font(file_bytes, filename) -> {font_family: str}`
- [ ] `app/workers/tasks/brand_asset_vision_task.py` — Celery task `run_vision_pass(asset_id)` that loads the row, dispatches to the right probe, persists `extracted_facts`.
- [ ] `POST /api/brand-assets/{id}/extract` (in `app/api/routes/brand_assets.py`) — enqueues the task, returns `{task_id, status: "queued"}`.
- [ ] `GET /api/brand-assets/{id}/extract/status` — returns `{status: "queued"|"running"|"ready"|"failed", extracted_facts?: {...}, error?: str}`.
- [ ] Use `AGENT_GEMINI_API_KEY` env var (NOT the user's BYO key — vision is host-paid).
- [ ] On Gemini call failure, write `extracted_facts = {"error": "..."}` so the agent sees the failure and can ask the user manually.

#### B. Tests (`tests/test_api/test_vision_pass.py`)

- [ ] TDD first.
- [ ] `test_probe_logo_returns_hex_codes` — stubbed Gemini call → assert structure.
- [ ] `test_probe_style_guide_extracts_facts` — stubbed call → assert OCR + palette.
- [ ] `test_task_persists_extracted_facts` — invoke task synchronously (`.apply()`), assert DB row updated.
- [ ] `test_task_handles_gemini_failure` — stub raise → assert `extracted_facts.error` set.
- [ ] `test_extract_endpoint_enqueues` — POST → 202 + task_id.
- [ ] `test_status_endpoint_returns_ready_when_done` — task ran → status "ready" + facts.

#### C. Integration Expectations

- [ ] Celery worker container picks up the task (`celery -A app.workers.celery_app worker`).
- [ ] No changes to PJ-02 upload endpoint behavior — vision is opt-in via the new `/extract` POST.
- [ ] Frontend (PJ-07) polls `/extract/status` after upload before including `asset_id` in `/converse`.

#### D. Documentation

- [ ] DEVLOG entry: `## 2026-XX-YY — PJ-03: Vision pass module (✅)`.
- [ ] Note the new `AGENT_GEMINI_API_KEY` env var in the entry; PJ-12 will fold this into `ENVIRONMENT.md`.

---

## Branch & Merge Workflow

```bash
git switch final-submission && git pull
git switch -c feature/PJ-03-vision-pass
# implement, run tests
git add app/api/vision.py app/workers/tasks/brand_asset_vision_task.py app/api/routes/brand_assets.py tests/
git commit -m "feat(PJ-03): async vision pass via Celery for brand assets"
git push -u origin feature/PJ-03-vision-pass
```

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `app/api/vision.py` | The four probe functions wrapping Gemini multimodal |
| `app/workers/tasks/brand_asset_vision_task.py` | Celery task that orchestrates the probe |
| `tests/test_api/test_vision_pass.py` | Probe + task + endpoint tests |

### Files to Modify

| File | Action |
|------|--------|
| `app/api/routes/brand_assets.py` | Add `/extract` (POST) and `/extract/status` (GET) endpoints |
| `.env.example` | Add `AGENT_GEMINI_API_KEY=` placeholder |

### Files to NOT Modify

- `app/api/routes/sessions.py` — not in scope for PJ-03.
- `iterate/`, `generate/` — pipeline unaffected.

### Files to READ for Context

| File | Why |
|------|-----|
| `app/workers/tasks/pipeline_task.py` | Celery task pattern, DB session handling, error reporting |
| `generate/` (any multimodal-using module) | Existing Gemini multimodal call wrapper to reuse |
| `docs/development/tickets/PJ-00-phase-plan.md` §9.2 | Probe spec per asset_type |

---

## Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Async vision pass | PJ-00 §3 decision 14 (GRILL Q4) | Celery task, frontend polls; chat path stays sync |
| Host-side key for vision | PJ-00 §3 decision 11 (GRILL Q1) | `AGENT_GEMINI_API_KEY` not BYO — vision is a setup-time cost |
| Structured JSON output | PJ-00 §9.2 | Probe results are structured so the LLM can interpret them in the next `/converse` |
| Failure is non-fatal | PJ-00 §11.2 | Gemini error → `extracted_facts.error` set; LLM falls back to asking the user |

---

## Suggested Implementation Pattern

```python
# app/api/vision.py
import google.generativeai as genai
import os, json

def _client():
    key = os.environ["AGENT_GEMINI_API_KEY"]
    genai.configure(api_key=key)
    return genai.GenerativeModel("gemini-2.5-flash")

LOGO_PROMPT = """Analyze this logo image and return JSON only:
{
  "dominant_colors": ["#hex", "#hex", "#hex"],     // top 3
  "background": "transparent" | "solid" | "photo",
  "detected_fonts": [{"family": "...", "confidence": 0..1}] // empty if pure mark
}
No prose."""

def probe_logo(file_bytes: bytes, mime: str) -> dict:
    model = _client()
    resp = model.generate_content([
        LOGO_PROMPT,
        {"mime_type": mime, "data": file_bytes},
    ])
    return json.loads(resp.text)
```

```python
# app/workers/tasks/brand_asset_vision_task.py
from app.workers.celery_app import celery_app
from app.db import SessionLocal
from app.models.brand_asset import BrandAsset
from app.api.vision import probe_logo, probe_style_guide, probe_reference, probe_font
from pathlib import Path

PROBES = {
    "logo": lambda b, m, f: probe_logo(b, m),
    "style_guide": lambda b, m, f: probe_style_guide(b),
    "reference": lambda b, m, f: probe_reference(b, m),
    "font": lambda b, m, f: probe_font(b, f),
}

@celery_app.task(name="brand_asset.vision_pass")
def run_vision_pass(asset_id: str):
    with SessionLocal() as db:
        row = db.query(BrandAsset).get(asset_id)
        if not row:
            return {"error": "asset not found"}
        path = Path("output") / row.storage_path
        try:
            facts = PROBES[row.asset_type](path.read_bytes(), row.mime_type, row.original_filename)
        except Exception as e:
            facts = {"error": str(e)}
        row.extracted_facts = facts
        db.commit()
        return facts
```

```python
# app/api/routes/brand_assets.py — add to the existing router

@router.post("/{asset_id}/extract", status_code=202)
def trigger_extract(asset_id: str, user_id: str = Depends(get_current_user_id), db = Depends(get_session)):
    row = db.query(BrandAsset).filter_by(id=asset_id, user_id=user_id).one_or_none()
    if not row:
        raise HTTPException(404)
    task = run_vision_pass.delay(asset_id)
    return {"task_id": task.id, "status": "queued"}

@router.get("/{asset_id}/extract/status")
def extract_status(asset_id: str, user_id: str = Depends(get_current_user_id), db = Depends(get_session)):
    row = db.query(BrandAsset).filter_by(id=asset_id, user_id=user_id).one_or_none()
    if not row:
        raise HTTPException(404)
    if row.extracted_facts is None:
        return {"status": "running"}
    if "error" in row.extracted_facts:
        return {"status": "failed", "error": row.extracted_facts["error"]}
    return {"status": "ready", "extracted_facts": row.extracted_facts}
```

---

## Edge Cases to Handle

1. Gemini returns non-JSON despite the prompt — wrap `json.loads` with a fallback that stores raw text under `extracted_facts.raw`.
2. PDF over a few pages — clamp to first 3 pages for OCR to stay inside the 25s budget.
3. SVG logos — Gemini multimodal accepts inline data; pass as `image/svg+xml` and hope (or rasterize via a helper). Document fallback if SVG support is flaky.
4. Re-extraction — calling `/extract` on an already-extracted asset re-runs and overwrites. The agent can use this for "user says the palette is wrong, re-probe with a different prompt."
5. Concurrent tasks for the same asset — Celery may dedupe by task name+arg if configured; otherwise tolerate the last-write-wins.
6. Missing `AGENT_GEMINI_API_KEY` → fail fast on first import with a clear error so misconfigured deploys don't run silently.

---

## Definition of Done

- [ ] All six tests pass.
- [ ] Celery worker logs show task pickup + completion on a manual upload+extract flow.
- [ ] `extracted_facts` JSONB populated for a real logo upload (manual smoke).
- [ ] `ruff check .` clean.
- [ ] DEVLOG entry mentions the new `AGENT_GEMINI_API_KEY` env var.
- [ ] Feature branch pushed.

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Probe prompt writing + Gemini smoke | 90 min |
| Probe functions + tests | 120 min |
| Celery task + endpoints | 90 min |
| End-to-end manual smoke | 60 min |
| DEVLOG + commit | 15 min |
| **Total** | **~1.5 days** |

---

## After This Ticket: What Comes Next

- **PJ-05** — `ingest_asset` tool reads `extracted_facts` to confirm with user
- **PJ-07** — Chat UI polls `/extract/status` then includes `asset_id` in `/converse`
