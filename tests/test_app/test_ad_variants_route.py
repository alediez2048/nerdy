"""Test the /api/sessions/{id}/ads/{ad_id}/variants endpoint.

Covers:
- 404 when session not found
- 404 when ad has no image events in ledger
- 200 with full variant breakdown when 3 variants exist
- ``is_winner`` flag points at the highest-composite variant
- ``lost_by`` dimension is computed correctly when losers exist
- All-tie case marks all non-winners as ``dimension="tie"``
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.main import app
from app.db import init_db, SessionLocal
from app.models.session import Session as SessionModel


TEST_USER_ID = "test_user_variants"


@pytest.fixture
def authed_client():
    """TestClient with auth dependency overridden to TEST_USER_ID."""
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": TEST_USER_ID,
        "email": "variants@test.com",
    }
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)


def _seed_session_with_variants(
    session_id: str,
    ad_id: str,
    variants: list[dict],
) -> str:
    """Write a session row + a ledger with ImageGenerated + ImageEvaluated events.

    Returns the ledger path used.
    """
    init_db()
    tmp_dir = tempfile.mkdtemp(prefix=f"{session_id}_")
    ledger_path = str(Path(tmp_dir) / "ledger.jsonl")

    # Insert session row.
    db = SessionLocal()
    try:
        db.query(SessionModel).filter(SessionModel.session_id == session_id).delete()
        db.add(SessionModel(
            session_id=session_id,
            user_id=TEST_USER_ID,
            config={"session_type": "image"},
            status="completed",
            ledger_path=ledger_path,
        ))
        db.commit()
    finally:
        db.close()

    # Write a small ledger with one ImageGenerated + one ImageEvaluated per variant.
    from iterate.ledger_events import ImageEvaluated, ImageGenerated
    from iterate.ledger_writer import LedgerWriter

    writer = LedgerWriter(ledger_path)
    for v in variants:
        writer.record(ImageGenerated(
            ad_id=ad_id, brief_id="b1", cycle_number=0,
            action=f"image_gen_{v['variant_type']}",
            tokens_consumed=0,
            model_used=v.get("model_used", "nano-banana-pro-preview"),
            seed="0",
            inputs={"variant_type": v["variant_type"]},
            outputs={"image_path": f"output/images/{ad_id}_{v['variant_type']}_1x1.png"},
        ))
        writer.record(ImageEvaluated(
            ad_id=ad_id, brief_id="b1", cycle_number=0,
            action=f"image_eval_{v['variant_type']}",
            tokens_consumed=0, model_used="gemini-2.0-flash", seed="0",
            inputs={"variant_type": v["variant_type"]},
            outputs={
                "attribute_pass_pct": v["attr"],
                "coherence_avg": v["coh"],
                "composite_score": v["composite"],
            },
        ))
    return ledger_path


# --- 404 paths -------------------------------------------------------------


def test_404_when_session_missing(authed_client: TestClient) -> None:
    r = authed_client.get("/api/sessions/sess_does_not_exist/ads/ad_x/variants")
    assert r.status_code == 404


def test_404_when_ad_has_no_variants(authed_client: TestClient) -> None:
    sid = "sess_variants_empty"
    _seed_session_with_variants(sid, "ad_only_one", variants=[])
    r = authed_client.get(f"/api/sessions/{sid}/ads/ad_other_id/variants")
    assert r.status_code == 404


# --- happy path ------------------------------------------------------------


def test_returns_three_variants_with_winner(authed_client: TestClient) -> None:
    sid = "sess_variants_happy"
    ad_id = "ad_happy_001"
    # anchor has highest composite (0.78) — should be the winner.
    _seed_session_with_variants(sid, ad_id, [
        {"variant_type": "anchor", "attr": 0.90, "coh": 0.70,
         "composite": 0.90 * 0.4 + 0.70 * 0.6,
         "model_used": "nano-banana-pro-preview"},
        {"variant_type": "tone_shift", "attr": 0.80, "coh": 0.65,
         "composite": 0.80 * 0.4 + 0.65 * 0.6,
         "model_used": "gemini-2.5-flash-image"},
        {"variant_type": "composition_shift", "attr": 0.70, "coh": 0.55,
         "composite": 0.70 * 0.4 + 0.55 * 0.6,
         "model_used": "gemini-2.5-flash-image"},
    ])

    r = authed_client.get(f"/api/sessions/{sid}/ads/{ad_id}/variants")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["session_id"] == sid
    assert data["ad_id"] == ad_id
    assert data["selection_criteria"]["winner_variant_type"] == "anchor"
    assert len(data["variants"]) == 3

    # Find the winner — exactly one is_winner=True.
    winners = [v for v in data["variants"] if v["is_winner"]]
    assert len(winners) == 1
    assert winners[0]["variant_type"] == "anchor"
    assert winners[0]["lost_by"] is None
    assert winners[0]["predicted_cost_usd"] == pytest.approx(0.13)

    # Both losers have a lost_by reason populated.
    losers = [v for v in data["variants"] if not v["is_winner"]]
    assert all(v["lost_by"] is not None for v in losers)
    assert all(v["lost_by"]["composite_delta"] < 0 for v in losers)


def test_lost_by_dimension_picks_dominant_axis(authed_client: TestClient) -> None:
    """The 'lost_by' dimension should reflect the bigger weighted loss."""
    sid = "sess_variants_dim"
    ad_id = "ad_dim_001"
    # Winner: high coh, low attr — coherence carries the win.
    # Loser A: lower coherence (heavy loss)
    # Loser B: lower attribute (lighter loss)
    _seed_session_with_variants(sid, ad_id, [
        {"variant_type": "anchor", "attr": 0.5, "coh": 0.9, "composite": 0.5 * 0.4 + 0.9 * 0.6},
        {"variant_type": "tone_shift", "attr": 0.5, "coh": 0.4,
         "composite": 0.5 * 0.4 + 0.4 * 0.6},  # lost coh by 0.5 (weighted 0.30)
        {"variant_type": "composition_shift", "attr": 0.2, "coh": 0.9,
         "composite": 0.2 * 0.4 + 0.9 * 0.6},  # lost attr by 0.3 (weighted 0.12)
    ])

    r = authed_client.get(f"/api/sessions/{sid}/ads/{ad_id}/variants")
    assert r.status_code == 200
    data = r.json()
    by_type = {v["variant_type"]: v for v in data["variants"]}
    assert by_type["anchor"]["is_winner"] is True
    assert by_type["tone_shift"]["lost_by"]["dimension"] == "coherence"
    assert by_type["composition_shift"]["lost_by"]["dimension"] == "attribute"


def test_all_tie_marks_non_winners_as_tie(authed_client: TestClient) -> None:
    """When all variants score identically, non-winners get dimension='tie'."""
    sid = "sess_variants_tie"
    ad_id = "ad_tie_001"
    _seed_session_with_variants(sid, ad_id, [
        {"variant_type": "anchor", "attr": 0.8, "coh": 0.5, "composite": 0.62},
        {"variant_type": "tone_shift", "attr": 0.8, "coh": 0.5, "composite": 0.62},
        {"variant_type": "composition_shift", "attr": 0.8, "coh": 0.5, "composite": 0.62},
    ])

    r = authed_client.get(f"/api/sessions/{sid}/ads/{ad_id}/variants")
    assert r.status_code == 200
    data = r.json()
    losers = [v for v in data["variants"] if not v["is_winner"]]
    assert all(v["lost_by"]["dimension"] == "tie" for v in losers)
