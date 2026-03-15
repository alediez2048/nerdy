"""Tests for SPC drift detection + canary injection (P2-04)."""

from __future__ import annotations

from pathlib import Path

from evaluate.spc_monitor import (
    ControlChartData,
    ControlLimits,
    DriftDiagnosis,
    DriftReport,
    compute_control_limits,
    detect_drift,
    diagnose_drift,
    get_control_chart_data,
    inject_canary,
    is_in_control,
)


# --- Control Limits ---


def test_control_limits_calculation() -> None:
    """Known data produces correct mean, UCL, LCL."""
    # 5 batches with known averages
    batch_avgs = [7.0, 7.2, 6.8, 7.1, 6.9]
    limits = compute_control_limits(batch_avgs)
    assert isinstance(limits, ControlLimits)
    # mean = 7.0
    assert abs(limits.mean - 7.0) < 0.01
    assert limits.sigma > 0
    assert limits.ucl > limits.mean
    assert limits.lcl < limits.mean
    assert abs(limits.ucl - (limits.mean + 2 * limits.sigma)) < 0.01
    assert abs(limits.lcl - (limits.mean - 2 * limits.sigma)) < 0.01


def test_in_control_within_limits() -> None:
    """Score between UCL and LCL returns True."""
    limits = ControlLimits(mean=7.0, ucl=7.4, lcl=6.6, sigma=0.2)
    assert is_in_control(7.0, limits) is True
    assert is_in_control(7.3, limits) is True
    assert is_in_control(6.7, limits) is True


def test_out_of_control_above_ucl() -> None:
    """Score above UCL returns False."""
    limits = ControlLimits(mean=7.0, ucl=7.4, lcl=6.6, sigma=0.2)
    assert is_in_control(7.5, limits) is False


def test_out_of_control_below_lcl() -> None:
    """Score below LCL returns False."""
    limits = ControlLimits(mean=7.0, ucl=7.4, lcl=6.6, sigma=0.2)
    assert is_in_control(6.5, limits) is False


def test_insufficient_data_returns_no_limits() -> None:
    """Fewer than 5 batches returns None (cannot establish limits)."""
    limits = compute_control_limits([7.0, 7.1, 6.9])
    assert limits is None


# --- Drift Detection ---


def test_drift_report_stable_data(tmp_path: Path) -> None:
    """All batches within limits produces no breaches."""
    from iterate.ledger import log_event

    ledger_path = str(tmp_path / "ledger.jsonl")
    # Log 7 stable batches
    for i in range(7):
        log_event(ledger_path, {
            "event_type": "BatchCompleted",
            "ad_id": f"batch_{i}",
            "brief_id": "b001",
            "cycle_number": 1,
            "action": "batch-complete",
            "inputs": {},
            "outputs": {"batch_avg_score": 7.0 + (i % 3) * 0.1},
            "scores": {},
            "tokens_consumed": 0,
            "model_used": "gemini-2.0-flash",
            "seed": "42",
        })

    report = detect_drift(ledger_path)
    assert isinstance(report, DriftReport)
    assert len(report.breaches) == 0
    assert report.is_stable is True


def test_drift_report_detects_shift(tmp_path: Path) -> None:
    """Batch 3σ above mean is detected as breach."""
    from iterate.ledger import log_event

    ledger_path = str(tmp_path / "ledger.jsonl")
    # 5 stable batches for baseline
    for i in range(5):
        log_event(ledger_path, {
            "event_type": "BatchCompleted",
            "ad_id": f"batch_{i}",
            "brief_id": "b001",
            "cycle_number": 1,
            "action": "batch-complete",
            "inputs": {},
            "outputs": {"batch_avg_score": 7.0},
            "scores": {},
            "tokens_consumed": 0,
            "model_used": "gemini-2.0-flash",
            "seed": "42",
        })
    # 1 anomalous batch
    log_event(ledger_path, {
        "event_type": "BatchCompleted",
        "ad_id": "batch_anomaly",
        "brief_id": "b001",
        "cycle_number": 1,
        "action": "batch-complete",
        "inputs": {},
        "outputs": {"batch_avg_score": 9.5},
        "scores": {},
        "tokens_consumed": 0,
        "model_used": "gemini-2.0-flash",
        "seed": "42",
    })

    report = detect_drift(ledger_path)
    assert report.is_stable is False
    assert len(report.breaches) >= 1
    assert report.breaches[0]["direction"] == "high"


# --- Canary Injection ---


def test_canary_injection_selects_diverse() -> None:
    """Canary injection returns 1 excellent, 1 good, 1 poor."""
    golden_path = str(
        Path(__file__).resolve().parents[1] / "test_data" / "golden_ads.json"
    )
    canaries = inject_canary(golden_path, count=3)
    assert len(canaries) == 3
    labels = {c["quality_label"] for c in canaries}
    assert "excellent" in labels
    assert "good" in labels
    assert "poor" in labels


# --- Drift Diagnosis ---


def test_diagnose_drift_evaluator_stable() -> None:
    """Canary scores matching humans means evaluator is stable."""
    canary_results = [
        {"ad_id": "ref_vt_01", "quality_label": "excellent",
         "scores": {"clarity": 8.0, "value_proposition": 8.0, "cta": 7.0,
                    "brand_voice": 7.0, "emotional_resonance": 7.0}},
    ]
    golden_scores = [
        {"ad_id": "ref_vt_01", "quality_label": "excellent",
         "human_scores": {"clarity": 8.4, "value_proposition": 8.4, "cta": 7.0,
                          "brand_voice": 7.4, "emotional_resonance": 7.4}},
    ]
    diagnosis = diagnose_drift(canary_results, golden_scores)
    assert isinstance(diagnosis, DriftDiagnosis)
    assert diagnosis.is_evaluator_drift is False


def test_diagnose_drift_evaluator_shifted() -> None:
    """Canary scores diverging from humans means evaluator drift detected."""
    canary_results = [
        {"ad_id": "ref_vt_01", "quality_label": "excellent",
         "scores": {"clarity": 4.0, "value_proposition": 4.0, "cta": 3.0,
                    "brand_voice": 3.0, "emotional_resonance": 3.0}},
    ]
    golden_scores = [
        {"ad_id": "ref_vt_01", "quality_label": "excellent",
         "human_scores": {"clarity": 8.4, "value_proposition": 8.4, "cta": 7.0,
                          "brand_voice": 7.4, "emotional_resonance": 7.4}},
    ]
    diagnosis = diagnose_drift(canary_results, golden_scores)
    assert diagnosis.is_evaluator_drift is True
    assert len(diagnosis.affected_dimensions) > 0
    assert diagnosis.recommendation


# --- Control Chart Data ---


def test_control_chart_data_format(tmp_path: Path) -> None:
    """Control chart data has all required fields for dashboard."""
    from iterate.ledger import log_event

    ledger_path = str(tmp_path / "ledger.jsonl")
    for i in range(6):
        log_event(ledger_path, {
            "event_type": "BatchCompleted",
            "ad_id": f"batch_{i}",
            "brief_id": "b001",
            "cycle_number": 1,
            "action": "batch-complete",
            "inputs": {},
            "outputs": {"batch_avg_score": 7.0 + (i % 3) * 0.1},
            "scores": {},
            "tokens_consumed": 0,
            "model_used": "gemini-2.0-flash",
            "seed": "42",
        })

    chart = get_control_chart_data(ledger_path)
    assert isinstance(chart, ControlChartData)
    assert len(chart.batch_averages) == 6
    assert chart.ucl is not None
    assert chart.lcl is not None
    assert chart.mean is not None
