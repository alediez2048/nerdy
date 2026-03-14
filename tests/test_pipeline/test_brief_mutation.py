"""Tests for brief mutation + escalation (P1-08)."""

from __future__ import annotations

import json

import pytest

from iterate.brief_mutation import (
    EscalationReport,
    MutationDiagnosis,
    diagnose_weakness,
    escalate,
    mutate_brief,
    should_escalate,
)

DIMS = ("clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance")


def _make_scores(
    clarity: float = 7.0,
    value_proposition: float = 7.0,
    cta: float = 7.0,
    brand_voice: float = 7.0,
    emotional_resonance: float = 7.0,
) -> dict[str, dict]:
    """Build a scores dict matching EvaluationResult.scores format."""
    vals = {
        "clarity": clarity,
        "value_proposition": value_proposition,
        "cta": cta,
        "brand_voice": brand_voice,
        "emotional_resonance": emotional_resonance,
    }
    return {
        d: {"score": v, "rationale": f"{d} rationale", "contrastive": f"{d} contrastive"}
        for d, v in vals.items()
    }


def _make_config(max_cycles: int = 3) -> dict:
    return {"max_regeneration_cycles": max_cycles, "ledger_path": "data/ledger.jsonl"}


# --- diagnose_weakness Tests ---


def test_diagnose_weakness_identifies_lowest_dimension() -> None:
    """diagnose_weakness picks the lowest-scoring dimension."""
    scores = _make_scores(clarity=5.0, cta=8.0, brand_voice=7.0)
    diagnosis = diagnose_weakness("ad_001", scores)
    assert diagnosis.weakest_dimension == "clarity"
    assert diagnosis.score == 5.0


def test_diagnose_weakness_maps_clarity_to_mutation() -> None:
    """Clarity weakness maps to simplification mutation."""
    scores = _make_scores(clarity=4.0)
    diagnosis = diagnose_weakness("ad_002", scores)
    assert diagnosis.weakest_dimension == "clarity"
    assert len(diagnosis.suggested_mutation) > 10


def test_diagnose_weakness_maps_cta_to_mutation() -> None:
    """CTA weakness maps to urgency/specificity mutation."""
    scores = _make_scores(cta=3.0)
    diagnosis = diagnose_weakness("ad_003", scores)
    assert diagnosis.weakest_dimension == "cta"
    assert len(diagnosis.suggested_mutation) > 10


def test_diagnose_weakness_maps_each_dimension() -> None:
    """Every dimension has a concrete mutation strategy."""
    for dim in DIMS:
        kwargs = {d: 8.0 for d in DIMS}
        kwargs[dim] = 3.0
        scores = _make_scores(**kwargs)
        diagnosis = diagnose_weakness("ad_test", scores)
        assert diagnosis.weakest_dimension == dim
        assert isinstance(diagnosis.suggested_mutation, str)
        assert len(diagnosis.suggested_mutation) > 10


# --- mutate_brief Tests ---


def test_mutate_brief_preserves_original_fields() -> None:
    """Mutated brief keeps all original fields intact."""
    original = {
        "brief_id": "b001",
        "audience": "parents",
        "campaign_goal": "conversion",
        "product": "SAT prep",
    }
    scores = _make_scores(cta=3.0)
    diagnosis = diagnose_weakness("ad_004", scores)
    mutated = mutate_brief(original, diagnosis)

    assert mutated["brief_id"] == "b001"
    assert mutated["audience"] == "parents"
    assert mutated["campaign_goal"] == "conversion"
    assert mutated["product"] == "SAT prep"


def test_mutate_brief_adds_mutation_context() -> None:
    """Mutated brief includes mutation metadata."""
    original = {"brief_id": "b002", "audience": "parents"}
    scores = _make_scores(brand_voice=4.0)
    diagnosis = diagnose_weakness("ad_005", scores)
    mutated = mutate_brief(original, diagnosis)

    assert "mutation" in mutated
    assert mutated["mutation"]["target_dimension"] == "brand_voice"
    assert isinstance(mutated["mutation"]["guidance"], str)


def test_mutate_brief_logs_event(tmp_path: pytest.TempPathFactory) -> None:
    """mutate_brief logs a BriefMutated event to the ledger."""
    ledger = str(tmp_path / "ledger.jsonl")
    original = {"brief_id": "b003", "audience": "students"}
    scores = _make_scores(emotional_resonance=3.5)
    diagnosis = diagnose_weakness("ad_006", scores)
    mutate_brief(original, diagnosis, ledger_path=ledger)

    with open(ledger) as f:
        events = [json.loads(line) for line in f]

    assert len(events) == 1
    assert events[0]["event_type"] == "BriefMutated"
    assert events[0]["ad_id"] == "ad_006"


# --- should_escalate Tests ---


def test_should_escalate_false_on_early_cycles() -> None:
    """Cycles 1 and 2 should not trigger escalation with default config."""
    config = _make_config(max_cycles=3)
    assert should_escalate(cycle=1, config=config) is False
    assert should_escalate(cycle=2, config=config) is False


def test_should_escalate_true_on_max_cycle() -> None:
    """Cycle 3 (default max) should trigger escalation."""
    config = _make_config(max_cycles=3)
    assert should_escalate(cycle=3, config=config) is True


def test_should_escalate_respects_custom_config() -> None:
    """Custom max_regeneration_cycles is respected."""
    config = _make_config(max_cycles=5)
    assert should_escalate(cycle=4, config=config) is False
    assert should_escalate(cycle=5, config=config) is True


# --- escalate Tests ---


def test_escalate_produces_complete_report() -> None:
    """Escalation report includes all attempts, diagnosis, and reason."""
    scores = _make_scores(clarity=4.0)
    diagnosis = diagnose_weakness("ad_007", scores)
    attempts = [
        {"cycle": 1, "scores": {d: 5.0 for d in DIMS}},
        {"cycle": 2, "scores": {d: 4.5 for d in DIMS}},
        {"cycle": 3, "scores": {d: 4.0 for d in DIMS}},
    ]
    report = escalate("ad_007", attempts, diagnosis)

    assert isinstance(report, EscalationReport)
    assert report.ad_id == "ad_007"
    assert len(report.attempts) == 3
    assert report.diagnosis.weakest_dimension == "clarity"
    assert isinstance(report.reason_for_escalation, str)
    assert len(report.reason_for_escalation) > 10


def test_escalate_logs_event(tmp_path: pytest.TempPathFactory) -> None:
    """Escalation logs an AdEscalated event to the ledger."""
    ledger = str(tmp_path / "ledger.jsonl")
    scores = _make_scores(value_proposition=3.0)
    diagnosis = diagnose_weakness("ad_008", scores)
    attempts = [{"cycle": 1, "scores": {d: 5.0 for d in DIMS}}]
    escalate("ad_008", attempts, diagnosis, ledger_path=ledger)

    with open(ledger) as f:
        events = [json.loads(line) for line in f]

    assert len(events) == 1
    assert events[0]["event_type"] == "AdEscalated"
    assert events[0]["ad_id"] == "ad_008"
    assert events[0]["action"] == "escalation"
