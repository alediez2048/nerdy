"""Tests for video Pareto selection + regen loop (P3-10).

Validates composite scoring, variant selection, regen diagnostics,
budget cap, and graceful degradation.
"""

from __future__ import annotations

from pathlib import Path

from evaluate.video_attributes import AttributeScore, VideoAttributeResult, VIDEO_ATTRIBUTES
from evaluate.video_coherence import CoherenceDimensionScore, VideoCoherenceResult
from generate_video.selector import compute_video_composite_score, select_best_video
from generate_video.regen import VideoDiagnostic, diagnose_video_failure, MAX_VIDEOS_PER_AD
from generate_video.degradation import DegradationResult, handle_video_failure


def _make_attr_result(all_pass: bool = True, pass_pct: float = 1.0) -> VideoAttributeResult:
    """Build a VideoAttributeResult."""
    scores = {}
    for a in VIDEO_ATTRIBUTES:
        scores[a["name"]] = AttributeScore(a["name"], all_pass, 0.9, "OK")
    return VideoAttributeResult("ad_001", "anchor", scores, all_pass, pass_pct, [])


def _make_coherence_result(
    scores: dict[str, float] | None = None,
) -> VideoCoherenceResult:
    """Build a VideoCoherenceResult."""
    default_scores = {
        "message_alignment": 7.0,
        "audience_match": 7.0,
        "emotional_consistency": 7.0,
        "narrative_flow": 7.0,
    }
    s = scores or default_scores
    dim_scores = {
        name: CoherenceDimensionScore(name, score, "OK")
        for name, score in s.items()
    }
    avg = sum(s.values()) / len(s)
    failing = [n for n, v in s.items() if v < 6.0]
    return VideoCoherenceResult("ad_001", "anchor", dim_scores, avg, len(failing) == 0, failing)


# --- Composite Score ---


def test_composite_score_weights() -> None:
    """Composite = attribute_pass_pct * 0.4 + coherence_avg * 0.6."""
    attr = _make_attr_result(pass_pct=0.8)
    coh = _make_coherence_result()  # avg = 7.0
    score = compute_video_composite_score(attr, coh)
    expected = 0.8 * 0.4 + 7.0 * 0.6  # 0.32 + 4.2 = 4.52
    assert abs(score - expected) < 0.01


def test_composite_score_perfect() -> None:
    """Perfect scores → high composite."""
    attr = _make_attr_result(pass_pct=1.0)
    coh = _make_coherence_result({
        "message_alignment": 10.0,
        "audience_match": 10.0,
        "emotional_consistency": 10.0,
        "narrative_flow": 10.0,
    })
    score = compute_video_composite_score(attr, coh)
    assert score > 6.0


# --- Variant Selection ---


def test_select_best_when_both_pass() -> None:
    """Selects variant with higher composite when both pass."""
    v1 = {"attr": _make_attr_result(pass_pct=0.8), "coh": _make_coherence_result()}
    v2 = {"attr": _make_attr_result(pass_pct=1.0), "coh": _make_coherence_result({
        "message_alignment": 9.0, "audience_match": 8.0,
        "emotional_consistency": 8.0, "narrative_flow": 8.0,
    })}
    variants = [("anchor", v1), ("alternative", v2)]
    winner = select_best_video(variants)
    assert winner == "alternative"


def test_select_best_when_one_passes() -> None:
    """Selects the only passing variant."""
    v1 = {"attr": _make_attr_result(all_pass=False, pass_pct=0.5), "coh": _make_coherence_result()}
    v2 = {"attr": _make_attr_result(pass_pct=1.0), "coh": _make_coherence_result()}
    variants = [("anchor", v1), ("alternative", v2)]
    winner = select_best_video(variants)
    assert winner == "alternative"


def test_select_best_none_when_all_fail() -> None:
    """Returns None when no variant passes."""
    v1 = {"attr": _make_attr_result(all_pass=False, pass_pct=0.3), "coh": _make_coherence_result()}
    variants = [("anchor", v1)]
    winner = select_best_video(variants)
    assert winner is None


# --- Regen Diagnostics ---


def test_diagnose_failure_identifies_weakest() -> None:
    """diagnose_video_failure identifies weakest attribute or dimension."""
    attr = _make_attr_result(all_pass=False, pass_pct=0.7)
    attr.attribute_scores["hook_timing"] = AttributeScore("hook_timing", False, 0.5, "Hook too late")
    coh = _make_coherence_result({"message_alignment": 4.0, "audience_match": 7.0,
                                   "emotional_consistency": 7.0, "narrative_flow": 7.0})
    diag = diagnose_video_failure(attr, coh)
    assert isinstance(diag, VideoDiagnostic)
    assert len(diag.failed_attributes) > 0 or len(diag.failed_dimensions) > 0


def test_budget_cap_defined() -> None:
    """Max videos per ad is 3 (2 initial + 1 regen)."""
    assert MAX_VIDEOS_PER_AD == 3


# --- Graceful Degradation ---


def test_graceful_degradation_result(tmp_path: Path) -> None:
    """handle_video_failure returns DegradationResult with image-only fallback."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    result = handle_video_failure("ad_001", ledger_path=ledger_path)
    assert isinstance(result, DegradationResult)
    assert result.fallback == "image-only"
    assert result.ad_id == "ad_001"


def test_degradation_logs_to_ledger(tmp_path: Path) -> None:
    """handle_video_failure logs video-blocked event."""
    import json

    ledger_path = str(tmp_path / "ledger.jsonl")
    handle_video_failure("ad_001", ledger_path=ledger_path)

    events = [json.loads(line) for line in Path(ledger_path).read_text().strip().split("\n")]
    blocked = [e for e in events if e["event_type"] == "VideoBlocked"]
    assert len(blocked) == 1
    assert blocked[0]["outputs"]["fallback"] == "image-only"
