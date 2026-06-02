# PI-06 Primer

**Source plan:** [`PI-PLAN.md`](PI-PLAN.md) — sliced from the ticket section below.
**Phase plan:** [`PI-00-phase-plan.md`](PI-00-phase-plan.md)

**Status:** ⏳ Not started

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
