# PI-02 Primer

**Source plan:** [`PI-PLAN.md`](PI-PLAN.md) — sliced from the ticket section below.
**Phase plan:** [`PI-00-phase-plan.md`](PI-00-phase-plan.md)

**Status:** ✅ Merged on `final-submission`

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
