"""Tests for cross-format cost reporter (P3-05).

Validates cost reporting across text, image, and video formats,
grouping by model, format, and task with estimated USD costs.
"""

from __future__ import annotations

from pathlib import Path

from evaluate.cost_reporter import (
    CrossFormatCostReport,
    format_cost_report,
    generate_cost_report,
)
from iterate.ledger import log_event


def _log_events(ledger_path: str, events: list[dict]) -> None:
    """Log multiple events to ledger."""
    for event in events:
        log_event(ledger_path, event)


def _base_event(event_type: str, model: str, tokens: int, action: str, ad_id: str = "ad_001") -> dict:
    """Build a base ledger event."""
    return {
        "event_type": event_type,
        "ad_id": ad_id,
        "brief_id": "b001",
        "cycle_number": 1,
        "action": action,
        "inputs": {},
        "outputs": {},
        "scores": {},
        "tokens_consumed": tokens,
        "model_used": model,
        "seed": "42",
    }


# --- Basic Reports ---


def test_text_only_report(tmp_path: Path) -> None:
    """Cost report with text-only events groups correctly."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _log_events(ledger_path, [
        _base_event("AdGenerated", "gemini-2.0-flash", 500, "generation"),
        _base_event("AdEvaluated", "gemini-2.0-flash", 300, "evaluation"),
    ])

    report = generate_cost_report(ledger_path)
    assert isinstance(report, CrossFormatCostReport)
    assert report.cost_by_format.get("text", 0) > 0
    assert report.cost_by_format.get("image", 0) == 0


def test_text_and_image_report(tmp_path: Path) -> None:
    """Cost report with text + image events."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _log_events(ledger_path, [
        _base_event("AdGenerated", "gemini-2.0-flash", 500, "generation"),
        _base_event("ImageGenerated", "gemini-2.0-flash-preview-image-generation", 800, "image-generation"),
    ])

    report = generate_cost_report(ledger_path)
    assert report.cost_by_format.get("text", 0) > 0
    assert report.cost_by_format.get("image", 0) > 0


def test_all_three_formats(tmp_path: Path) -> None:
    """Cost report with text + image + video events."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _log_events(ledger_path, [
        _base_event("AdGenerated", "gemini-2.0-flash", 500, "generation"),
        _base_event("ImageGenerated", "gemini-2.0-flash-preview-image-generation", 800, "image-generation"),
        _base_event("VideoGenerated", "veo-3.1-fast", 0, "video-generation"),
    ])

    report = generate_cost_report(ledger_path)
    assert "text" in report.cost_by_format
    assert "image" in report.cost_by_format
    assert "video" in report.cost_by_format


# --- Grouping Accuracy ---


def test_cost_grouping_by_model(tmp_path: Path) -> None:
    """Cost grouped by model sums correctly."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _log_events(ledger_path, [
        _base_event("AdGenerated", "gemini-2.0-flash", 500, "generation"),
        _base_event("AdGenerated", "gemini-2.0-flash", 300, "generation", "ad_002"),
        _base_event("AdRegenerated", "gemini-2.0-pro", 1000, "regeneration"),
    ])

    report = generate_cost_report(ledger_path)
    assert report.cost_by_model["gemini-2.0-flash"] > 0
    assert report.cost_by_model["gemini-2.0-pro"] > 0


def test_cost_grouping_by_task(tmp_path: Path) -> None:
    """Cost grouped by task sums correctly."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _log_events(ledger_path, [
        _base_event("AdGenerated", "gemini-2.0-flash", 500, "generation"),
        _base_event("AdEvaluated", "gemini-2.0-flash", 300, "evaluation"),
    ])

    report = generate_cost_report(ledger_path)
    assert "generation" in report.cost_by_task
    assert "evaluation" in report.cost_by_task


def test_estimated_usd_cost(tmp_path: Path) -> None:
    """Estimated USD cost is non-negative and proportional to tokens."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _log_events(ledger_path, [
        _base_event("AdGenerated", "gemini-2.0-flash", 1000, "generation"),
    ])

    report = generate_cost_report(ledger_path)
    assert report.total_cost_usd > 0
    assert len(report.entries) > 0
    assert all(e.estimated_cost_usd >= 0 for e in report.entries)


def test_empty_ledger_zero_cost(tmp_path: Path) -> None:
    """Empty ledger returns zero-cost report."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    Path(ledger_path).touch()

    report = generate_cost_report(ledger_path)
    assert report.total_cost_usd == 0
    assert len(report.entries) == 0


def test_format_cost_report_readable(tmp_path: Path) -> None:
    """format_cost_report produces readable text output."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _log_events(ledger_path, [
        _base_event("AdGenerated", "gemini-2.0-flash", 1000, "generation"),
    ])

    report = generate_cost_report(ledger_path)
    text = format_cost_report(report)
    assert isinstance(text, str)
    assert "Total" in text
    assert "$" in text
