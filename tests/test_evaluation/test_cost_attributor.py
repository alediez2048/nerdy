"""PH-02 CostAttributor tests.

Cover the public surface added in PH-02:
- ``SessionCostResult`` exposes a per-format breakdown that sums to the
  ledger-derived total.
- ``confidence`` is derived correctly from ``source``.
- The video winner-only rule is honoured in the breakdown (only the
  selected variant's cost counts toward ``video_usd``).
- ``attribute_session_cost`` is a behaviour-equivalent alias of
  ``compute_session_cost_usd``.
- Manifest fallback path produces ``confidence == "low"`` and surfaces
  whatever ledger split we *did* observe even when the total comes from
  the manifest.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluate.cost_reporter import (
    SessionCostResult,
    _compute_format_breakdown_usd,
    _confidence_from_source,
    attribute_session_cost,
    compute_session_cost_usd,
    reload_cost_manifest,
)
from iterate.ledger_events import (
    AdGenerated,
    BriefExpanded,
    ImageGenerated,
    VideoGenerated,
    VideoSelected,
)
from iterate.ledger_writer import LedgerWriter


# --- confidence derivation -----------------------------------------------


def test_confidence_high_for_ledger() -> None:
    assert _confidence_from_source("ledger") == "high"


def test_confidence_medium_for_ledger_partial() -> None:
    assert _confidence_from_source("ledger_partial") == "medium"


def test_confidence_low_for_manifest_estimate() -> None:
    assert _confidence_from_source("manifest_estimate") == "low"


def test_confidence_medium_for_unknown_source() -> None:
    assert _confidence_from_source("future_source_we_have_not_added") == "medium"


def test_session_result_confidence_field_is_derived() -> None:
    r = SessionCostResult(
        session_id="s", total_usd=0.5, source="ledger",
        ledger_usd=0.5, manifest_usd=None,
    )
    assert r.confidence == "high"

    r2 = SessionCostResult(
        session_id="s", total_usd=0.5, source="manifest_estimate",
        ledger_usd=0.0, manifest_usd=0.5,
    )
    assert r2.confidence == "low"


# --- breakdown sums to total ---------------------------------------------


def test_breakdown_text_only(tmp_path: Path) -> None:
    p = str(tmp_path / "l.jsonl")
    w = LedgerWriter(p)
    w.record(BriefExpanded(
        brief_id="b1", cycle_number=0, action="expand",
        tokens_consumed=1000, model_used="gemini-2.0-flash", seed="s",
    ))
    w.record(AdGenerated(
        ad_id="ad_001", brief_id="b1", cycle_number=0, action="generation",
        tokens_consumed=2000, model_used="gemini-2.0-flash", seed="s",
    ))

    r = attribute_session_cost("test_session", p)
    assert r.video_usd == 0.0
    assert r.image_usd == 0.0
    assert r.text_usd > 0
    assert pytest.approx(r.text_usd + r.image_usd + r.video_usd, rel=1e-6) == r.ledger_usd
    assert r.confidence == "high" if r.source == "ledger" else r.confidence in {"medium", "low"}


def test_breakdown_image_only(tmp_path: Path) -> None:
    p = str(tmp_path / "l.jsonl")
    w = LedgerWriter(p)
    # Image is per-call, not per-token
    w.record(ImageGenerated(
        ad_id="ad_001", brief_id="b", cycle_number=0, action="img",
        tokens_consumed=0, model_used="gemini-2.5-flash-image", seed="s",
    ))

    breakdown = _compute_format_breakdown_usd([
        {
            "event_type": "ImageGenerated",
            "model_used": "gemini-2.5-flash-image",
            "tokens_consumed": 0,
            "outputs": {},
        }
    ])
    assert breakdown["image"] > 0
    assert breakdown["text"] == 0.0
    assert breakdown["video"] == 0.0


def test_breakdown_video_winner_only_rule(tmp_path: Path) -> None:
    """Only the selected video variant counts toward video_usd."""
    p = str(tmp_path / "l.jsonl")
    w = LedgerWriter(p)
    model = "fal-ai/minimax/hailuo-02/standard/text-to-video"
    w.record(VideoGenerated(
        ad_id="ad_001", brief_id="b", cycle_number=0, action="vid_anchor",
        tokens_consumed=0, model_used=model, seed="s",
        outputs={"variant_type": "anchor"},
    ))
    w.record(VideoGenerated(
        ad_id="ad_001", brief_id="b", cycle_number=0, action="vid_alt",
        tokens_consumed=0, model_used=model, seed="s",
        outputs={"variant_type": "alternative"},
    ))
    w.record(VideoSelected(
        ad_id="ad_001", brief_id="b", cycle_number=0, action="select",
        tokens_consumed=0, model_used="none", seed="s",
        outputs={"winner_variant": "anchor"},
    ))

    # Use the breakdown helper directly — independent of the
    # ledger-reliability heuristic that classifies video-only ledgers
    # as "ledger_partial" because they lack text events with tokens.
    from iterate.ledger_reader import read_dicts
    from evaluate.cost_reporter import compute_event_cost
    breakdown = _compute_format_breakdown_usd(read_dicts(p))
    # 1× per-call rate, not 2×
    single = compute_event_cost({
        "event_type": "VideoGenerated",
        "model_used": model,
        "tokens_consumed": 0,
    })
    assert pytest.approx(breakdown["video"], rel=1e-6) == single
    assert breakdown["text"] == 0.0
    assert breakdown["image"] == 0.0

    # And the high-level result still reflects the winner-only rule.
    r = attribute_session_cost("test_session", p)
    assert pytest.approx(r.video_usd, rel=1e-6) == single


# --- attribute_session_cost is an alias ----------------------------------


def test_attribute_session_cost_matches_compute_session_cost_usd(tmp_path: Path) -> None:
    p = str(tmp_path / "l.jsonl")
    LedgerWriter(p).record(BriefExpanded(
        brief_id="b1", cycle_number=0, action="expand",
        tokens_consumed=1000, model_used="gemini-2.0-flash", seed="s",
    ))

    legacy = compute_session_cost_usd("test_session", p)
    canonical = attribute_session_cost("test_session", p)

    assert legacy.total_usd == canonical.total_usd
    assert legacy.source == canonical.source
    assert legacy.ledger_usd == canonical.ledger_usd
    assert legacy.text_usd == canonical.text_usd
    assert legacy.image_usd == canonical.image_usd
    assert legacy.video_usd == canonical.video_usd
    assert legacy.confidence == canonical.confidence


# --- manifest fallback ----------------------------------------------------


def test_manifest_fallback_yields_low_confidence(tmp_path: Path, monkeypatch) -> None:
    """When ledger is thin and manifest has an entry, confidence is low."""
    # Empty ledger
    p = str(tmp_path / "l.jsonl")
    Path(p).touch()

    # Stub manifest
    manifest_dir = tmp_path
    manifest_path = manifest_dir / "cost_manifest.json"
    manifest_path.write_text(json.dumps({
        "sessions": {
            "session_with_baseline": {"estimated_cost_usd": 12.34}
        }
    }))
    monkeypatch.setattr(
        "evaluate.cost_reporter.COST_MANIFEST_PATH",
        manifest_path,
    )
    reload_cost_manifest()

    r = attribute_session_cost("session_with_baseline", p)
    assert r.source == "manifest_estimate"
    assert r.confidence == "low"
    assert r.total_usd == pytest.approx(12.34)
    # Breakdown reflects what we KNOW from events (i.e. nothing).
    assert r.text_usd == 0.0
    assert r.image_usd == 0.0
    assert r.video_usd == 0.0

    # Cleanup so other tests don't see this manifest.
    reload_cost_manifest()
