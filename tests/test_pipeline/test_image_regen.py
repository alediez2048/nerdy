"""Tests for image targeted regen loop (P1-17)."""

from __future__ import annotations

from evaluate.coherence_checker import CoherenceResult, COHERENCE_DIMENSIONS
from evaluate.image_evaluator import ImageAttributeResult, VISUAL_ATTRIBUTES
from iterate.image_regen import (
    RegenDiagnostic,
    diagnose_failure,
    build_regen_spec,
    get_image_count,
    can_generate_more,
    run_image_regen,
    flag_image_blocked,
)


def _make_attr_result(
    fails: list[str] | None = None,
    variant_type: str = "anchor",
) -> ImageAttributeResult:
    """Build an ImageAttributeResult with specified failing attributes."""
    attrs = {a: True for a in VISUAL_ATTRIBUTES}
    for f in (fails or []):
        attrs[f] = True  # default
        if f in attrs:
            attrs[f] = False
    pass_count = sum(attrs.values())
    pass_pct = pass_count / len(VISUAL_ATTRIBUTES)
    return ImageAttributeResult(
        ad_id="ad_001",
        variant_type=variant_type,
        attributes=attrs,
        attribute_pass_pct=round(pass_pct, 2),
        meets_threshold=pass_pct >= 0.8,
    )


def _make_coherence_result(
    scores: dict[str, float] | None = None,
    variant_type: str = "anchor",
) -> CoherenceResult:
    """Build a CoherenceResult with given dimension scores."""
    if scores is None:
        scores = {d: 8.0 for d in COHERENCE_DIMENSIONS}
    avg = sum(scores.values()) / len(scores)
    return CoherenceResult(
        ad_id="ad_001",
        variant_type=variant_type,
        dimension_scores=scores,
        coherence_avg=round(avg, 2),
    )


# --- Failure Diagnosis ---


def test_diagnose_identifies_most_common_failed_attribute() -> None:
    """When all variants fail attributes, identifies the most common failure."""
    attr_results = [
        _make_attr_result(["no_artifacts", "lighting"], "anchor"),
        _make_attr_result(["no_artifacts", "diversity"], "tone_shift"),
        _make_attr_result(["no_artifacts"], "composition_shift"),
    ]
    coherence_results = [
        _make_coherence_result(variant_type="anchor"),
        _make_coherence_result(variant_type="tone_shift"),
        _make_coherence_result(variant_type="composition_shift"),
    ]
    diag = diagnose_failure(attr_results, coherence_results)
    assert diag.failure_type == "attribute"
    assert diag.weakest_dimension == "no_artifacts"
    assert diag.fix_suggestion


def test_diagnose_identifies_weakest_coherence_dimension() -> None:
    """When coherence is the issue, identifies the weakest dimension."""
    attr_results = [
        _make_attr_result(variant_type="anchor"),  # all pass
    ]
    coherence_results = [
        _make_coherence_result(
            {
                "message_alignment": 4.0,
                "audience_match": 7.0,
                "emotional_consistency": 7.0,
                "visual_narrative": 7.0,
            },
            variant_type="anchor",
        ),
    ]
    diag = diagnose_failure(attr_results, coherence_results)
    assert diag.failure_type == "coherence"
    assert diag.weakest_dimension == "message_alignment"
    assert diag.fix_suggestion


# --- Regen Spec Building ---


def test_regen_spec_includes_fix_suggestion() -> None:
    """Regen spec appends diagnostic fix suggestion to original spec."""
    original_spec = {"subject": "Student studying", "setting": "Library"}
    diag = RegenDiagnostic(
        failure_type="attribute",
        weakest_dimension="no_artifacts",
        fix_suggestion="Ensure no distorted faces, extra fingers, or warped text",
    )
    new_spec = build_regen_spec(original_spec, diag)
    assert "regen_guidance" in new_spec
    assert "no_artifacts" in new_spec["regen_guidance"].lower() or "distort" in new_spec["regen_guidance"].lower()
    # Original fields preserved
    assert new_spec["subject"] == "Student studying"


# --- Budget Tracking ---


def test_get_image_count_from_ledger(tmp_path: object) -> None:
    """Counts images generated for an ad from ledger events."""
    ledger_path = str(tmp_path / "ledger.jsonl")  # type: ignore[operator]
    from iterate.ledger import log_event

    for i in range(3):
        log_event(
            ledger_path,
            {
                "event_type": "ImageGenerated",
                "ad_id": "ad_001",
                "brief_id": "b001",
                "cycle_number": 1,
                "action": "image-generation",
                "inputs": {},
                "outputs": {"variant_type": f"variant_{i}"},
                "scores": {},
                "tokens_consumed": 0,
                "model_used": "gemini-2.0-flash",
                "seed": "42",
            },
        )
    assert get_image_count("ad_001", ledger_path) == 3


def test_can_generate_more_within_budget(tmp_path: object) -> None:
    """Returns True when under budget."""
    ledger_path = str(tmp_path / "ledger.jsonl")  # type: ignore[operator]
    from iterate.ledger import log_event

    for i in range(3):
        log_event(
            ledger_path,
            {
                "event_type": "ImageGenerated",
                "ad_id": "ad_001",
                "brief_id": "b001",
                "cycle_number": 1,
                "action": "image-generation",
                "inputs": {},
                "outputs": {},
                "scores": {},
                "tokens_consumed": 0,
                "model_used": "gemini-2.0-flash",
                "seed": "42",
            },
        )
    assert can_generate_more("ad_001", ledger_path, requested=2) is True


def test_can_generate_more_over_budget(tmp_path: object) -> None:
    """Returns False when at or over budget."""
    ledger_path = str(tmp_path / "ledger.jsonl")  # type: ignore[operator]
    from iterate.ledger import log_event

    for i in range(5):
        log_event(
            ledger_path,
            {
                "event_type": "ImageGenerated",
                "ad_id": "ad_001",
                "brief_id": "b001",
                "cycle_number": 1,
                "action": "image-generation",
                "inputs": {},
                "outputs": {},
                "scores": {},
                "tokens_consumed": 0,
                "model_used": "gemini-2.0-flash",
                "seed": "42",
            },
        )
    assert can_generate_more("ad_001", ledger_path, requested=1) is False


# --- Regen Loop ---


def test_regen_generates_two_on_attribute_failure() -> None:
    """Full attribute failure triggers 2 regen variants."""
    diag = RegenDiagnostic(
        failure_type="attribute",
        weakest_dimension="no_artifacts",
        fix_suggestion="Fix artifacts",
    )
    result = run_image_regen(
        ad_id="ad_001",
        diagnostic=diag,
        current_image_count=3,
    )
    assert result.regen_count == 2


def test_regen_generates_one_on_coherence_failure() -> None:
    """Coherence-only failure triggers 1 regen variant."""
    diag = RegenDiagnostic(
        failure_type="coherence",
        weakest_dimension="message_alignment",
        fix_suggestion="Image must show value proposition",
    )
    result = run_image_regen(
        ad_id="ad_001",
        diagnostic=diag,
        current_image_count=3,
    )
    assert result.regen_count == 1


def test_regen_capped_at_budget() -> None:
    """Regen count is reduced when near budget limit."""
    diag = RegenDiagnostic(
        failure_type="attribute",
        weakest_dimension="no_artifacts",
        fix_suggestion="Fix artifacts",
    )
    # 4 already generated, budget is 5, so max 1 more
    result = run_image_regen(
        ad_id="ad_001",
        diagnostic=diag,
        current_image_count=4,
    )
    assert result.regen_count == 1


def test_regen_blocked_at_budget() -> None:
    """No regen when budget is exhausted."""
    diag = RegenDiagnostic(
        failure_type="attribute",
        weakest_dimension="no_artifacts",
        fix_suggestion="Fix artifacts",
    )
    result = run_image_regen(
        ad_id="ad_001",
        diagnostic=diag,
        current_image_count=5,
    )
    assert result.regen_count == 0
    assert result.blocked is True


# --- Image Blocked ---


def test_flag_image_blocked_logs_event(tmp_path: object) -> None:
    """Image-blocked flag appends ImageBlocked event to ledger."""
    ledger_path = str(tmp_path / "ledger.jsonl")  # type: ignore[operator]
    diag = RegenDiagnostic(
        failure_type="attribute",
        weakest_dimension="no_artifacts",
        fix_suggestion="Fix artifacts",
    )
    flag_image_blocked("ad_001", diag, ledger_path)

    from iterate.ledger import read_events_filtered
    events = read_events_filtered(ledger_path, event_type="ImageBlocked")
    assert len(events) == 1
    assert events[0]["ad_id"] == "ad_001"
    assert "no_artifacts" in str(events[0]["outputs"])
