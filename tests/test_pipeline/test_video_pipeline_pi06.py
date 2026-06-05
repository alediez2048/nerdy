"""PI-06: video pipeline emits MediaEvaluation events."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from evaluate.media_quality import (
    DimensionScore,
    GateEvaluation,
    MediaEvaluationResult,
    VIDEO_DIMENSIONS,
)


def _fake_video_eval(media_path, ad_copy, ad_id, variant_type, media_type="video", **kw):
    score = {"anchor": 7, "alternative": 5}.get(variant_type, 6)
    dims = {
        d["name"]: DimensionScore(score=score, weight=d["weight"], rationale="r")
        for d in VIDEO_DIMENSIONS
    }
    gates = {
        g: GateEvaluation(False, "ok")
        for g in (
            "has_ai_artifacts",
            "has_uncanny_faces",
            "brand_safety_violation",
            "has_temporal_artifacts",
            "has_pacing_dead_zones",
        )
    }
    return MediaEvaluationResult(
        ad_id=ad_id,
        variant_type=variant_type,
        media_type="video",
        media_path=str(media_path),
        model_used="gemini-2.5-flash",
        tokens_consumed=3000,
        dimensions=dims,
        penalty_gates=gates,
        raw_score=score / 10.0,
        penalty_multiplier=1.0,
        composite_score=score * 10.0,
    )


def test_video_orchestrator_writes_media_evaluation_events(tmp_path):
    """One MediaEvaluation per variant; no legacy VideoEvaluated."""
    from generate_video.orchestrator import score_and_select_video_variants

    ledger = tmp_path / "ledger.jsonl"
    fake_ad = MagicMock(
        ad_id="ad_X",
        headline="h",
        primary_text="b",
        cta_button="c",
    )
    variants = []
    for i, name in enumerate(("anchor", "alternative")):
        p = tmp_path / f"{name}.mp4"
        p.write_bytes(b"x")
        variants.append(MagicMock(video_path=str(p), variant_type=name, seed=i))

    with patch("generate_video.orchestrator.evaluate_media", side_effect=_fake_video_eval):
        winner = score_and_select_video_variants(
            ad=fake_ad,
            variants=variants,
            brief={"brief_id": "brief_001"},
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
    fake_ad = MagicMock(
        ad_id="ad_Y",
        headline="h",
        primary_text="b",
        cta_button="c",
    )
    bad = MagicMock(
        video_path=str(tmp_path / "missing.mp4"),
        variant_type="anchor",
        seed=0,
    )
    winner = score_and_select_video_variants(
        ad=fake_ad,
        variants=[bad],
        brief={"brief_id": "brief_001"},
        ledger_path=str(ledger),
    )
    assert winner is None
    events = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert events[0]["event_type"] == "MediaEvaluationFailed"
    assert events[0]["outputs"]["failure_reason"] == "file_not_found"
