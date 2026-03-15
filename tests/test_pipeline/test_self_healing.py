"""Tests for self-healing feedback loop (P4-02).

Validates SPC drift detection, brief mutation integration, quality ratchet,
and the self-healing orchestrator.
"""

from __future__ import annotations

from pathlib import Path

from iterate.ledger import log_event
from iterate.spc import SPCResult, check_spc, detect_quality_drift
from iterate.brief_mutation import MutationDiagnosis, diagnose_weakness, mutate_brief
from iterate.quality_ratchet import (
    RatchetState,
    compute_threshold,
    get_ratchet_state,
    update_ratchet,
)
from iterate.self_healing import HealingAction, run_healing_check


# --- SPC Drift Detection ---


def test_spc_in_control() -> None:
    """Stable scores should be in control."""
    scores = [7.2, 7.1, 7.3, 7.0, 7.2, 7.0, 7.3, 7.1, 7.2, 7.1]
    result = check_spc(scores)
    assert isinstance(result, SPCResult)
    assert result.in_control is True
    assert len(result.violations) == 0


def test_spc_detects_mean_shift() -> None:
    """3+ consecutive points below mean triggers violation."""
    scores = [7.5, 7.4, 7.3, 5.0, 5.1, 5.2, 5.0, 7.3, 7.2, 7.1]
    result = check_spc(scores)
    assert result.in_control is False
    assert any("mean_shift" in v or "below" in v.lower() or "outlier" in v.lower() for v in result.violations)


def test_spc_detects_outlier() -> None:
    """Single point outside ±2σ triggers violation."""
    scores = [7.0, 7.1, 7.0, 7.1, 7.0, 7.1, 7.0, 7.1, 7.0, 2.0]
    result = check_spc(scores)
    assert result.in_control is False


def test_spc_from_ledger(tmp_path: Path) -> None:
    """detect_quality_drift reads batch scores from ledger."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    for i in range(10):
        log_event(ledger_path, {
            "event_type": "BatchCompleted",
            "ad_id": f"batch_{i}",
            "brief_id": f"batch_{i}",
            "cycle_number": 0,
            "action": "batch-complete",
            "tokens_consumed": 0,
            "model_used": "none",
            "seed": "0",
            "inputs": {"batch_num": i},
            "outputs": {"batch_average": 7.0 + (i % 3) * 0.1},
        })
    result = detect_quality_drift(ledger_path)
    assert isinstance(result, SPCResult)


# --- Brief Mutation (existing P1-08 interface) ---


def test_diagnose_weakness_identifies_lowest() -> None:
    """diagnose_weakness picks the weakest dimension."""
    scores = {
        "clarity": {"score": 7.5, "rationale": "Clear"},
        "value_proposition": {"score": 5.2, "rationale": "Weak VP"},
        "cta": {"score": 6.8, "rationale": "OK CTA"},
        "brand_voice": {"score": 7.0, "rationale": "Good voice"},
        "emotional_resonance": {"score": 6.5, "rationale": "Moderate"},
    }
    diagnosis = diagnose_weakness("ad_001", scores)
    assert isinstance(diagnosis, MutationDiagnosis)
    assert diagnosis.weakest_dimension == "value_proposition"


def test_mutate_brief_changes_brief() -> None:
    """mutate_brief returns a modified brief with mutation metadata."""
    brief = {"brief_id": "b001", "campaign_goal": "awareness", "audience": "parents"}
    scores = {
        "clarity": {"score": 7.5},
        "value_proposition": {"score": 5.2},
        "cta": {"score": 6.8},
        "brand_voice": {"score": 7.0},
        "emotional_resonance": {"score": 6.5},
    }
    diagnosis = diagnose_weakness("ad_001", scores)
    mutated = mutate_brief(brief, diagnosis)
    assert "mutation" in mutated
    assert mutated["mutation"]["target_dimension"] == "value_proposition"


# --- Quality Ratchet (existing P1-10 interface) ---


def test_ratchet_floor_minimum() -> None:
    """Ratchet threshold never goes below 7.0."""
    config = {"quality_threshold": 7.0, "ratchet_window": 5, "ratchet_buffer": 0.5}
    threshold = compute_threshold([5.0, 5.0, 5.0, 5.0, 5.0], config)
    assert threshold >= 7.0


def test_ratchet_goes_up() -> None:
    """Ratchet increases when rolling average is high."""
    config = {"quality_threshold": 7.0, "ratchet_window": 5, "ratchet_buffer": 0.5}
    threshold = compute_threshold([8.5, 8.5, 8.5, 8.5, 8.5], config)
    assert threshold == 8.0  # max(7.0, 8.5 - 0.5)


def test_ratchet_monotonic() -> None:
    """Ratchet never decreases with update_ratchet."""
    config = {"quality_threshold": 7.0, "ratchet_window": 5, "ratchet_buffer": 0.5}
    state = RatchetState(
        current_threshold=8.0,
        base_threshold=7.0,
        rolling_average=8.5,
        window_scores=[8.5, 8.5, 8.5, 8.5, 8.5],
    )
    # Feed low scores — threshold should not drop
    new_state = update_ratchet(state, 5.0, config)
    assert new_state.current_threshold >= 8.0


def test_ratchet_from_ledger(tmp_path: Path) -> None:
    """get_ratchet_state reconstructs from ledger."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    for i in range(5):
        log_event(ledger_path, {
            "event_type": "BatchCompleted",
            "ad_id": f"batch_{i}",
            "brief_id": f"batch_{i}",
            "cycle_number": 0,
            "action": "batch-complete",
            "tokens_consumed": 0,
            "model_used": "none",
            "seed": "0",
            "inputs": {"batch_num": i},
            "outputs": {"batch_average": 8.5},
        })
    config = {"quality_threshold": 7.0, "ratchet_window": 5, "ratchet_buffer": 0.5}
    state = get_ratchet_state(ledger_path, config)
    assert isinstance(state, RatchetState)
    assert state.current_threshold >= 7.0


# --- Self-Healing Orchestrator ---


def test_healing_check_no_drift(tmp_path: Path) -> None:
    """No healing needed when quality is stable."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    for i in range(10):
        log_event(ledger_path, {
            "event_type": "BatchCompleted",
            "ad_id": f"batch_{i}",
            "brief_id": f"batch_{i}",
            "cycle_number": 0,
            "action": "batch-complete",
            "tokens_consumed": 0,
            "model_used": "none",
            "seed": "0",
            "inputs": {"batch_num": i},
            "outputs": {"batch_average": 7.5},
        })
    result = run_healing_check(ledger_path, config={})
    assert result is None  # No healing needed


def test_healing_check_drift_detected(tmp_path: Path) -> None:
    """Healing triggers when quality drops."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    # Good scores then sudden drop
    for i in range(7):
        log_event(ledger_path, {
            "event_type": "BatchCompleted",
            "ad_id": f"batch_{i}",
            "brief_id": f"batch_{i}",
            "cycle_number": 0,
            "action": "batch-complete",
            "tokens_consumed": 0,
            "model_used": "none",
            "seed": "0",
            "inputs": {"batch_num": i},
            "outputs": {"batch_average": 7.5},
        })
    for i in range(7, 11):
        log_event(ledger_path, {
            "event_type": "BatchCompleted",
            "ad_id": f"batch_{i}",
            "brief_id": f"batch_{i}",
            "cycle_number": 0,
            "action": "batch-complete",
            "tokens_consumed": 0,
            "model_used": "none",
            "seed": "0",
            "inputs": {"batch_num": i},
            "outputs": {"batch_average": 4.0},
        })
    result = run_healing_check(ledger_path, config={})
    assert isinstance(result, HealingAction)
    assert result.trigger is not None
