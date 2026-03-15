"""Tests for ad library export (P5-10).

Validates JSON and CSV export with full metadata, scores, and summary stats.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from output.export_ad_library import export_ad_library_json, export_ad_library_csv, build_ad_library


def _seed_ledger(path: str) -> None:
    """Write representative ledger events for testing."""
    events = [
        {
            "timestamp": "2026-03-15T10:00:00Z",
            "event_type": "AdGenerated",
            "ad_id": "ad_b001_c0_abc1",
            "brief_id": "b001",
            "cycle_number": 0,
            "action": "generation",
            "inputs": {"audience": "parents", "campaign_goal": "conversion"},
            "outputs": {
                "headline": "Boost Your SAT Score",
                "primary_text": "Expert 1-on-1 tutoring that adapts.",
                "description": "Start improving today.",
                "cta_button": "Learn More",
            },
            "scores": {},
            "tokens_consumed": 500,
            "model_used": "gemini-2.0-flash",
            "seed": "abc1",
        },
        {
            "timestamp": "2026-03-15T10:01:00Z",
            "event_type": "AdEvaluated",
            "ad_id": "ad_b001_c0_abc1",
            "brief_id": "b001",
            "cycle_number": 0,
            "action": "evaluation",
            "inputs": {},
            "outputs": {
                "scores": {
                    "clarity": 8.0, "value_proposition": 7.5,
                    "cta": 7.0, "brand_voice": 7.2, "emotional_resonance": 7.8,
                },
                "aggregate_score": 7.5,
                "rationale": {"clarity": "Clear messaging", "cta": "Good but generic"},
            },
            "tokens_consumed": 300,
            "model_used": "gemini-2.0-flash",
            "seed": "abc1",
        },
        {
            "timestamp": "2026-03-15T10:02:00Z",
            "event_type": "AdPublished",
            "ad_id": "ad_b001_c0_abc1",
            "brief_id": "b001",
            "cycle_number": 0,
            "action": "publish",
            "inputs": {"aggregate_score": 7.5},
            "outputs": {},
            "scores": {},
            "tokens_consumed": 0,
            "model_used": "gemini-2.0-flash",
            "seed": "abc1",
        },
        {
            "timestamp": "2026-03-15T10:03:00Z",
            "event_type": "AdGenerated",
            "ad_id": "ad_b002_c0_def2",
            "brief_id": "b002",
            "cycle_number": 0,
            "action": "generation",
            "inputs": {"audience": "students", "campaign_goal": "awareness"},
            "outputs": {
                "headline": "SAT Prep Made Easy",
                "primary_text": "Join students who improved.",
                "description": "Free practice test.",
                "cta_button": "Get Started",
            },
            "scores": {},
            "tokens_consumed": 480,
            "model_used": "gemini-2.0-flash",
            "seed": "def2",
        },
        {
            "timestamp": "2026-03-15T10:04:00Z",
            "event_type": "AdEvaluated",
            "ad_id": "ad_b002_c0_def2",
            "brief_id": "b002",
            "cycle_number": 0,
            "action": "evaluation",
            "inputs": {},
            "outputs": {
                "scores": {
                    "clarity": 5.0, "value_proposition": 4.5,
                    "cta": 4.0, "brand_voice": 5.5, "emotional_resonance": 4.0,
                },
                "aggregate_score": 4.6,
                "rationale": {"clarity": "Too vague", "cta": "No clear CTA"},
            },
            "tokens_consumed": 290,
            "model_used": "gemini-2.0-flash",
            "seed": "def2",
        },
        {
            "timestamp": "2026-03-15T10:05:00Z",
            "event_type": "AdDiscarded",
            "ad_id": "ad_b002_c0_def2",
            "brief_id": "b002",
            "cycle_number": 0,
            "action": "discard",
            "inputs": {"aggregate_score": 4.6},
            "outputs": {},
            "scores": {},
            "tokens_consumed": 0,
            "model_used": "gemini-2.0-flash",
            "seed": "def2",
        },
    ]
    with open(path, "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


def test_build_ad_library_returns_all_ads(tmp_path: Path) -> None:
    """Ad library contains all ads from ledger."""
    ledger = str(tmp_path / "ledger.jsonl")
    _seed_ledger(ledger)

    ads = build_ad_library(ledger)
    ad_ids = [a["ad_id"] for a in ads]
    assert "ad_b001_c0_abc1" in ad_ids
    assert "ad_b002_c0_def2" in ad_ids
    assert len(ads) == 2


def test_ad_has_required_fields(tmp_path: Path) -> None:
    """Each ad has all required metadata fields."""
    ledger = str(tmp_path / "ledger.jsonl")
    _seed_ledger(ledger)

    ads = build_ad_library(ledger)
    required = {"ad_id", "brief_id", "copy", "scores", "aggregate_score", "rationale", "status", "cycle_count", "model_used", "tokens_total", "seed"}
    for ad in ads:
        assert required.issubset(set(ad.keys())), f"Missing fields: {required - set(ad.keys())}"


def test_json_export_has_summary(tmp_path: Path) -> None:
    """JSON export includes summary statistics header."""
    ledger = str(tmp_path / "ledger.jsonl")
    _seed_ledger(ledger)
    output = str(tmp_path / "ad_library.json")

    export_ad_library_json(ledger, output)

    with open(output) as f:
        data = json.load(f)

    assert "summary" in data
    assert data["summary"]["total_ads"] == 2
    assert data["summary"]["total_publishable"] == 1
    assert "avg_score" in data["summary"]
    assert "per_dimension_avg" in data["summary"]


def test_json_export_summary_math(tmp_path: Path) -> None:
    """Summary statistics are mathematically correct."""
    ledger = str(tmp_path / "ledger.jsonl")
    _seed_ledger(ledger)
    output = str(tmp_path / "ad_library.json")

    export_ad_library_json(ledger, output)

    with open(output) as f:
        data = json.load(f)

    # avg_score should be average of 7.5 and 4.6
    expected_avg = round((7.5 + 4.6) / 2, 2)
    assert data["summary"]["avg_score"] == expected_avg
    assert data["summary"]["total_publishable"] == 1


def test_csv_export_has_correct_rows(tmp_path: Path) -> None:
    """CSV export has one row per ad plus header."""
    ledger = str(tmp_path / "ledger.jsonl")
    _seed_ledger(ledger)
    output = str(tmp_path / "ad_library.csv")

    export_ad_library_csv(ledger, output)

    with open(output) as f:
        reader = csv.reader(f)
        rows = list(reader)

    assert len(rows) == 3  # header + 2 ads


def test_csv_sorted_by_score_descending(tmp_path: Path) -> None:
    """CSV rows are sorted by aggregate score descending."""
    ledger = str(tmp_path / "ledger.jsonl")
    _seed_ledger(ledger)
    output = str(tmp_path / "ad_library.csv")

    export_ad_library_csv(ledger, output)

    with open(output) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    scores = [float(r["aggregate_score"]) for r in rows]
    assert scores == sorted(scores, reverse=True)


def test_status_correctly_assigned(tmp_path: Path) -> None:
    """Published and discarded status correctly reflected."""
    ledger = str(tmp_path / "ledger.jsonl")
    _seed_ledger(ledger)

    ads = build_ad_library(ledger)
    status_map = {a["ad_id"]: a["status"] for a in ads}
    assert status_map["ad_b001_c0_abc1"] == "published"
    assert status_map["ad_b002_c0_def2"] == "discarded"
