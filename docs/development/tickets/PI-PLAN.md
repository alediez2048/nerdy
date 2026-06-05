# PI Implementation Plan — Unified Media Quality Evaluator

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace six legacy evaluator modules (image_evaluator, coherence_checker, image_scorer, video_evaluator, video_attributes, video_scorer) with a single source-of-truth `media_quality.py` that scores both image and video on 8/10 weighted dimensions plus 3/5 penalty gates, producing rationale-bearing v2 ledger events that drive both selection and UI display.

**Architecture:** One Gemini 2.5 Flash multimodal call per variant returns all dimension scores + gate evaluations + rationales in a single structured JSON response. Composite math: `raw_score × penalty_mult × 100`. Selection picks max-composite; SelectionResult carries `winner_reason` (top 2 distinguishing dimensions) and per-loser `rejection_reason` (worst dimension delta + rationale). Old ledger events stay readable for backward compat; new writes emit `MediaEvaluation` v2 only.

**Tech Stack:** Python 3.14 (pytest, dataclasses, SQLAlchemy), Google Generative AI SDK (`google.genai`, Gemini 2.5 Flash), React 19 + TypeScript (Vite), FastAPI.

**Source spec:** `docs/development/tickets/PI-00-phase-plan.md`

**Granularity target:** ≥ 8 distinct composite values across a 15-variant batch (today: 3). Enforced by the calibration test in Ticket PI-09. The phase is not done until that test passes against a real `GEMINI_API_KEY`.

---

## File structure (locked at plan time)

### New files
```
evaluate/media_quality.py                                  # PI-02, extended in PI-05
evaluate/media_selector.py                                 # PI-03
tests/test_evaluation/test_media_quality.py                # PI-02 + PI-05
tests/test_evaluation/test_media_selector.py               # PI-03
tests/test_evaluation/test_media_quality_calibration.py    # PI-09
tests/test_evaluation/fixtures/media_quality/             # PI-09 (golden set)
  images/                                                  # 12 reference images
  videos/                                                  # 8 reference videos
  annotations.yaml                                         # tier labels
```

### Modified files
```
iterate/ledger_events.py                  # PI-01: add MediaEvaluation, MediaEvaluationFailed
iterate/batch_processor.py                # PI-04: image path uses new evaluator
generate_video/orchestrator.py            # PI-06: video path uses new evaluator
generate_video/selector.py                # PI-06: use media_selector
generate_video/regen.py                   # PI-06: video coherence reference removal
app/api/routes/dashboard.py               # PI-07: /variants endpoint v2 branch
app/frontend/src/api/dashboard.ts         # PI-08: v2 type definitions
app/frontend/src/components/VariantsPanel.tsx  # PI-08: Evidence panel + legacy badge
```

### Deleted at end of phase (PI-10)
```
evaluate/image_evaluator.py
evaluate/coherence_checker.py
evaluate/image_scorer.py
evaluate/video_evaluator.py
evaluate/video_attributes.py
evaluate/video_coherence.py
evaluate/video_scorer.py
tests/test_pipeline/test_image_evaluator.py
tests/test_pipeline/test_coherence_checker.py
tests/test_pipeline/test_image_scorer.py
tests/test_pipeline/test_video_*.py  (six files)
```

### File ownership
- `media_quality.py` — single responsibility: take (media_path, ad_copy, brief, media_type) → produce `MediaEvaluation` or `MediaEvaluationFailed`. Pure transformation; no DB, no orchestration, no file management.
- `media_selector.py` — single responsibility: take `list[MediaEvaluation]` → produce `SelectionResult`. No I/O.
- `batch_processor.py` / `generate_video/orchestrator.py` — orchestration only. They call the new modules and write events. No scoring logic.

---

## Ticket roster

| Ticket | Title | Deps | Est. |
|---|---|---|---|
| PI-01 | Ledger event classes (`MediaEvaluation`, `MediaEvaluationFailed`) | — | 2h |
| PI-02 | `media_quality.py` — image path + tests | PI-01 | 6h |
| PI-03 | `media_selector.py` — winner_reason + rejection_reason + tests | PI-01 | 3h |
| PI-04 | Wire image batch_processor to new evaluator | PI-02, PI-03 | 3h |
| PI-05 | `media_quality.py` — video path + tests | PI-02 | 4h |
| PI-06 | Wire video pipeline + fix missing-file root cause | PI-05, PI-03 | 7h |
| PI-07 | Dashboard `/variants` endpoint v2 branch | PI-04, PI-06 | 3h |
| PI-08 | `VariantsPanel` UI — Evidence panel + legacy badge | PI-07 | 5h |
| PI-09 | Calibration golden set + spread test | PI-05 | 5h |
| PI-10 | Retire 6 legacy modules + their tests | PI-04, PI-06 | 3h |
| PI-11 | Verification gate (end-to-end run + granularity check) | PI-01..PI-10 | 4h |

Total: ~45 hours, matches PI-00 estimate.

---

# Ticket PI-01: Ledger event classes

**Goal:** Add `MediaEvaluation` and `MediaEvaluationFailed` event classes to `iterate/ledger_events.py` so subsequent tickets have a target type to write to.

**Files:**
- Modify: `iterate/ledger_events.py`
- Test: `tests/test_pipeline/test_ledger_seam.py` (extend existing)

- [ ] **Step 1: Write the failing test** — append to `tests/test_pipeline/test_ledger_seam.py`:

```python
def test_media_evaluation_event_roundtrip():
    from iterate.ledger_events import MediaEvaluation, parse_event
    ev = MediaEvaluation(
        ad_id="ad_x",
        brief_id="brief_001",
        cycle_number=0,
        action="media_eval_anchor",
        tokens_consumed=1820,
        model_used="gemini-2.5-flash",
        seed="0",
        inputs={"variant_type": "anchor", "media_type": "image"},
        outputs={
            "schema_version": "v2",
            "media_type": "image",
            "media_path": "out/foo.png",
            "dimensions": {
                "thumb_stop_potential": {"score": 7, "weight": 0.20, "rationale": "x"},
            },
            "penalty_gates": {
                "has_ai_artifacts": {"triggered": False, "rationale": "clean"},
            },
            "raw_score": 0.58,
            "penalty_multiplier": 1.0,
            "composite_score": 58.0,
        },
    )
    line = ev.to_jsonl()
    parsed = parse_event(line)
    assert isinstance(parsed, MediaEvaluation)
    assert parsed.outputs["composite_score"] == 58.0
    assert parsed.outputs["schema_version"] == "v2"


def test_media_evaluation_failed_event():
    from iterate.ledger_events import MediaEvaluationFailed, parse_event
    ev = MediaEvaluationFailed(
        ad_id="ad_x",
        brief_id="brief_001",
        cycle_number=0,
        action="media_eval_failed_anchor",
        tokens_consumed=0,
        model_used="gemini-2.5-flash",
        seed="0",
        inputs={"variant_type": "anchor", "media_type": "video"},
        outputs={
            "schema_version": "v2",
            "media_type": "video",
            "failure_reason": "file_not_found",
            "error_message": "videofile.mp4 missing",
        },
    )
    line = ev.to_jsonl()
    parsed = parse_event(line)
    assert isinstance(parsed, MediaEvaluationFailed)
    assert parsed.outputs["failure_reason"] == "file_not_found"
```

- [ ] **Step 2: Run tests to verify they fail**

```
.venv/bin/python -m pytest tests/test_pipeline/test_ledger_seam.py::test_media_evaluation_event_roundtrip tests/test_pipeline/test_ledger_seam.py::test_media_evaluation_failed_event -v
```

Expected: FAIL with `ImportError: cannot import name 'MediaEvaluation'`.

- [ ] **Step 3: Add the event classes to `iterate/ledger_events.py`** — append before the `EVENT_TYPES` registry (look for `EVENT_TYPES = (` at the bottom):

```python
class MediaEvaluation(LedgerEvent):
    """Unified per-variant media quality evaluation (PI-02). Schema v2.

    Replaces ImageEvaluated, ImageScored, VideoEvaluated, VideoCoherenceChecked,
    VideoScored. The outputs dict carries the full rubric: per-dimension
    {score, weight, rationale}, per-gate {triggered, rationale},
    raw_score / penalty_multiplier / composite_score, and schema_version.
    """
    event_type: str = "MediaEvaluation"


class MediaEvaluationFailed(LedgerEvent):
    """Explicit failure event for a single variant (PI-02).

    Emitted when the evaluator cannot produce a MediaEvaluation — e.g.
    file missing, upload too large, LLM JSON unparseable. Selection skips
    failed variants; if all variants for an ad fail, the ad is
    regenerated via the existing P1-08 brief-mutation flow.
    """
    event_type: str = "MediaEvaluationFailed"
```

- [ ] **Step 4: Register them in the `EVENT_TYPES` tuple** — find the existing tuple (currently includes `ImageEvaluated, ImageScored, VideoEvaluated, ...`) and add the two new classes:

```python
EVENT_TYPES = (
    # ... existing entries ...
    ImageEvaluated,
    ImageScored,
    VideoEvaluated,
    VideoCoherenceChecked,
    VideoScored,
    MediaEvaluation,         # PI-01
    MediaEvaluationFailed,   # PI-01
)
```

- [ ] **Step 5: Run tests to verify they pass**

```
.venv/bin/python -m pytest tests/test_pipeline/test_ledger_seam.py -v
```

Expected: all green (previous tests + 2 new ones).

- [ ] **Step 6: Commit**

```
git add iterate/ledger_events.py tests/test_pipeline/test_ledger_seam.py
git commit -m "feat(PI-01): MediaEvaluation + MediaEvaluationFailed ledger events"
```

---

# Ticket PI-02: `media_quality.py` — image path

**Goal:** Build the unified evaluator module, image-only path. Single Gemini 2.5 Flash call returns 8 dimension scores + 3 gate evaluations + rationales. Image-only here; video path comes in PI-05.

**Files:**
- Create: `evaluate/media_quality.py`
- Create: `tests/test_evaluation/test_media_quality.py`

- [ ] **Step 1: Write failing test for dimension/weight schema** — create `tests/test_evaluation/test_media_quality.py`:

```python
"""Tests for unified media quality evaluator (PI-02)."""
from __future__ import annotations

from unittest.mock import patch
import pytest

from evaluate.media_quality import (
    IMAGE_DIMENSIONS,
    IMAGE_GATES,
    DimensionScore,
    GateEvaluation,
    MediaEvaluationResult,
    compute_composite,
    evaluate_media,
)


def test_image_dimensions_and_weights():
    """8 dimensions for image, weights sum to 1.0."""
    assert len(IMAGE_DIMENSIONS) == 8
    total = sum(d["weight"] for d in IMAGE_DIMENSIONS)
    assert abs(total - 1.0) < 1e-9, f"weights sum to {total}, not 1.0"
    names = {d["name"] for d in IMAGE_DIMENSIONS}
    assert names == {
        "thumb_stop_potential", "mobile_legibility", "single_focal_point",
        "brand_consistency", "emotional_impact", "message_alignment",
        "audience_match", "production_quality",
    }


def test_image_gates_have_caps():
    """3 image gates with cap multipliers <1.0."""
    assert len(IMAGE_GATES) == 3
    names = {g["name"] for g in IMAGE_GATES}
    assert names == {"has_ai_artifacts", "has_uncanny_faces", "brand_safety_violation"}
    for g in IMAGE_GATES:
        assert 0.0 < g["cap"] < 1.0
```

- [ ] **Step 2: Run test to verify it fails**

```
.venv/bin/python -m pytest tests/test_evaluation/test_media_quality.py::test_image_dimensions_and_weights -v
```

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Create `evaluate/media_quality.py` with the constants and dataclasses**

```python
"""Unified media quality evaluator (PI-02 / PI-05).

Single source of truth for image and video variant scoring. One Gemini
2.5 Flash multimodal call per variant returns all dimension scores,
gate evaluations, and rationales in a single structured JSON response.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from iterate.retry import retry_with_backoff

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash"

# ---- Image rubric (PI-02) ----
IMAGE_DIMENSIONS: tuple[dict[str, Any], ...] = (
    {"name": "thumb_stop_potential", "weight": 0.20,
     "criterion": "Does it stop the scroll in the first 0.3s? Strong visual hook."},
    {"name": "mobile_legibility", "weight": 0.15,
     "criterion": "Key elements readable at 320px width (mobile feed size)."},
    {"name": "single_focal_point", "weight": 0.10,
     "criterion": "Clear hierarchy — no competing subjects."},
    {"name": "brand_consistency", "weight": 0.10,
     "criterion": "Varsity Tutors visual identity — teal/navy/white palette."},
    {"name": "emotional_impact", "weight": 0.15,
     "criterion": "Evokes a specific emotion (aspiration, determination, warmth)."},
    {"name": "message_alignment", "weight": 0.10,
     "criterion": "Visual reinforces the ad's headline and copy."},
    {"name": "audience_match", "weight": 0.10,
     "criterion": "Fits the target audience (parent of HS student vs student)."},
    {"name": "production_quality", "weight": 0.10,
     "criterion": "Composition, color balance, no obvious AI tells."},
)

IMAGE_GATES: tuple[dict[str, Any], ...] = (
    {"name": "has_ai_artifacts", "cap": 0.5,
     "criterion": "Warped hands, mangled text, impossible geometry."},
    {"name": "has_uncanny_faces", "cap": 0.6,
     "criterion": "Asymmetric features, melted skin, lifeless eyes."},
    {"name": "brand_safety_violation", "cap": 0.3,
     "criterion": "Competitor logos, inappropriate context, unsafe imagery."},
)


@dataclass
class DimensionScore:
    score: int          # 1–10
    weight: float       # taken from the rubric, not the LLM
    rationale: str


@dataclass
class GateEvaluation:
    triggered: bool
    rationale: str


@dataclass
class MediaEvaluationResult:
    ad_id: str
    variant_type: str
    media_type: Literal["image", "video"]
    media_path: str
    model_used: str
    tokens_consumed: int
    dimensions: dict[str, DimensionScore]
    penalty_gates: dict[str, GateEvaluation]
    raw_score: float
    penalty_multiplier: float
    composite_score: float
    schema_version: str = "v2"
    failed: bool = False
    failure_reason: str | None = None
    error_message: str | None = None


def compute_composite(
    dimensions: dict[str, DimensionScore],
    penalty_gates: dict[str, GateEvaluation],
    gate_rubric: tuple[dict[str, Any], ...],
) -> tuple[float, float, float]:
    """Return (raw_score 0..1, penalty_mult, composite 0..100).

    Multiple triggered gates take the most-severe (lowest) cap.
    """
    raw = sum(d.score * d.weight for d in dimensions.values()) / 10.0
    triggered_caps = [
        g["cap"] for g in gate_rubric
        if penalty_gates.get(g["name"], GateEvaluation(False, "")).triggered
    ]
    penalty_mult = min(triggered_caps) if triggered_caps else 1.0
    composite = round(raw * penalty_mult * 100.0, 2)
    return round(raw, 4), penalty_mult, composite
```

- [ ] **Step 4: Add tests for `compute_composite` math**

```python
def test_compute_composite_no_gates_triggered():
    """raw * 1.0 * 100 when no penalty applies."""
    dims = {
        d["name"]: DimensionScore(score=7, weight=d["weight"], rationale="")
        for d in IMAGE_DIMENSIONS
    }
    gates = {g["name"]: GateEvaluation(triggered=False, rationale="") for g in IMAGE_GATES}
    raw, mult, composite = compute_composite(dims, gates, IMAGE_GATES)
    assert mult == 1.0
    assert raw == pytest.approx(0.7, abs=1e-4)
    assert composite == pytest.approx(70.0, abs=0.01)


def test_compute_composite_single_gate_triggered():
    """has_uncanny_faces caps at 0.6."""
    dims = {
        d["name"]: DimensionScore(score=8, weight=d["weight"], rationale="")
        for d in IMAGE_DIMENSIONS
    }
    gates = {g["name"]: GateEvaluation(triggered=False, rationale="") for g in IMAGE_GATES}
    gates["has_uncanny_faces"] = GateEvaluation(triggered=True, rationale="bad eyes")
    raw, mult, composite = compute_composite(dims, gates, IMAGE_GATES)
    assert mult == 0.6
    assert composite == pytest.approx(48.0, abs=0.01)  # 0.8 * 0.6 * 100


def test_compute_composite_multiple_gates_use_lowest_cap():
    """has_ai_artifacts (0.5) wins over has_uncanny_faces (0.6) when both fire."""
    dims = {
        d["name"]: DimensionScore(score=8, weight=d["weight"], rationale="")
        for d in IMAGE_DIMENSIONS
    }
    gates = {g["name"]: GateEvaluation(triggered=False, rationale="") for g in IMAGE_GATES}
    gates["has_uncanny_faces"] = GateEvaluation(triggered=True, rationale="")
    gates["has_ai_artifacts"] = GateEvaluation(triggered=True, rationale="")
    raw, mult, composite = compute_composite(dims, gates, IMAGE_GATES)
    assert mult == 0.5  # most severe cap
    assert composite == pytest.approx(40.0, abs=0.01)
```

- [ ] **Step 5: Run those tests, verify pass**

```
.venv/bin/python -m pytest tests/test_evaluation/test_media_quality.py -v
```

Expected: 4/4 pass (the schema test + 3 math tests).

- [ ] **Step 6: Add the prompt builder + parser + `evaluate_media`**

Append to `evaluate/media_quality.py`:

```python
def _build_image_prompt(ad_copy: dict[str, Any], session_config: dict[str, Any] | None) -> str:
    headline = ad_copy.get("headline", "")
    primary_text = ad_copy.get("primary_text", "") or ad_copy.get("body", "")
    cta = ad_copy.get("cta_button", "") or ad_copy.get("cta", "")
    audience = (session_config or {}).get("audience", "")
    persona = (session_config or {}).get("persona", "")

    dims_block = "\n".join(
        f"{i+1}. {d['name']} (weight {d['weight']:.2f}) — {d['criterion']}"
        for i, d in enumerate(IMAGE_DIMENSIONS)
    )
    gates_block = "\n".join(
        f"- {g['name']} (cap {g['cap']:.1f}) — {g['criterion']}"
        for g in IMAGE_GATES
    )
    return f"""You are a strict visual ad quality evaluator for Varsity Tutors SAT test prep on Facebook and Instagram.

CALIBRATION: You are scoring AI-GENERATED images, not human photography. Be critical. Scores cluster too high if you are not specific. Most AI images are mediocre. A score of 7 is genuinely good. 9–10 is exceptional and rare. Average score in a batch should be near 5–6. If you find yourself scoring everything above 7, you are being too lenient.

AD COPY (for message-alignment evaluation):
- Headline: {headline or "(none)"}
- Primary Text: {primary_text or "(none)"}
- CTA: {cta or "(none)"}
- Target audience: {audience or "(none)"}
- Persona: {persona or "(none)"}

DIMENSIONS — score 1–10 with a 1–2 sentence rationale. The rationale MUST name a specific visual element that earned that score (e.g. "the green CTA pill in the bottom-third"). Generic statements like "good composition" will be rejected.

{dims_block}

PENALTY GATES — answer true / false with a 1-sentence rationale. Trigger only when the issue is clearly visible.

{gates_block}

Return ONLY a JSON object with this exact shape:
{{
  "dimensions": {{
    "thumb_stop_potential": {{"score": 7, "rationale": "..."}},
    ...
  }},
  "penalty_gates": {{
    "has_ai_artifacts": {{"triggered": false, "rationale": "..."}},
    ...
  }}
}}"""


def _parse_response(text: str) -> dict[str, Any]:
    stripped = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped)
    if m:
        stripped = m.group(1).strip()
    return json.loads(stripped)


def evaluate_media(
    media_path: str,
    ad_copy: dict[str, Any],
    ad_id: str,
    variant_type: str,
    media_type: Literal["image", "video"] = "image",
    session_config: dict[str, Any] | None = None,
    model: str = DEFAULT_MODEL,
) -> MediaEvaluationResult:
    """Run the unified evaluator on one variant. Image path only (PI-02)."""
    if not Path(media_path).exists():
        return _failure_result(
            ad_id, variant_type, media_type, media_path,
            "file_not_found", f"{media_path} does not exist",
        )

    if media_type != "image":
        # video path lands in PI-05
        raise NotImplementedError(f"media_type={media_type} not yet supported")

    rubric_dims = IMAGE_DIMENSIONS
    rubric_gates = IMAGE_GATES
    prompt = _build_image_prompt(ad_copy, session_config)

    try:
        raw_payload, tokens = retry_with_backoff(
            lambda: _call_multimodal(media_path, prompt, model, media_type)
        )
        parsed = _parse_response(raw_payload)
    except (json.JSONDecodeError, ValueError) as e:
        return _failure_result(
            ad_id, variant_type, media_type, media_path,
            "json_parse_failed", str(e),
        )
    except Exception as e:
        return _failure_result(
            ad_id, variant_type, media_type, media_path,
            "llm_call_failed", str(e), tokens=0,
        )

    dimensions: dict[str, DimensionScore] = {}
    for d in rubric_dims:
        raw_d = parsed.get("dimensions", {}).get(d["name"], {})
        score = int(raw_d.get("score", 5))
        score = max(1, min(10, score))
        dimensions[d["name"]] = DimensionScore(
            score=score, weight=d["weight"],
            rationale=str(raw_d.get("rationale", "")).strip(),
        )

    gates: dict[str, GateEvaluation] = {}
    for g in rubric_gates:
        raw_g = parsed.get("penalty_gates", {}).get(g["name"], {})
        gates[g["name"]] = GateEvaluation(
            triggered=bool(raw_g.get("triggered", False)),
            rationale=str(raw_g.get("rationale", "")).strip(),
        )

    raw_score, penalty_mult, composite = compute_composite(dimensions, gates, rubric_gates)
    return MediaEvaluationResult(
        ad_id=ad_id, variant_type=variant_type, media_type=media_type,
        media_path=media_path, model_used=model, tokens_consumed=tokens,
        dimensions=dimensions, penalty_gates=gates,
        raw_score=raw_score, penalty_multiplier=penalty_mult,
        composite_score=composite,
    )


def _call_multimodal(
    media_path: str, prompt: str, model: str, media_type: str
) -> tuple[str, int]:
    """Call Gemini 2.5 Flash multimodal. Returns (text, total_tokens)."""
    from google.genai import types
    from generate.gemini_client import call_gemini_multimodal

    with open(media_path, "rb") as f:
        data = f.read()
    mime = "image/png" if media_type == "image" else "video/mp4"
    resp = call_gemini_multimodal(
        [types.Part.from_bytes(data=data, mime_type=mime), prompt],
        model=model,
        temperature=0.1,
        max_output_tokens=2048,
    )
    return resp.text, resp.total_tokens


def _failure_result(
    ad_id: str, variant_type: str, media_type: str, media_path: str,
    failure_reason: str, error_message: str, tokens: int = 0,
) -> MediaEvaluationResult:
    return MediaEvaluationResult(
        ad_id=ad_id, variant_type=variant_type, media_type=media_type,
        media_path=media_path, model_used=DEFAULT_MODEL, tokens_consumed=tokens,
        dimensions={}, penalty_gates={}, raw_score=0.0,
        penalty_multiplier=0.0, composite_score=0.0,
        failed=True, failure_reason=failure_reason, error_message=error_message,
    )
```

- [ ] **Step 7: Add tests for evaluate_media (mocked LLM call)**

```python
def _make_payload(score: int = 7) -> dict[str, Any]:
    return {
        "dimensions": {
            d["name"]: {"score": score, "rationale": f"specific reason for {d['name']}"}
            for d in IMAGE_DIMENSIONS
        },
        "penalty_gates": {
            g["name"]: {"triggered": False, "rationale": "clean"}
            for g in IMAGE_GATES
        },
    }


def test_evaluate_media_image_happy_path(tmp_path):
    """Mocked LLM returns valid JSON → MediaEvaluationResult populated end to end."""
    media_path = tmp_path / "ad.png"
    media_path.write_bytes(b"fake-png")
    payload = json.dumps(_make_payload(score=7))

    with patch("evaluate.media_quality._call_multimodal", return_value=(payload, 1500)):
        result = evaluate_media(
            media_path=str(media_path),
            ad_copy={"headline": "Ace the SAT", "body": "1-on-1 tutoring", "cta": "Start"},
            ad_id="ad_001",
            variant_type="anchor",
            media_type="image",
        )

    assert not result.failed
    assert result.media_type == "image"
    assert result.tokens_consumed == 1500
    assert len(result.dimensions) == 8
    assert all(1 <= ds.score <= 10 for ds in result.dimensions.values())
    assert len(result.penalty_gates) == 3
    assert result.composite_score == pytest.approx(70.0, abs=0.01)
    # Rationales preserved
    assert "specific reason" in result.dimensions["thumb_stop_potential"].rationale


def test_evaluate_media_file_not_found_returns_failure():
    result = evaluate_media(
        media_path="/does/not/exist.png",
        ad_copy={}, ad_id="ad_001", variant_type="anchor", media_type="image",
    )
    assert result.failed
    assert result.failure_reason == "file_not_found"


def test_evaluate_media_json_parse_failure_returns_failure(tmp_path):
    media_path = tmp_path / "ad.png"
    media_path.write_bytes(b"x")
    with patch("evaluate.media_quality._call_multimodal", return_value=("not json", 100)):
        result = evaluate_media(
            media_path=str(media_path),
            ad_copy={}, ad_id="ad_001", variant_type="anchor", media_type="image",
        )
    assert result.failed
    assert result.failure_reason == "json_parse_failed"


def test_evaluate_media_score_clamped_to_1_10(tmp_path):
    media_path = tmp_path / "ad.png"
    media_path.write_bytes(b"x")
    bad_payload = _make_payload(score=15)  # out of range
    with patch("evaluate.media_quality._call_multimodal", return_value=(json.dumps(bad_payload), 100)):
        result = evaluate_media(
            media_path=str(media_path),
            ad_copy={}, ad_id="ad_001", variant_type="anchor", media_type="image",
        )
    assert not result.failed
    assert all(ds.score == 10 for ds in result.dimensions.values())  # clamped
```

- [ ] **Step 8: Run all tests in the new file, verify all pass**

```
.venv/bin/python -m pytest tests/test_evaluation/test_media_quality.py -v
```

Expected: 8/8 PASS.

- [ ] **Step 9: Commit**

```
git add evaluate/media_quality.py tests/test_evaluation/test_media_quality.py
git commit -m "feat(PI-02): media_quality evaluator — image path with rubric + gates"
```

---

# Ticket PI-03: `media_selector.py` — winner_reason + rejection_reason

**Goal:** Build the selection module that consumes `list[MediaEvaluationResult]` and produces `SelectionResult` with winner + per-loser rejection reasoning.

**Files:**
- Create: `evaluate/media_selector.py`
- Create: `tests/test_evaluation/test_media_selector.py`

- [ ] **Step 1: Write the failing test** — create `tests/test_evaluation/test_media_selector.py`:

```python
"""Tests for unified media selection (PI-03)."""
from __future__ import annotations

import pytest

from evaluate.media_quality import (
    DimensionScore, GateEvaluation, MediaEvaluationResult, IMAGE_DIMENSIONS,
)
from evaluate.media_selector import select_best, SelectionResult


def _eval(ad_id: str, variant: str, composite: float, dim_overrides: dict | None = None) -> MediaEvaluationResult:
    dim_overrides = dim_overrides or {}
    dims = {
        d["name"]: DimensionScore(
            score=int(dim_overrides.get(d["name"], 7)),
            weight=d["weight"], rationale=f"{d['name']} rationale",
        )
        for d in IMAGE_DIMENSIONS
    }
    return MediaEvaluationResult(
        ad_id=ad_id, variant_type=variant, media_type="image",
        media_path=f"/tmp/{variant}.png", model_used="gemini-2.5-flash",
        tokens_consumed=1500, dimensions=dims, penalty_gates={},
        raw_score=composite / 100.0, penalty_multiplier=1.0,
        composite_score=composite,
    )


def test_select_best_picks_highest_composite():
    evs = [_eval("a1", "anchor", 60.0), _eval("a1", "tone_shift", 80.0), _eval("a1", "comp", 55.0)]
    result = select_best(evs)
    assert isinstance(result, SelectionResult)
    assert result.winner.variant_type == "tone_shift"
    assert not result.all_failed


def test_select_best_winner_reason_names_top_two_distinguishing_dims():
    """Winner's top 2 dimensions vs. mean of losers."""
    losers_dims = {"thumb_stop_potential": 4, "emotional_impact": 5}
    winner_dims = {"thumb_stop_potential": 9, "emotional_impact": 9}
    evs = [
        _eval("a1", "anchor", 50.0, losers_dims),
        _eval("a1", "tone_shift", 90.0, winner_dims),
        _eval("a1", "comp", 50.0, losers_dims),
    ]
    result = select_best(evs)
    dims_named = {d["dimension"] for d in result.winner_reason.distinguishing_dimensions}
    assert "thumb_stop_potential" in dims_named
    assert "emotional_impact" in dims_named


def test_select_best_rejection_reasons_per_loser():
    evs = [_eval("a1", "anchor", 80.0), _eval("a1", "tone_shift", 50.0, {"mobile_legibility": 3})]
    result = select_best(evs)
    assert result.winner.variant_type == "anchor"
    rr = result.rejection_reasons["tone_shift"]
    assert rr.worst_dimension == "mobile_legibility"
    assert rr.composite_delta == pytest.approx(-30.0, abs=0.01)


def test_select_best_all_failed():
    evs = [
        MediaEvaluationResult(
            ad_id="a1", variant_type=v, media_type="image", media_path="x",
            model_used="g", tokens_consumed=0, dimensions={}, penalty_gates={},
            raw_score=0.0, penalty_multiplier=0.0, composite_score=0.0,
            failed=True, failure_reason="file_not_found",
        )
        for v in ("anchor", "tone_shift", "comp")
    ]
    result = select_best(evs)
    assert result.all_failed is True
    assert result.winner is None


def test_select_best_single_variant_uses_absolute_top_dims():
    """When only one valid variant exists, distinguishing dims come from its top-2 absolute scores."""
    high = {"thumb_stop_potential": 10, "emotional_impact": 9}
    evs = [_eval("a1", "anchor", 90.0, high)]
    result = select_best(evs)
    assert result.winner.variant_type == "anchor"
    dims_named = {d["dimension"] for d in result.winner_reason.distinguishing_dimensions}
    assert dims_named == {"thumb_stop_potential", "emotional_impact"}
```

- [ ] **Step 2: Run, expect ImportError fail**

```
.venv/bin/python -m pytest tests/test_evaluation/test_media_selector.py -v
```

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Create `evaluate/media_selector.py`**

```python
"""Unified media variant selection (PI-03).

Picks the highest-composite variant and produces a SelectionResult
with winner_reason (top-2 distinguishing dimensions vs. mean of losers)
and per-loser rejection_reason (worst dimension delta + rationale).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from statistics import mean
from typing import Any

from evaluate.media_quality import MediaEvaluationResult

logger = logging.getLogger(__name__)


@dataclass
class WinnerReason:
    composite_score: float
    distinguishing_dimensions: list[dict[str, Any]]


@dataclass
class RejectionReason:
    composite_delta: float
    worst_dimension: str
    worst_dimension_delta: float
    worst_dimension_rationale: str


@dataclass
class SelectionResult:
    winner: MediaEvaluationResult | None
    losers: list[MediaEvaluationResult]
    winner_reason: WinnerReason | None = None
    rejection_reasons: dict[str, RejectionReason] = field(default_factory=dict)
    all_failed: bool = False


def select_best(evaluations: list[MediaEvaluationResult]) -> SelectionResult:
    valid = [e for e in evaluations if not e.failed]
    if not valid:
        return SelectionResult(winner=None, losers=[], all_failed=True)

    winner = max(valid, key=lambda e: e.composite_score)
    losers = [e for e in valid if e is not winner]

    # winner_reason: top 2 distinguishing dimensions. If only 1 variant, use winner's own top-2.
    if losers:
        delta_by_dim = {
            dim: winner.dimensions[dim].score
                 - mean(loser.dimensions[dim].score for loser in losers)
            for dim in winner.dimensions
        }
        top_dims = sorted(delta_by_dim, key=delta_by_dim.get, reverse=True)[:2]
        distinguishing = [
            {"dimension": d, "delta_vs_mean": round(delta_by_dim[d], 2)}
            for d in top_dims
        ]
    else:
        top_dims = sorted(
            winner.dimensions, key=lambda d: winner.dimensions[d].score, reverse=True
        )[:2]
        distinguishing = [
            {"dimension": d, "absolute_score": winner.dimensions[d].score,
             "note": "only valid variant"}
            for d in top_dims
        ]

    winner_reason = WinnerReason(
        composite_score=winner.composite_score,
        distinguishing_dimensions=distinguishing,
    )

    rejection_reasons: dict[str, RejectionReason] = {}
    for loser in losers:
        deltas = {
            dim: loser.dimensions[dim].score - winner.dimensions[dim].score
            for dim in loser.dimensions
        }
        worst_dim = min(deltas, key=deltas.get)
        rejection_reasons[loser.variant_type] = RejectionReason(
            composite_delta=round(loser.composite_score - winner.composite_score, 2),
            worst_dimension=worst_dim,
            worst_dimension_delta=round(deltas[worst_dim], 2),
            worst_dimension_rationale=loser.dimensions[worst_dim].rationale,
        )

    logger.info(
        "Selected %s (composite=%.2f) for ad %s from %d candidates",
        winner.variant_type, winner.composite_score, winner.ad_id, len(valid),
    )
    return SelectionResult(
        winner=winner, losers=losers,
        winner_reason=winner_reason, rejection_reasons=rejection_reasons,
    )
```

- [ ] **Step 4: Run, expect all tests pass**

```
.venv/bin/python -m pytest tests/test_evaluation/test_media_selector.py -v
```

Expected: 5/5 PASS.

- [ ] **Step 5: Commit**

```
git add evaluate/media_selector.py tests/test_evaluation/test_media_selector.py
git commit -m "feat(PI-03): media_selector — SelectionResult with winner/rejection reasons"
```

---

# Ticket PI-04: Wire image batch_processor to new evaluator

**Goal:** Replace the broken image evaluation block in `_generate_and_select_image` with the new `evaluate_media` + `select_best` path. Write `MediaEvaluation` events; stop writing `ImageEvaluated` / `ImageScored`.

**Files:**
- Modify: `iterate/batch_processor.py` — `_generate_and_select_image` function (lines ~301-453) and the `score_image` post-hoc block (lines ~240-266)
- Test: `tests/test_pipeline/test_batch_processor_pi04.py` (new)

- [ ] **Step 1: Write the failing test** — create `tests/test_pipeline/test_batch_processor_pi04.py`:

```python
"""PI-04: image batch processing emits MediaEvaluation events."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import json
from pathlib import Path

import pytest


def test_generate_and_select_image_writes_media_evaluation_events(tmp_path):
    """One MediaEvaluation per variant; one MediaSelected aggregate."""
    from iterate.batch_processor import _generate_and_select_image
    from evaluate.media_quality import (
        DimensionScore, GateEvaluation, MediaEvaluationResult, IMAGE_DIMENSIONS,
    )

    ledger = tmp_path / "ledger.jsonl"
    fake_ad = MagicMock(ad_id="ad_X", headline="h", primary_text="b", cta_button="c")
    fake_brief = {"brief_id": "brief_001"}

    def _fake_eval(media_path, ad_copy, ad_id, variant_type, media_type="image", **kw):
        score = {"anchor": 8, "tone_shift": 6, "composition_shift": 5}[variant_type]
        dims = {
            d["name"]: DimensionScore(score=score, weight=d["weight"], rationale="r")
            for d in IMAGE_DIMENSIONS
        }
        gates = {
            "has_ai_artifacts": GateEvaluation(False, "clean"),
            "has_uncanny_faces": GateEvaluation(False, "ok"),
            "brand_safety_violation": GateEvaluation(False, "ok"),
        }
        return MediaEvaluationResult(
            ad_id=ad_id, variant_type=variant_type, media_type="image",
            media_path=str(media_path), model_used="gemini-2.5-flash",
            tokens_consumed=1500, dimensions=dims, penalty_gates=gates,
            raw_score=score/10.0, penalty_multiplier=1.0, composite_score=score*10.0,
        )

    fake_variant = MagicMock(
        image_path=str(tmp_path / "ad_X_anchor.png"), seed=1, variant_type="anchor",
    )
    Path(fake_variant.image_path).write_bytes(b"x")

    with patch("iterate.batch_processor.generate_variants", return_value=[
        MagicMock(image_path=str(tmp_path / f"ad_X_{v}.png"), seed=i, variant_type=v)
        for i, v in enumerate(("anchor", "tone_shift", "composition_shift"))
    ]):
        for v in ("anchor", "tone_shift", "composition_shift"):
            Path(tmp_path / f"ad_X_{v}.png").write_bytes(b"x")
        with patch("iterate.batch_processor.evaluate_media", side_effect=_fake_eval):
            with patch("iterate.batch_processor.extract_visual_spec", return_value=MagicMock(subject="s", setting="t")):
                winner = _generate_and_select_image(
                    ad=fake_ad, expanded_brief=MagicMock(visual_spec=MagicMock()),
                    brief=fake_brief, brief_seed=42, ledger_path=str(ledger),
                )

    assert winner is not None and "anchor" in winner  # anchor scored 8 → highest
    events = [json.loads(line) for line in ledger.read_text().splitlines()]
    types = [e["event_type"] for e in events]
    assert types.count("MediaEvaluation") == 3
    assert "ImageEvaluated" not in types
    assert "ImageScored" not in types
```

- [ ] **Step 2: Run, expect failure** — the old code still emits `ImageEvaluated`.

```
.venv/bin/python -m pytest tests/test_pipeline/test_batch_processor_pi04.py -v
```

Expected: FAIL (event type mismatch or function signature mismatch).

- [ ] **Step 3: Rewrite `_generate_and_select_image` in `iterate/batch_processor.py`**

Locate the function (currently spans ~lines 301-453). Replace the body from line ~320 (`from generate.visual_spec import extract_visual_spec` block) through the end with:

```python
def _generate_and_select_image(
    ad: Any, expanded_brief: Any, brief: dict[str, Any], brief_seed: int,
    ledger_path: str, persona: str | None = None,
    creative_brief: str = "auto", copy_on_image: bool = False,
    aspect_ratio: str = "1:1",
) -> str | None:
    """Generate N image variants, evaluate via media_quality, select winner."""
    try:
        visual_spec = extract_visual_spec(ad, expanded_brief, brief)
        variants = generate_variants(
            ad=ad, visual_spec=visual_spec, persona=persona,
            creative_brief=creative_brief, copy_on_image=copy_on_image,
            aspect_ratio=aspect_ratio, brief_seed=brief_seed,
        )
        if not variants:
            logger.warning("No image variants generated for %s", ad.ad_id)
            return None

        ad_copy = {
            "headline": ad.headline,
            "primary_text": getattr(ad, "primary_text", "") or getattr(ad, "body", ""),
            "cta_button": getattr(ad, "cta_button", "") or getattr(ad, "cta", ""),
        }
        session_config = brief.get("session_config")

        evaluations: list[MediaEvaluationResult] = []
        for variant in variants:
            result = evaluate_media(
                media_path=variant.image_path, ad_copy=ad_copy, ad_id=ad.ad_id,
                variant_type=variant.variant_type, media_type="image",
                session_config=session_config,
            )
            evaluations.append(result)
            _record_media_evaluation(ledger_path, brief, variant, result)

        selection = select_best(evaluations)
        if selection.all_failed or selection.winner is None:
            logger.warning("All image variants failed for %s — no winner", ad.ad_id)
            return None
        logger.info(
            "Image winner %s for %s (composite=%.2f, %d variants)",
            selection.winner.variant_type, ad.ad_id,
            selection.winner.composite_score, len(evaluations),
        )
        return selection.winner.media_path
    except Exception as e:
        logger.warning("Image generation failed for %s: %s", ad.ad_id, e)
        return None


def _record_media_evaluation(
    ledger_path: str, brief: dict[str, Any], variant: Any, result: MediaEvaluationResult,
) -> None:
    """Append the right ledger event for one variant evaluation."""
    if result.failed:
        LedgerWriter(ledger_path).record(MediaEvaluationFailed(
            ad_id=result.ad_id, brief_id=brief.get("brief_id", "unknown"),
            cycle_number=0, action=f"media_eval_failed_{result.variant_type}",
            tokens_consumed=result.tokens_consumed, model_used=result.model_used,
            seed=str(getattr(variant, "seed", "0")),
            inputs={"variant_type": result.variant_type, "media_type": result.media_type},
            outputs={
                "schema_version": "v2",
                "media_type": result.media_type,
                "failure_reason": result.failure_reason,
                "error_message": result.error_message,
            },
        ))
        return

    LedgerWriter(ledger_path).record(MediaEvaluation(
        ad_id=result.ad_id, brief_id=brief.get("brief_id", "unknown"),
        cycle_number=0, action=f"media_eval_{result.variant_type}",
        tokens_consumed=result.tokens_consumed, model_used=result.model_used,
        seed=str(getattr(variant, "seed", "0")),
        inputs={"variant_type": result.variant_type, "media_type": result.media_type},
        outputs={
            "schema_version": "v2",
            "media_type": result.media_type,
            "media_path": result.media_path,
            "dimensions": {
                name: {"score": ds.score, "weight": ds.weight, "rationale": ds.rationale}
                for name, ds in result.dimensions.items()
            },
            "penalty_gates": {
                name: {"triggered": ge.triggered, "rationale": ge.rationale}
                for name, ge in result.penalty_gates.items()
            },
            "raw_score": result.raw_score,
            "penalty_multiplier": result.penalty_multiplier,
            "composite_score": result.composite_score,
        },
    ))
```

- [ ] **Step 4: Update imports at top of `batch_processor.py`**

Find the existing imports block. Add:
```python
from evaluate.media_quality import evaluate_media, MediaEvaluationResult
from evaluate.media_selector import select_best
from iterate.ledger_events import MediaEvaluation, MediaEvaluationFailed
```
Remove (will be deleted in PI-10, but stop importing now):
```python
# DELETE these import lines:
from evaluate.image_evaluator import evaluate_image_attributes
from evaluate.coherence_checker import check_coherence
from evaluate.image_selector import ...
from evaluate.image_scorer import score_image
from iterate.ledger_events import ImageEvaluated, ImageScored
```

- [ ] **Step 5: Remove the `# PD-13: Image quality scoring` post-hoc block** (lines ~240-266 in current `process_batch`). That block called `score_image` and wrote `ImageScored`. It's redundant now — every variant including the winner already has a rich `MediaEvaluation`.

- [ ] **Step 6: Run the new PI-04 test, verify pass**

```
.venv/bin/python -m pytest tests/test_pipeline/test_batch_processor_pi04.py -v
```

Expected: PASS.

- [ ] **Step 7: Run the broader batch_processor regression**

```
.venv/bin/python -m pytest tests/test_pipeline/ -q --tb=line
```

Expected: existing tests pass except those that referenced `ImageEvaluated` / `ImageScored` / `evaluate_image_attributes` directly (those are migrated in PI-10). Note any new failures and fix before commit.

- [ ] **Step 8: Commit**

```
git add iterate/batch_processor.py tests/test_pipeline/test_batch_processor_pi04.py
git commit -m "feat(PI-04): image batch_processor emits MediaEvaluation events"
```

---

# Ticket PI-05: `media_quality.py` — video path

**Goal:** Extend `evaluate_media` to handle `media_type="video"`. Adds video-specific dimensions, gates, prompt, mime type, and (if needed) frame-extraction fallback when the video file is too large to upload.

**Files:**
- Modify: `evaluate/media_quality.py`
- Modify: `tests/test_evaluation/test_media_quality.py` (add video tests)

- [ ] **Step 1: Write the failing test** — append to `tests/test_evaluation/test_media_quality.py`:

```python
from evaluate.media_quality import VIDEO_DIMENSIONS, VIDEO_GATES


def test_video_dimensions_and_weights():
    """10 dimensions for video, weights sum to 1.0."""
    assert len(VIDEO_DIMENSIONS) == 10
    total = sum(d["weight"] for d in VIDEO_DIMENSIONS)
    assert abs(total - 1.0) < 1e-9
    names = {d["name"] for d in VIDEO_DIMENSIONS}
    assert names == {
        "thumb_stop_potential", "brand_consistency", "emotional_impact",
        "message_alignment", "audience_match", "production_quality",
        "hook_in_3s", "pacing", "motion_quality", "audio_appropriateness",
    }


def test_video_gates_have_caps():
    assert len(VIDEO_GATES) == 5
    names = {g["name"] for g in VIDEO_GATES}
    assert names == {
        "has_ai_artifacts", "has_uncanny_faces", "brand_safety_violation",
        "has_temporal_artifacts", "has_pacing_dead_zones",
    }


def _make_video_payload(score: int = 6) -> dict[str, Any]:
    return {
        "dimensions": {
            d["name"]: {"score": score, "rationale": f"video {d['name']}"}
            for d in VIDEO_DIMENSIONS
        },
        "penalty_gates": {
            g["name"]: {"triggered": False, "rationale": "clean"}
            for g in VIDEO_GATES
        },
    }


def test_evaluate_media_video_happy_path(tmp_path):
    media_path = tmp_path / "ad.mp4"
    media_path.write_bytes(b"fake-mp4")
    payload = json.dumps(_make_video_payload(score=6))
    with patch("evaluate.media_quality._call_multimodal", return_value=(payload, 3000)):
        result = evaluate_media(
            media_path=str(media_path),
            ad_copy={"headline": "Ace SAT", "body": "1-on-1", "cta": "Start"},
            ad_id="ad_001", variant_type="anchor", media_type="video",
        )
    assert not result.failed
    assert result.media_type == "video"
    assert len(result.dimensions) == 10
    assert len(result.penalty_gates) == 5
    assert result.composite_score == pytest.approx(60.0, abs=0.01)
```

- [ ] **Step 2: Run, verify fail (`ImportError: VIDEO_DIMENSIONS`)**

```
.venv/bin/python -m pytest tests/test_evaluation/test_media_quality.py::test_video_dimensions_and_weights -v
```

- [ ] **Step 3: Add `VIDEO_DIMENSIONS` and `VIDEO_GATES` to `evaluate/media_quality.py`**

After the `IMAGE_GATES` definition, add:

```python
# ---- Video rubric (PI-05) ----
VIDEO_DIMENSIONS: tuple[dict[str, Any], ...] = (
    {"name": "thumb_stop_potential", "weight": 0.15,
     "criterion": "Visual hook within 0.3s that stops the scroll."},
    {"name": "brand_consistency", "weight": 0.10,
     "criterion": "Varsity Tutors palette and tone visible throughout."},
    {"name": "emotional_impact", "weight": 0.10,
     "criterion": "Evokes a specific emotion across the clip."},
    {"name": "message_alignment", "weight": 0.10,
     "criterion": "Video reinforces the copy's message and CTA."},
    {"name": "audience_match", "weight": 0.10,
     "criterion": "Casting and setting match the target persona."},
    {"name": "production_quality", "weight": 0.05,
     "criterion": "Composition + color balance + no obvious tells."},
    {"name": "hook_in_3s", "weight": 0.15,
     "criterion": "Opening 3 seconds grab attention — Meta's #1 video metric."},
    {"name": "pacing", "weight": 0.10,
     "criterion": "No dead frames; energy matches the brief."},
    {"name": "motion_quality", "weight": 0.10,
     "criterion": "Smooth motion, no jank or unnatural transitions."},
    {"name": "audio_appropriateness", "weight": 0.05,
     "criterion": "Audio fits tone; intentional silence is OK."},
)

VIDEO_GATES: tuple[dict[str, Any], ...] = (
    {"name": "has_ai_artifacts", "cap": 0.5,
     "criterion": "Warped hands, mangled text, impossible geometry."},
    {"name": "has_uncanny_faces", "cap": 0.6,
     "criterion": "Asymmetric features, melted skin, lifeless eyes."},
    {"name": "brand_safety_violation", "cap": 0.3,
     "criterion": "Competitor logos, inappropriate context."},
    {"name": "has_temporal_artifacts", "cap": 0.4,
     "criterion": "Flickering, frame jumps, faces morphing across cuts."},
    {"name": "has_pacing_dead_zones", "cap": 0.7,
     "criterion": "Long static moments where nothing happens."},
)
```

- [ ] **Step 4: Update `evaluate_media` to dispatch on `media_type`**

Replace the early `if media_type != "image": raise NotImplementedError(...)` line with:

```python
if media_type == "image":
    rubric_dims, rubric_gates = IMAGE_DIMENSIONS, IMAGE_GATES
    prompt = _build_image_prompt(ad_copy, session_config)
elif media_type == "video":
    rubric_dims, rubric_gates = VIDEO_DIMENSIONS, VIDEO_GATES
    prompt = _build_video_prompt(ad_copy, session_config)
else:
    return _failure_result(
        ad_id, variant_type, media_type, media_path,
        "unsupported_media_type", f"media_type={media_type}",
    )
```

- [ ] **Step 5: Add `_build_video_prompt` next to `_build_image_prompt`**

```python
def _build_video_prompt(ad_copy: dict[str, Any], session_config: dict[str, Any] | None) -> str:
    headline = ad_copy.get("headline", "")
    primary_text = ad_copy.get("primary_text", "") or ad_copy.get("body", "")
    cta = ad_copy.get("cta_button", "") or ad_copy.get("cta", "")
    audience = (session_config or {}).get("audience", "")
    persona = (session_config or {}).get("persona", "")

    dims_block = "\n".join(
        f"{i+1}. {d['name']} (weight {d['weight']:.2f}) — {d['criterion']}"
        for i, d in enumerate(VIDEO_DIMENSIONS)
    )
    gates_block = "\n".join(
        f"- {g['name']} (cap {g['cap']:.1f}) — {g['criterion']}"
        for g in VIDEO_GATES
    )
    return f"""You are a strict UGC-style video ad evaluator for Varsity Tutors SAT test prep on Facebook and Instagram.

CALIBRATION: AI-generated video has visible weak points. Be specific. A score of 7 is genuinely good. 9–10 is exceptional and rare. Most generated video clips score 4–6. Watch the full clip before scoring.

AD COPY (for message-alignment evaluation):
- Headline: {headline or "(none)"}
- Primary Text: {primary_text or "(none)"}
- CTA: {cta or "(none)"}
- Target audience: {audience or "(none)"}
- Persona: {persona or "(none)"}

DIMENSIONS — score 1–10 with a 1–2 sentence rationale naming a specific moment or visual element (e.g. "the 0:02 cut from student to tutor").

{dims_block}

PENALTY GATES — answer true / false with a 1-sentence rationale.

{gates_block}

Return ONLY a JSON object with this exact shape:
{{
  "dimensions": {{"thumb_stop_potential": {{"score": 7, "rationale": "..."}}, ...}},
  "penalty_gates": {{"has_ai_artifacts": {{"triggered": false, "rationale": "..."}}, ...}}
}}"""
```

- [ ] **Step 6: Run all media_quality tests, verify pass**

```
.venv/bin/python -m pytest tests/test_evaluation/test_media_quality.py -v
```

Expected: 11/11 PASS (8 from PI-02 + 3 new for video).

- [ ] **Step 7: Commit**

```
git add evaluate/media_quality.py tests/test_evaluation/test_media_quality.py
git commit -m "feat(PI-05): media_quality video path — 10 dimensions + 5 gates"
```

---

# Ticket PI-06: Wire video pipeline + missing-file root-cause fix

**Goal:** Migrate `generate_video/orchestrator.py`, `selector.py`, `regen.py` to call `evaluate_media(media_type="video")` + `select_best`. Stop emitting `VideoEvaluated`/`VideoCoherenceChecked`/`VideoScored`. Investigate and fix the 82 missing-file ghost events from PI-00.

**Files:**
- Modify: `generate_video/orchestrator.py`
- Modify: `generate_video/selector.py`
- Modify: `generate_video/regen.py`
- Test: `tests/test_pipeline/test_video_pipeline_pi06.py` (new)

- [ ] **Step 1: Read the current code to find where evaluators are called**

```
.venv/bin/python -c "import ast, pathlib; [print(p, [n.name for n in ast.walk(ast.parse(p.read_text())) if isinstance(n, ast.FunctionDef)]) for p in pathlib.Path('generate_video').glob('*.py')]"
```

Identify the function(s) currently calling `evaluate_video_attributes` / `check_video_coherence` / `score_video`. Take notes.

- [ ] **Step 2: Write failing test** — `tests/test_pipeline/test_video_pipeline_pi06.py`:

```python
"""PI-06: video pipeline emits MediaEvaluation events."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from evaluate.media_quality import (
    DimensionScore, GateEvaluation, MediaEvaluationResult, VIDEO_DIMENSIONS,
)


def _fake_video_eval(media_path, ad_copy, ad_id, variant_type, media_type="video", **kw):
    score = {"anchor": 7, "alternative": 5}.get(variant_type, 6)
    dims = {
        d["name"]: DimensionScore(score=score, weight=d["weight"], rationale="r")
        for d in VIDEO_DIMENSIONS
    }
    gates = {
        g: GateEvaluation(False, "ok") for g in (
            "has_ai_artifacts", "has_uncanny_faces", "brand_safety_violation",
            "has_temporal_artifacts", "has_pacing_dead_zones",
        )
    }
    return MediaEvaluationResult(
        ad_id=ad_id, variant_type=variant_type, media_type="video",
        media_path=str(media_path), model_used="gemini-2.5-flash",
        tokens_consumed=3000, dimensions=dims, penalty_gates=gates,
        raw_score=score/10.0, penalty_multiplier=1.0, composite_score=score*10.0,
    )


def test_video_orchestrator_writes_media_evaluation_events(tmp_path):
    """One MediaEvaluation per variant; no legacy VideoEvaluated."""
    from generate_video.orchestrator import score_and_select_video_variants

    ledger = tmp_path / "ledger.jsonl"
    fake_ad = MagicMock(ad_id="ad_X", headline="h", primary_text="b", cta_button="c")
    variants = []
    for v, name in enumerate(("anchor", "alternative")):
        p = tmp_path / f"{name}.mp4"
        p.write_bytes(b"x")
        variants.append(MagicMock(video_path=str(p), variant_id=name, seed=v))

    with patch("generate_video.orchestrator.evaluate_media", side_effect=_fake_video_eval):
        winner = score_and_select_video_variants(
            ad=fake_ad, variants=variants, brief={"brief_id": "brief_001"},
            ledger_path=str(ledger),
        )

    assert winner is not None
    assert "anchor" in winner  # higher composite
    events = [json.loads(line) for line in ledger.read_text().splitlines()]
    types = [e["event_type"] for e in events]
    assert types.count("MediaEvaluation") == 2
    assert "VideoEvaluated" not in types
    assert "VideoCoherenceChecked" not in types
    assert "VideoScored" not in types


def test_video_missing_file_emits_failed_event(tmp_path):
    """Missing video file → MediaEvaluationFailed, not a zero-scored MediaEvaluation."""
    from generate_video.orchestrator import score_and_select_video_variants
    ledger = tmp_path / "ledger.jsonl"
    fake_ad = MagicMock(ad_id="ad_Y", headline="h", primary_text="b", cta_button="c")
    bad = MagicMock(video_path=str(tmp_path / "missing.mp4"), variant_id="anchor", seed=0)
    # File does NOT exist
    winner = score_and_select_video_variants(
        ad=fake_ad, variants=[bad], brief={"brief_id": "brief_001"},
        ledger_path=str(ledger),
    )
    assert winner is None
    events = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert events[0]["event_type"] == "MediaEvaluationFailed"
    assert events[0]["outputs"]["failure_reason"] == "file_not_found"
```

- [ ] **Step 3: Run, expect failure** (function doesn't exist / wrong shape).

```
.venv/bin/python -m pytest tests/test_pipeline/test_video_pipeline_pi06.py -v
```

- [ ] **Step 4: Create / rewrite `score_and_select_video_variants` in `generate_video/orchestrator.py`**

Locate the existing video score/select logic (originally splits across `selector.py` + parts of `orchestrator.py`). Consolidate into one function:

```python
from evaluate.media_quality import evaluate_media, MediaEvaluationResult
from evaluate.media_selector import select_best
from iterate.ledger_events import MediaEvaluation, MediaEvaluationFailed
from iterate.ledger import LedgerWriter


def score_and_select_video_variants(
    ad: Any, variants: list[Any], brief: dict[str, Any], ledger_path: str,
) -> str | None:
    """Evaluate N video variants via unified media_quality, pick winner."""
    ad_copy = {
        "headline": ad.headline,
        "primary_text": getattr(ad, "primary_text", "") or getattr(ad, "body", ""),
        "cta_button": getattr(ad, "cta_button", "") or getattr(ad, "cta", ""),
    }
    session_config = brief.get("session_config")
    evaluations: list[MediaEvaluationResult] = []
    for v in variants:
        result = evaluate_media(
            media_path=v.video_path, ad_copy=ad_copy, ad_id=ad.ad_id,
            variant_type=v.variant_id, media_type="video",
            session_config=session_config,
        )
        evaluations.append(result)
        _record_video_evaluation(ledger_path, brief, v, result)

    selection = select_best(evaluations)
    if selection.all_failed or selection.winner is None:
        return None
    return selection.winner.media_path


def _record_video_evaluation(
    ledger_path: str, brief: dict[str, Any], variant: Any, result: MediaEvaluationResult,
) -> None:
    # Identical body to batch_processor._record_media_evaluation; consider
    # DRYing into a shared helper in a follow-up if both stay long-lived.
    if result.failed:
        LedgerWriter(ledger_path).record(MediaEvaluationFailed(
            ad_id=result.ad_id, brief_id=brief.get("brief_id", "unknown"),
            cycle_number=0, action=f"media_eval_failed_{result.variant_type}",
            tokens_consumed=result.tokens_consumed, model_used=result.model_used,
            seed=str(getattr(variant, "seed", "0")),
            inputs={"variant_type": result.variant_type, "media_type": "video"},
            outputs={
                "schema_version": "v2",
                "media_type": "video",
                "failure_reason": result.failure_reason,
                "error_message": result.error_message,
            },
        ))
        return
    LedgerWriter(ledger_path).record(MediaEvaluation(
        ad_id=result.ad_id, brief_id=brief.get("brief_id", "unknown"),
        cycle_number=0, action=f"media_eval_{result.variant_type}",
        tokens_consumed=result.tokens_consumed, model_used=result.model_used,
        seed=str(getattr(variant, "seed", "0")),
        inputs={"variant_type": result.variant_type, "media_type": "video"},
        outputs={
            "schema_version": "v2",
            "media_type": "video",
            "media_path": result.media_path,
            "dimensions": {
                name: {"score": ds.score, "weight": ds.weight, "rationale": ds.rationale}
                for name, ds in result.dimensions.items()
            },
            "penalty_gates": {
                name: {"triggered": ge.triggered, "rationale": ge.rationale}
                for name, ge in result.penalty_gates.items()
            },
            "raw_score": result.raw_score,
            "penalty_multiplier": result.penalty_multiplier,
            "composite_score": result.composite_score,
        },
    ))
```

- [ ] **Step 5: Replace the call sites in the rest of `orchestrator.py` / `selector.py` / `regen.py`** — wherever the old `evaluate_video_attributes` / `check_video_coherence` / `score_video` were called, invoke `score_and_select_video_variants` instead. Delete imports of `VideoCoherenceResult`, `VideoEvaluated`, etc., from these three files.

- [ ] **Step 6: Investigate the 82 missing-file ghost events**

```
.venv/bin/python -c "
import json, glob
for f in sorted(glob.glob('data/sessions/sess_*/ledger.jsonl')):
    bad = [e for e in (json.loads(l) for l in open(f)) if e.get('event_type') == 'VideoEvaluated' and e.get('outputs', {}).get('attribute_pass_pct') == 0.0]
    if bad:
        print(f, len(bad), bad[0].get('outputs', {}).get('media_path') or 'no path')
" | head -10
```

For each session with ghost events, check whether the video file was supposed to be at the path the ledger references. Look for: (a) generator wrote to one path, evaluator looked at another; (b) Veo / Fal output never finished writing to disk; (c) cleanup script removed the file before evaluator ran.

Fix the root cause in `generate_video/orchestrator.py` (or wherever the gap is — likely in the Veo response handler not awaiting file write completion). Add a short DEVLOG note documenting the cause and the fix.

- [ ] **Step 7: Run PI-06 tests + existing video tests**

```
.venv/bin/python -m pytest tests/test_pipeline/test_video_pipeline_pi06.py tests/test_pipeline/test_video_*.py -v --tb=line
```

Expected: PI-06 tests PASS. Some existing video tests may need updates (covered in PI-10). Note any new failures vs. pre-PI baseline.

- [ ] **Step 8: Commit**

```
git add generate_video/ tests/test_pipeline/test_video_pipeline_pi06.py
git commit -m "feat(PI-06): video pipeline emits MediaEvaluation; missing-file fix"
```

---

# Ticket PI-07: Dashboard `/variants` endpoint v2 branch

**Goal:** `/api/sessions/{id}/ads/{ad_id}/variants` returns the new v2 shape when the session's ledger has `MediaEvaluation` events. Falls back to the existing v1 shape for legacy sessions.

**Files:**
- Modify: `app/api/routes/dashboard.py` — `get_ad_variants` function (lines ~243-367)
- Test: `tests/test_app/test_ad_variants_route_v2.py` (new)

- [ ] **Step 1: Write the failing test** — `tests/test_app/test_ad_variants_route_v2.py`:

```python
"""PI-07: /variants endpoint emits v2 shape when MediaEvaluation events exist."""
from __future__ import annotations

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient


def _write_v2_ledger(p: Path, ad_id: str) -> None:
    """Write a ledger with 3 MediaEvaluation events for one ad."""
    events = []
    for i, (variant, composite) in enumerate(
        [("anchor", 80.0), ("tone_shift", 60.0), ("composition_shift", 45.0)]
    ):
        events.append({
            "event_type": "ImageGenerated",
            "ad_id": ad_id, "model_used": "nano-banana-pro-preview",
            "inputs": {"variant_type": variant},
            "outputs": {"image_path": f"out/{ad_id}_{variant}.png"},
        })
        events.append({
            "event_type": "MediaEvaluation",
            "ad_id": ad_id, "brief_id": "brief_001",
            "cycle_number": 0, "action": f"media_eval_{variant}",
            "tokens_consumed": 1500, "model_used": "gemini-2.5-flash",
            "seed": "0",
            "inputs": {"variant_type": variant, "media_type": "image"},
            "outputs": {
                "schema_version": "v2", "media_type": "image",
                "media_path": f"out/{ad_id}_{variant}.png",
                "dimensions": {
                    "thumb_stop_potential": {"score": 8, "weight": 0.20, "rationale": "rich"},
                    "mobile_legibility": {"score": 7, "weight": 0.15, "rationale": "ok"},
                },
                "penalty_gates": {
                    "has_ai_artifacts": {"triggered": False, "rationale": "clean"},
                },
                "raw_score": composite/100.0, "penalty_multiplier": 1.0,
                "composite_score": composite,
            },
        })
    p.write_text("\n".join(json.dumps(e) for e in events))


def test_variants_endpoint_returns_v2_shape(tmp_path, monkeypatch, auth_test_client):
    ledger = tmp_path / "ledger.jsonl"
    _write_v2_ledger(ledger, ad_id="ad_X")
    # Test fixture should make a session row with this ledger_path; reuse the
    # existing pattern from test_ad_variants_route.py.
    client, session_id, ad_id = auth_test_client(ledger)
    resp = client.get(f"/api/sessions/{session_id}/ads/{ad_id}/variants")
    assert resp.status_code == 200
    body = resp.json()
    assert body["schema_version"] == "v2"
    assert len(body["variants"]) == 3
    # Winner is the highest composite
    winners = [v for v in body["variants"] if v["is_winner"]]
    assert len(winners) == 1
    assert winners[0]["variant_type"] == "anchor"
    # Per-variant dimensions present
    assert "dimensions" in winners[0]
    assert "thumb_stop_potential" in winners[0]["dimensions"]
    # Loser carries rejection_reason
    losers = [v for v in body["variants"] if not v["is_winner"]]
    assert all("rejection_reason" in v for v in losers)
    # Selection criteria reflect v2 formula
    assert "raw_score" in body["selection_criteria"]["formula"] or "composite" in body["selection_criteria"]["formula"].lower()


def test_variants_endpoint_falls_back_to_v1_for_legacy(tmp_path, auth_test_client):
    """A legacy session with ImageEvaluated events still returns the v1 shape."""
    ledger = tmp_path / "ledger.jsonl"
    # Write a v1-style ImageEvaluated event
    events = [
        {"event_type": "ImageGenerated", "ad_id": "ad_Y",
         "model_used": "gemini-2.5-flash-image",
         "inputs": {"variant_type": "anchor"},
         "outputs": {"image_path": "out/ad_Y_anchor.png"}},
        {"event_type": "ImageEvaluated", "ad_id": "ad_Y",
         "inputs": {"variant_type": "anchor"},
         "outputs": {"attribute_pass_pct": 0.8, "coherence_avg": 0.5, "composite_score": 0.35}},
    ]
    ledger.write_text("\n".join(json.dumps(e) for e in events))
    client, session_id, ad_id = auth_test_client(ledger, ad_id="ad_Y")
    resp = client.get(f"/api/sessions/{session_id}/ads/{ad_id}/variants")
    assert resp.status_code == 200
    body = resp.json()
    assert body["schema_version"] == "v1"
    assert "composite_score" in body["variants"][0]
```

- [ ] **Step 2: Run, expect failure**

```
.venv/bin/python -m pytest tests/test_app/test_ad_variants_route_v2.py -v
```

- [ ] **Step 3: Rewrite `get_ad_variants`** in `app/api/routes/dashboard.py` — at the top of the function (just after the session ownership check), branch on event type:

```python
@router.get("/{session_id}/ads/{ad_id}/variants")
def get_ad_variants(
    session_id: str, ad_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    init_db()
    session = _get_session(db, session_id, user["user_id"])
    ledger_path = session.ledger_path
    if not ledger_path or not Path(ledger_path).exists():
        raise HTTPException(status_code=404, detail="Session ledger not found")

    from iterate.ledger_reader import read_dicts_filtered
    events = read_dicts_filtered(ledger_path, ad_id=ad_id)
    if not events:
        raise HTTPException(status_code=404, detail="No events for that ad")

    has_v2 = any(e.get("event_type") == "MediaEvaluation" for e in events)
    if has_v2:
        return _build_variants_v2(session_id, ad_id, events)
    return _build_variants_v1(session_id, ad_id, events)  # extracted from old body
```

Then implement `_build_variants_v2`:

```python
def _build_variants_v2(session_id: str, ad_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    """v2 shape: per-variant dimensions, gates, raw_score, winner/rejection reasons."""
    rate_per_call = {
        "nano-banana-pro-preview": 0.13,
        "gemini-2.5-flash-image": 0.035,
        "gemini-2.0-flash-preview-image-generation": 0.13,
    }
    variants_by_type: dict[str, dict[str, Any]] = {}
    for ev in events:
        if ev.get("event_type") == "ImageGenerated":
            vt = (ev.get("inputs") or {}).get("variant_type", "")
            outs = ev.get("outputs") or {}
            path = outs.get("image_path", "")
            variants_by_type.setdefault(vt, {})
            variants_by_type[vt]["image_path"] = path or None
            variants_by_type[vt]["image_url"] = (
                f"/api/images/{Path(path).name}" if path else None
            )
            variants_by_type[vt]["model_used"] = ev.get("model_used", "")
            variants_by_type[vt]["predicted_cost_usd"] = rate_per_call.get(ev.get("model_used", ""), 0.0)
        elif ev.get("event_type") == "MediaEvaluation":
            vt = (ev.get("inputs") or {}).get("variant_type", "")
            outs = ev.get("outputs") or {}
            variants_by_type.setdefault(vt, {})
            variants_by_type[vt].update({
                "variant_type": vt,
                "media_type": outs.get("media_type", "image"),
                "dimensions": outs.get("dimensions", {}),
                "penalty_gates": outs.get("penalty_gates", {}),
                "raw_score": outs.get("raw_score", 0.0),
                "penalty_multiplier": outs.get("penalty_multiplier", 1.0),
                "composite_score": outs.get("composite_score", 0.0),
            })

    variants = list(variants_by_type.values())
    if not variants:
        raise HTTPException(status_code=404, detail="No image variants for that ad")

    winner = max(variants, key=lambda v: v.get("composite_score", 0))
    for v in variants:
        v["is_winner"] = (v is winner)
        v.setdefault("variant_type", "unknown")
        v.setdefault("composite_score", 0.0)

    # winner_reason: top 2 distinguishing dimensions
    losers = [v for v in variants if not v["is_winner"]]
    if losers:
        dim_names = list(winner.get("dimensions", {}).keys())
        deltas = {}
        for d in dim_names:
            w_score = winner["dimensions"][d].get("score", 0)
            loser_mean = sum(lo["dimensions"].get(d, {}).get("score", 0) for lo in losers) / len(losers)
            deltas[d] = w_score - loser_mean
        top2 = sorted(deltas, key=deltas.get, reverse=True)[:2]
        winner_reason = {
            "composite_score": winner["composite_score"],
            "distinguishing_dimensions": [
                {"dimension": d, "delta_vs_mean": round(deltas[d], 2)} for d in top2
            ],
        }
        for lo in losers:
            dim_deltas = {
                d: lo["dimensions"].get(d, {}).get("score", 0)
                   - winner["dimensions"].get(d, {}).get("score", 0)
                for d in dim_names
            }
            worst = min(dim_deltas, key=dim_deltas.get)
            lo["rejection_reason"] = {
                "composite_delta": round(lo["composite_score"] - winner["composite_score"], 2),
                "worst_dimension": worst,
                "worst_dimension_delta": round(dim_deltas[worst], 2),
                "worst_dimension_rationale": lo["dimensions"].get(worst, {}).get("rationale", ""),
            }
    else:
        winner_reason = None

    return {
        "session_id": session_id, "ad_id": ad_id,
        "schema_version": "v2",
        "selection_criteria": {
            "formula": "composite = sum(weight * dim_score) / 10 * penalty_mult * 100",
            "winner_variant_type": winner["variant_type"],
            "winner_composite_score": winner["composite_score"],
        },
        "winner_reason": winner_reason,
        "variants": variants,
    }
```

Refactor the existing body into `_build_variants_v1` (no logic changes — wrap the current code in that helper and have it return the same dict plus `"schema_version": "v1"`).

- [ ] **Step 4: Run new tests, verify PASS**

```
.venv/bin/python -m pytest tests/test_app/test_ad_variants_route_v2.py tests/test_app/test_ad_variants_route.py -v
```

Expected: existing v1 tests still pass + 2 new v2 tests pass.

- [ ] **Step 5: Commit**

```
git add app/api/routes/dashboard.py tests/test_app/test_ad_variants_route_v2.py
git commit -m "feat(PI-07): /variants endpoint v2 branch with dimensions + rationales"
```

---

# Ticket PI-08: `VariantsPanel` UI — Evidence panel + legacy badge

**Goal:** Frontend handles both v1 and v2 response shapes. v2 variant cards reveal an Evidence panel with per-dimension scores + rationales; legacy sessions show a "Legacy scoring" badge. Video sessions get unblocked in the Ad Library.

**Files:**
- Modify: `app/frontend/src/api/dashboard.ts` — TypeScript types
- Modify: `app/frontend/src/components/VariantsPanel.tsx` — Evidence panel + legacy branch
- Modify: `app/frontend/src/tabs/AdLibrary.tsx` — remove the video-session hide guard
- Test: smoke check via `npm run build` and manual browser

- [ ] **Step 1: Update `app/frontend/src/api/dashboard.ts`** — extend types to allow both v1 and v2 shapes:

```typescript
export interface DimensionScore {
  score: number
  weight: number
  rationale: string
}
export interface GateEvaluation {
  triggered: boolean
  rationale: string
}
export interface AdVariantV2 {
  variant_type: string
  media_type: 'image' | 'video'
  image_path: string | null
  image_url: string | null
  model_used: string
  predicted_cost_usd: number
  composite_score: number
  raw_score: number
  penalty_multiplier: number
  dimensions: Record<string, DimensionScore>
  penalty_gates: Record<string, GateEvaluation>
  is_winner: boolean
  rejection_reason?: {
    composite_delta: number
    worst_dimension: string
    worst_dimension_delta: number
    worst_dimension_rationale: string
  }
}
export interface AdVariantsV2Response {
  session_id: string
  ad_id: string
  schema_version: 'v2'
  selection_criteria: {
    formula: string
    winner_variant_type: string
    winner_composite_score: number
  }
  winner_reason: {
    composite_score: number
    distinguishing_dimensions: Array<{ dimension: string; delta_vs_mean?: number; absolute_score?: number; note?: string }>
  } | null
  variants: AdVariantV2[]
}
export type AnyVariantsResponse = AdVariantsResponse | AdVariantsV2Response
```

Update the `fetchAdVariants` return type:

```typescript
export const fetchAdVariants = (sessionId: string, adId: string) =>
  get<AnyVariantsResponse>(`${BASE}/${sessionId}/ads/${adId}/variants`)
```

- [ ] **Step 2: Update `VariantsPanel.tsx` — branch on `schema_version`**

Top of the component, after fetching `data`:

```typescript
const isV2 = (data as AdVariantsV2Response).schema_version === 'v2'
if (!isV2) {
  // Render the existing legacy view with a badge.
  return (
    <div style={styles.container}>
      <div style={{ ...styles.header, color: colors.muted, fontStyle: 'italic' }}>
        Legacy scoring (pre-2026-05-15) — per-dimension breakdown not available.
      </div>
      {/* existing v1 grid as today */}
    </div>
  )
}
```

For v2, render the new card shape with the Evidence expander:

```tsx
function EvidencePanel({ variant }: { variant: AdVariantV2 }) {
  const [open, setOpen] = useState(false)
  return (
    <div style={{ marginTop: '8px' }}>
      <button onClick={() => setOpen(!open)} style={styles.expander}>
        {open ? '▾' : '▸'} Evidence
      </button>
      {open && (
        <div style={styles.evidence}>
          <table style={{ width: '100%', fontSize: font.xs }}>
            <thead><tr><th>Dimension</th><th>Score</th><th>Weight</th><th>Rationale</th></tr></thead>
            <tbody>
              {Object.entries(variant.dimensions).map(([name, d]) => (
                <tr key={name}>
                  <td>{name}</td>
                  <td>{d.score}/10</td>
                  <td>{(d.weight * 100).toFixed(0)}%</td>
                  <td style={{ fontStyle: 'italic' }}>{d.rationale}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {Object.entries(variant.penalty_gates).filter(([, g]) => g.triggered).length > 0 && (
            <div style={{ marginTop: '8px', color: colors.danger }}>
              <strong>Triggered gates:</strong>
              <ul>
                {Object.entries(variant.penalty_gates)
                  .filter(([, g]) => g.triggered)
                  .map(([name, g]) => (
                    <li key={name}>{name} — {g.rationale}</li>
                  ))}
              </ul>
            </div>
          )}
          <div style={{ marginTop: '8px', color: colors.muted }}>
            raw {variant.raw_score.toFixed(2)} × penalty {variant.penalty_multiplier.toFixed(2)}
            = composite {variant.composite_score.toFixed(1)}
          </div>
        </div>
      )}
    </div>
  )
}
```

Replace the existing `describeReason` block with v2 versions:

```typescript
function describeWinnerReason(reason: AdVariantsV2Response['winner_reason']): string {
  if (!reason || !reason.distinguishing_dimensions.length) return ''
  const dims = reason.distinguishing_dimensions
    .map(d => `${d.dimension} ${d.delta_vs_mean != null ? `+${d.delta_vs_mean}` : `(score ${d.absolute_score})`}`)
    .join(', ')
  return `Why this won: top vs mean of other variants — ${dims}`
}

function describeRejection(v: AdVariantV2): string {
  if (!v.rejection_reason) return ''
  const r = v.rejection_reason
  return `Lost on ${r.worst_dimension}: ${r.worst_dimension_delta} score delta (composite ${r.composite_delta}). ${r.worst_dimension_rationale}`
}
```

- [ ] **Step 3: Unblock video sessions in `AdLibrary.tsx`**

Find the existing guard that hides VariantsPanel for video sessions (commit `2c527e8`). Remove it — the unified `media_type` field lets the same component render video variants. (Video thumbnails will use existing image_url for the first-frame poster when present.)

- [ ] **Step 4: Smoke test**

```
cd app/frontend && npm run build 2>&1 | tail -10
```

Expected: build succeeds, no TypeScript errors.

Manual browser test:
- Start the dev server: `cd app/frontend && npm run dev`
- Sign in, open a session whose ledger has v2 events, expand a variant card → Evidence panel shows 8 dimensions with rationales
- Open a legacy session → "Legacy scoring (pre-2026-05-15)" badge visible

- [ ] **Step 5: Commit**

```
git add app/frontend/src/api/dashboard.ts app/frontend/src/components/VariantsPanel.tsx app/frontend/src/tabs/AdLibrary.tsx
git commit -m "feat(PI-08): VariantsPanel Evidence panel + legacy badge + video unblock"
```

---

# Ticket PI-09: Calibration golden set + spread test

**Goal:** Assemble a 12-image + 8-video golden set with tier labels. Add an opt-in pytest marker `calibration` that runs the unified evaluator against each item and asserts the spread + tier separation contracts. This test is the granularity canary.

**Files:**
- Create: `tests/test_evaluation/fixtures/media_quality/annotations.yaml`
- Create: `tests/test_evaluation/fixtures/media_quality/images/` (12 files)
- Create: `tests/test_evaluation/fixtures/media_quality/videos/` (8 files)
- Create: `tests/test_evaluation/test_media_quality_calibration.py`
- Modify: `pyproject.toml` — register the `calibration` pytest marker

- [ ] **Step 1: Source the 12 image references**

Walk `data/sessions/sess_*/` and copy 12 representative `.png` files to `tests/test_evaluation/fixtures/media_quality/images/`:
- 4 obviously-great (winners from past sessions with strong composition)
- 4 mediocre (mid-pack winners)
- 4 obviously-bad (planted with: blurry, off-brand, AI-artifact hands, generic stock-photo)

If you can't find 4 obviously-bad in the historical data, hand-create 4 from public-domain bad-AI-image collections. Document the source of each in `annotations.yaml`.

- [ ] **Step 2: Source the 8 video references**

Same process for 8 video files (`.mp4`) from `data/sessions/sess_*/videos/`:
- 3 great (clean Veo outputs)
- 3 mid
- 2 bad (intentionally pick clips with `has_temporal_artifacts` triggers — flickering frames, morphing faces across cuts)

- [ ] **Step 3: Write the annotations file** — `tests/test_evaluation/fixtures/media_quality/annotations.yaml`:

```yaml
# Calibration golden set — PI-09
# tier: great | mid | bad
# source: where the file came from (session_id or hand-curated)
images:
  - file: img_great_01.png
    tier: great
    source: sess_f71c27911fe08803/images/anchor_1x1.png
    notes: strong focal point, brand colors, clean composition
  # ...11 more
videos:
  - file: vid_great_01.mp4
    tier: great
    source: sess_aaf2ccf3ca302cea/videos/anchor_9x16.mp4
    notes: clean Veo output, hook within 1s, smooth motion
  # ...7 more
```

- [ ] **Step 4: Register the `calibration` marker** — append to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "calibration: opt-in golden-set tests that hit the real Gemini API. Skipped unless GEMINI_API_KEY is set.",
]
```

- [ ] **Step 5: Write the calibration test** — `tests/test_evaluation/test_media_quality_calibration.py`:

```python
"""Golden-set calibration test for media_quality evaluator (PI-09).

Opt-in: requires GEMINI_API_KEY. Runs nightly + on prompt changes.
Asserts spread, tier separation, and that planted gate triggers fire.
"""
from __future__ import annotations

import os
from pathlib import Path
import yaml
import pytest

from evaluate.media_quality import evaluate_media

FIXTURES = Path(__file__).parent / "fixtures" / "media_quality"
ANNOTATIONS = yaml.safe_load((FIXTURES / "annotations.yaml").read_text())

requires_api = pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set — calibration test is opt-in",
)


def _ad_copy() -> dict:
    return {
        "headline": "Ace Your SAT with Expert Tutors",
        "primary_text": "1-on-1 tutoring that builds confidence and raises scores.",
        "cta_button": "Start Today",
    }


def _evaluate_all(items: list[dict], media_subdir: str, media_type: str) -> list[dict]:
    out = []
    for item in items:
        result = evaluate_media(
            media_path=str(FIXTURES / media_subdir / item["file"]),
            ad_copy=_ad_copy(), ad_id=item["file"], variant_type="calibration",
            media_type=media_type,
        )
        assert not result.failed, f"Calibration eval failed for {item['file']}: {result.failure_reason}"
        out.append({"item": item, "result": result})
    return out


@requires_api
@pytest.mark.calibration
def test_image_calibration_spread_and_tier_separation():
    rated = _evaluate_all(ANNOTATIONS["images"], "images", "image")
    scores_by_tier = {"great": [], "mid": [], "bad": []}
    for r in rated:
        scores_by_tier[r["item"]["tier"]].append(r["result"].composite_score)

    # 1. Obvious tiers separate
    for s in scores_by_tier["great"]:
        assert s > 70, f"great image scored {s}, expected > 70"
    for s in scores_by_tier["bad"]:
        assert s < 35, f"bad image scored {s}, expected < 35"

    # 2. Within-tier spread
    for tier in ("great", "mid", "bad"):
        scores = scores_by_tier[tier]
        assert max(scores) - min(scores) >= 10, (
            f"{tier} tier collapsed: {scores}"
        )

    # 3. Overall granularity
    all_scores = sorted({round(r["result"].composite_score, 1) for r in rated})
    assert len(all_scores) >= 8, (
        f"only {len(all_scores)} distinct composites across {len(rated)} images: {all_scores}"
    )

    # 4. Planted bad images trigger has_ai_artifacts
    bad_results = [r["result"] for r in rated if r["item"]["tier"] == "bad"]
    artifact_triggered = [r for r in bad_results
                          if r.penalty_gates.get("has_ai_artifacts", None) and r.penalty_gates["has_ai_artifacts"].triggered]
    assert len(artifact_triggered) >= 2, (
        f"only {len(artifact_triggered)}/{len(bad_results)} planted bad images triggered has_ai_artifacts"
    )


@requires_api
@pytest.mark.calibration
def test_video_calibration_spread_and_tier_separation():
    rated = _evaluate_all(ANNOTATIONS["videos"], "videos", "video")
    scores_by_tier = {"great": [], "mid": [], "bad": []}
    for r in rated:
        scores_by_tier[r["item"]["tier"]].append(r["result"].composite_score)

    for s in scores_by_tier["great"]:
        assert s > 60, f"great video scored {s}"
    for s in scores_by_tier["bad"]:
        assert s < 40, f"bad video scored {s}"

    all_scores = sorted({round(r["result"].composite_score, 1) for r in rated})
    assert len(all_scores) >= 6, (
        f"only {len(all_scores)} distinct composites across {len(rated)} videos"
    )
```

- [ ] **Step 6: Run the calibration test against real API**

```
.venv/bin/python -m pytest tests/test_evaluation/test_media_quality_calibration.py -m calibration -v
```

Expected: PASS. If FAIL, iterate on the prompt in `media_quality.py` (most likely lever: strengthen "calibration" paragraph that pushes scores away from the middle). Budget 2–4 prompt-tuning cycles. Each cycle: edit prompt → run test → read which assertion failed → adjust.

- [ ] **Step 7: Commit**

```
git add tests/test_evaluation/fixtures/media_quality/ tests/test_evaluation/test_media_quality_calibration.py pyproject.toml
git commit -m "feat(PI-09): golden-set calibration test — granularity canary"
```

---

# Ticket PI-10: Retire 6 legacy modules + their tests

**Goal:** Delete the six legacy evaluator modules and their dedicated test files now that nothing imports them. Update any remaining test files that still imported retired symbols.

**Files:**
- Delete: `evaluate/image_evaluator.py`
- Delete: `evaluate/coherence_checker.py`
- Delete: `evaluate/image_scorer.py`
- Delete: `evaluate/video_evaluator.py`
- Delete: `evaluate/video_attributes.py`
- Delete: `evaluate/video_coherence.py`
- Delete: `evaluate/video_scorer.py`
- Delete: `tests/test_pipeline/test_image_evaluator.py`
- Delete: `tests/test_pipeline/test_coherence_checker.py`
- Delete: `tests/test_pipeline/test_image_scorer.py`
- Delete: any `tests/test_pipeline/test_video_*.py` that targeted only retired modules
- Modify (probably): `iterate/batch_processor.py` if any stale imports linger
- Modify (probably): `generate_video/*.py` if any stale imports linger

- [ ] **Step 1: Verify no live imports of the retired modules remain**

```
grep -rn "from evaluate.image_evaluator\|from evaluate.coherence_checker\|from evaluate.image_scorer\|from evaluate.video_evaluator\|from evaluate.video_attributes\|from evaluate.video_coherence\|from evaluate.video_scorer" --include="*.py" .
```

Expected: ZERO matches in production code (matches only inside tests that are about to be deleted). If anything remains in production, go back to PI-04 / PI-06 and finish the migration before this ticket.

- [ ] **Step 2: Delete the seven `evaluate/` modules and their tests**

```
git rm evaluate/image_evaluator.py evaluate/coherence_checker.py evaluate/image_scorer.py
git rm evaluate/video_evaluator.py evaluate/video_attributes.py evaluate/video_coherence.py evaluate/video_scorer.py
git rm tests/test_pipeline/test_image_evaluator.py tests/test_pipeline/test_coherence_checker.py tests/test_pipeline/test_image_scorer.py
git rm tests/test_pipeline/test_video_evaluator.py tests/test_pipeline/test_video_attributes.py tests/test_pipeline/test_video_coherence.py tests/test_pipeline/test_video_scorer.py 2>/dev/null || true
```

(Adjust the video test files based on what's actually in the tree.)

- [ ] **Step 3: Run the full test suite**

```
.venv/bin/python -m pytest tests/ --tb=line -q
```

Expected: all pass except the known PH-baseline failures (5 Clerk env-dep + 1 LLM flake). Any new failures point to a test file that still imports a retired module — fix or delete those imports.

- [ ] **Step 4: Run ruff**

```
.venv/bin/python -m ruff check .
```

Expected: clean.

- [ ] **Step 5: Run GitNexus impact + detect_changes** (per CLAUDE.md mandate)

```
npx gitnexus analyze
npx gitnexus detect_changes
```

Confirm: only the expected files in the expected scope.

- [ ] **Step 6: Commit**

```
git commit -m "chore(PI-10): retire 6 legacy evaluators + their tests"
```

---

# Ticket PI-11: Verification gate

**Goal:** End-to-end live run on a fresh staging session. Confirm the granularity target (≥ 8 distinct composites across 15 variants), the rationale UX, cost reconciliation, and ledger format compatibility on a real ledger.

**Files:**
- No code changes
- Modify: `docs/development/DEVLOG.md` — add a `PI-11` entry at the top with the verification results
- Create: `docs/development/PI-MANUAL-TEST-RUNBOOK.md` (similar to PH-MANUAL-TEST-RUNBOOK.md)

- [ ] **Step 1: Run lint + full pytest as the green baseline**

```
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest tests/ --tb=no -q
```

Record the pass/fail counts. Confirm no new regressions vs. PH baseline.

- [ ] **Step 2: Run a fresh image pipeline session**

```
.venv/bin/python run_pipeline.py --max-ads 5
```

Then read the resulting ledger:

```
.venv/bin/python - <<'PY'
import json, glob
latest = max(glob.glob('data/sessions/sess_*/ledger.jsonl'))
events = [json.loads(l) for l in open(latest)]
me = [e for e in events if e.get('event_type') == 'MediaEvaluation']
print(f'session: {latest}')
print(f'MediaEvaluation events: {len(me)} (expected 15 for 5 ads x 3 variants)')
composites = sorted({e['outputs']['composite_score'] for e in me})
print(f'distinct composites: {len(composites)} -> {composites}')
assert len(composites) >= 8, f'GRANULARITY TARGET MISSED: {len(composites)} < 8'
PY
```

Expected: assertion passes — ≥8 distinct composites.

- [ ] **Step 3: Run a fresh video pipeline session**

```
.venv/bin/python run_pipeline.py --max-ads 3 --session-type video
```

Check the resulting ledger has `MediaEvaluation` events with `media_type: "video"` and no `VideoEvaluated` / `VideoCoherenceChecked` / `VideoScored`.

- [ ] **Step 4: Open the dashboard locally and exercise the UI**

```
docker compose up -d
cd app/frontend && npm run dev
```

Sign in, navigate to the new session, open an ad in the Ad Library, expand a variant card, verify:
- 8 dimensions visible in the Evidence expander (10 for video)
- Each dimension has a non-generic rationale (no "good composition" placeholders)
- Winner card shows the "Why this won:" line
- Loser cards show "Lost on …" with worst-dim rationale

- [ ] **Step 5: Cost reconciliation**

```
.venv/bin/python - <<'PY'
from evaluate.cost_reporter import compute_session_cost_usd
from iterate.ledger_reader import LedgerReader
import glob
latest = max(glob.glob('data/sessions/sess_*/ledger.jsonl'))
reader = LedgerReader(latest)
total = compute_session_cost_usd(latest)
print(f'total: ${total:.4f}')
# Spot-check sum of MediaEvaluation tokens × Gemini 2.5 Flash rate
PY
```

Confirm: cost numbers are sane and the PH-02 CostAttributor still produces a clean breakdown.

- [ ] **Step 6: Calibration test re-run** (locks in granularity claim)

```
.venv/bin/python -m pytest tests/test_evaluation/test_media_quality_calibration.py -m calibration -v
```

Expected: PASS.

- [ ] **Step 7: Write the PI manual test runbook**

`docs/development/PI-MANUAL-TEST-RUNBOOK.md` — mirror the PH-MANUAL-TEST-RUNBOOK.md structure. Cover: dev-server smoke, image pipeline run, video pipeline run, dashboard variant-rationale visual check, calibration spread check, cost reconciliation. This is the document the next agent uses to verify a prod deploy is sound.

- [ ] **Step 8: Write the DEVLOG entry**

Append to the TOP of `docs/development/DEVLOG.md`:

```markdown
## 2026-XX-YY — PI-11: Phase verification gate (✅)

### Summary
End-to-end verification of PI-01..PI-10. Granularity target met; rubric
discriminates; rationales surfaced in UI; cost reconciles.

### Results
| Check | Result |
|---|---|
| ruff | clean |
| pytest | <N> passed / 6 baseline failures, zero PI regressions |
| Image pipeline run (5 ads × 3 variants) | <N> distinct composites across 15 variants (target ≥ 8) |
| Video pipeline run | <N> MediaEvaluation events with media_type='video' |
| Calibration test | PASS |
| Dashboard variant card | Evidence panel renders 8 dims with rationales |
| Cost reconciliation | ledger-attributed total within ±$0.01 of CostAttributor |

(...remaining sections per PH-07 template — scope shipped, branch state,
next steps, files changed.)
```

- [ ] **Step 9: Commit**

```
git add docs/development/DEVLOG.md docs/development/PI-MANUAL-TEST-RUNBOOK.md
git commit -m "docs(PI-11): phase verification gate — granularity target met"
```

- [ ] **Step 10: Merge to main + tag**

```
git checkout final-submission
git merge --no-ff feature/PI-XX  # (whatever branch the PI work lived on)
git tag pre-PI-deploy <prev-main-sha>
git checkout main && git merge --no-ff final-submission
git push origin main
```

(Adjust the branch name to match how the work was actually shipped.)

---

## Plan self-review

**Spec coverage check** — every section of `PI-00-phase-plan.md`:

| Spec section | Implementing ticket(s) |
|---|---|
| §4 Architecture (module layout) | PI-02, PI-03, PI-10 |
| §5 Rubric — shared/image-only/video-only dimensions | PI-02 (image), PI-05 (video) |
| §6 Penalty gates | PI-02 (image), PI-05 (video) |
| §7 Composite math | PI-02 (`compute_composite`) |
| §8 Ledger schema v2 | PI-01 (event classes), PI-04 + PI-06 (writes) |
| §9 Selection algorithm | PI-03 |
| §10 UI changes | PI-08 |
| §11 Calibration golden set | PI-09 |
| §12 Model selection (Gemini 2.5 Flash) | PI-02 (default), PI-09 (golden set runs against real API) |
| §13 Migration / rollout | PI-07 (v1 fallback), PI-11 (deploy step) |
| §14 Bonus fixes (placeholder code, missing-file, video unblock) | PI-06 (missing-file), PI-08 (video unblock), PI-10 (placeholder deletion) |
| §15 Test plan | PI-02, PI-03, PI-04, PI-05, PI-06, PI-07, PI-09 |

All sections accounted for.

**Placeholder scan** — no "TBD", no "add appropriate error handling", no unimplemented helpers. All code samples are complete enough to paste.

**Type consistency** — `DimensionScore`, `GateEvaluation`, `MediaEvaluationResult`, `WinnerReason`, `RejectionReason`, `SelectionResult` are defined exactly once each in PI-02 / PI-03 and referenced by the same names throughout PI-04, PI-06, PI-07, PI-08. `evaluate_media` signature and `select_best` signature stable across tickets.

**Scope check** — single phase, single subsystem, ~45h estimate, ships behind a verification gate. Right-sized for one implementation cycle.
