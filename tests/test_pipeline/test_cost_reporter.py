"""Tests for cross-format cost reporter (P3-05).

Validates cost reporting across text, image, and video formats,
grouping by model, format, and task with estimated USD costs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import evaluate.cost_reporter as cost_reporter_mod
from evaluate.cost_reporter import (
    CrossFormatCostReport,
    compute_event_cost,
    format_cost_report,
    generate_cost_report,
    compute_session_cost_usd,
    sum_session_display_cost_usd,
    reload_cost_manifest,
    reload_fal_veo3_cost_config,
    reload_fal_model_cost_overrides,
    reload_google_veo_cost_config,
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


def test_fal_veo3_video_generated_uses_config_per_call_not_invoice_average() -> None:
    """fal-ai/veo3 uses video_fal_veo3_cost_per_call_usd (Fal hosted), distinct from Google Veo."""
    reload_fal_veo3_cost_config()
    ev = {
        "event_type": "VideoGenerated",
        "model_used": "fal-ai/veo3",
        "tokens_consumed": 0,
    }
    cost = compute_event_cost(ev)
    assert cost >= 1.0, "Fal fal-ai/veo3 per-call should come from video_fal_veo3_cost_per_call_usd"
    assert abs(cost - 6.40) < 0.01
    reload_fal_veo3_cost_config()


def test_google_veo_video_generated_uses_config_per_call() -> None:
    """veo-3.1-fast (Google Veo API) uses video_google_veo_cost_per_call_usd, not Fal rates."""
    reload_google_veo_cost_config()
    ev = {
        "event_type": "VideoGenerated",
        "model_used": "veo-3.1-fast",
        "tokens_consumed": 0,
    }
    cost = compute_event_cost(ev)
    assert abs(cost - 6.00) < 0.01
    reload_google_veo_cost_config()


def test_sum_session_display_cost_excludes_non_winning_video_variant() -> None:
    """When VideoSelected picks a winner, only that VideoGenerated is billed in session total."""
    reload_fal_model_cost_overrides()
    events = [
        {
            "event_type": "VideoGenerated",
            "ad_id": "ad_x",
            "model_used": "fal-ai/wan/v2.2-5b/text-to-video/distill",
            "tokens_consumed": 0,
            "outputs": {"variant_type": "anchor"},
        },
        {
            "event_type": "VideoGenerated",
            "ad_id": "ad_x",
            "model_used": "fal-ai/wan/v2.2-5b/text-to-video/distill",
            "tokens_consumed": 0,
            "outputs": {"variant_type": "alternative"},
        },
        {
            "event_type": "VideoSelected",
            "ad_id": "ad_x",
            "model_used": "fal-ai/wan/v2.2-5b/text-to-video/distill",
            "tokens_consumed": 0,
            "outputs": {"winner_variant": "anchor", "winner_video_path": "/tmp/a.mp4"},
        },
    ]
    full = sum(compute_event_cost(e) for e in events)
    display = sum_session_display_cost_usd(events)
    one_job = compute_event_cost(events[0])
    assert full > display
    assert abs(display - one_job) < 0.001
    reload_fal_model_cost_overrides()


def test_fal_wan_distill_per_call_uses_table_or_config_override() -> None:
    """Fal Wan distill uses MODEL_COST_RATES / video_fal_model_costs_usd (not Veo3 pricing)."""
    reload_fal_model_cost_overrides()
    ev = {
        "event_type": "VideoGenerated",
        "model_used": "fal-ai/wan/v2.2-5b/text-to-video/distill",
        "tokens_consumed": 0,
    }
    cost = compute_event_cost(ev)
    assert abs(cost - 1.50) < 0.01
    reload_fal_model_cost_overrides()


def test_compute_session_cost_uses_manifest_when_ledger_unreliable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Historical sessions with empty/low ledger use cost_manifest estimate."""
    manifest_path = tmp_path / "cost_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "sessions": {
                    "sess_test": {
                        "estimated_cost_usd": 5.25,
                        "method": "backfill_estimate",
                    },
                },
            },
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cost_reporter_mod, "COST_MANIFEST_PATH", manifest_path)
    reload_cost_manifest()

    ledger_path = str(tmp_path / "ledger.jsonl")
    Path(ledger_path).touch()

    result = compute_session_cost_usd("sess_test", ledger_path)
    assert result.source == "manifest_estimate"
    assert result.total_usd == 5.25

    reload_cost_manifest()
