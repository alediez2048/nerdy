"""PI-04: image batch processing emits MediaEvaluation events."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_generate_and_select_image_writes_media_evaluation_events(tmp_path):
    """One MediaEvaluation per variant; no ImageEvaluated / ImageScored."""
    from evaluate.media_quality import (
        DimensionScore,
        GateEvaluation,
        IMAGE_DIMENSIONS,
        MediaEvaluationResult,
    )
    from iterate.batch_processor import _generate_and_select_image

    ledger = tmp_path / "ledger.jsonl"
    fake_ad = MagicMock(
        ad_id="ad_X",
        headline="h",
        primary_text="b",
        cta_button="c",
    )
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
            ad_id=ad_id,
            variant_type=variant_type,
            media_type="image",
            media_path=str(media_path),
            model_used="gemini-2.5-flash",
            tokens_consumed=1500,
            dimensions=dims,
            penalty_gates=gates,
            raw_score=score / 10.0,
            penalty_multiplier=1.0,
            composite_score=score * 10.0,
        )

    fake_variants = []
    for i, v in enumerate(("anchor", "tone_shift", "composition_shift")):
        path = tmp_path / f"ad_X_{v}.png"
        path.write_bytes(b"x")
        fake_variants.append(
            MagicMock(
                image_path=str(path),
                seed=i,
                variant_type=v,
                tokens_consumed=0,
                model_used="gemini-image",
            )
        )

    with patch("iterate.batch_processor.generate_variants", return_value=fake_variants):
        with patch("iterate.batch_processor.evaluate_media", side_effect=_fake_eval):
            with patch(
                "iterate.batch_processor.extract_visual_spec",
                return_value=MagicMock(subject="s", setting="t", spec_extraction_tokens=0),
            ):
                winner = _generate_and_select_image(
                    ad=fake_ad,
                    expanded_brief={"brief_id": "brief_001"},
                    brief=fake_brief,
                    brief_seed=42,
                    ledger_path=str(ledger),
                )

    assert winner is not None and "anchor" in winner  # anchor scored 8 → highest
    events = [json.loads(line) for line in ledger.read_text().splitlines()]
    types = [e["event_type"] for e in events]
    assert types.count("MediaEvaluation") == 3, types
    assert "ImageEvaluated" not in types
    assert "ImageScored" not in types
