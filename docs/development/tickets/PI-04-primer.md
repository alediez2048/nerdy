# PI-04 Primer

**Source plan:** [`PI-PLAN.md`](PI-PLAN.md) — sliced from the ticket section below.
**Phase plan:** [`PI-00-phase-plan.md`](PI-00-phase-plan.md)

**Status:** ⏳ Not started

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
