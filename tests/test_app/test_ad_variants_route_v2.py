"""PI-07: /variants endpoint emits v2 shape when MediaEvaluation events exist."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.main import app
from app.db import SessionLocal, init_db
from app.models.session import Session as SessionModel

TEST_USER_ID = "test_user_variants_v2"


@pytest.fixture
def authed_client():
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": TEST_USER_ID,
        "email": "variants_v2@test.com",
    }
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)


def _seed_v2_session(session_id: str, ad_id: str) -> str:
    """Write a session row + a v2 ledger with MediaEvaluation events."""
    init_db()
    tmp_dir = tempfile.mkdtemp(prefix=f"{session_id}_")
    ledger_path = str(Path(tmp_dir) / "ledger.jsonl")

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

    from iterate.ledger_events import ImageGenerated, MediaEvaluation
    from iterate.ledger_writer import LedgerWriter

    writer = LedgerWriter(ledger_path)
    triples = [
        ("anchor", 80.0, {"thumb_stop_potential": 8, "mobile_legibility": 8}),
        ("tone_shift", 60.0, {"thumb_stop_potential": 6, "mobile_legibility": 6}),
        ("composition_shift", 45.0, {"thumb_stop_potential": 4, "mobile_legibility": 5}),
    ]
    for variant, composite, dim_scores in triples:
        writer.record(ImageGenerated(
            ad_id=ad_id, brief_id="brief_001", cycle_number=0,
            action=f"image_gen_{variant}",
            tokens_consumed=0,
            model_used="nano-banana-pro-preview",
            seed="0",
            inputs={"variant_type": variant},
            outputs={"image_path": f"output/images/{ad_id}_{variant}.png"},
        ))
        writer.record(MediaEvaluation(
            ad_id=ad_id, brief_id="brief_001", cycle_number=0,
            action=f"media_eval_{variant}",
            tokens_consumed=1500, model_used="gemini-2.5-flash", seed="0",
            inputs={"variant_type": variant, "media_type": "image"},
            outputs={
                "schema_version": "v2",
                "media_type": "image",
                "media_path": f"output/images/{ad_id}_{variant}.png",
                "dimensions": {
                    "thumb_stop_potential": {
                        "score": dim_scores["thumb_stop_potential"],
                        "weight": 0.20,
                        "rationale": f"{variant} hook",
                    },
                    "mobile_legibility": {
                        "score": dim_scores["mobile_legibility"],
                        "weight": 0.15,
                        "rationale": f"{variant} legibility",
                    },
                },
                "penalty_gates": {
                    "has_ai_artifacts": {"triggered": False, "rationale": "clean"},
                },
                "raw_score": composite / 100.0,
                "penalty_multiplier": 1.0,
                "composite_score": composite,
            },
        ))
    return ledger_path


def _seed_v1_session(session_id: str, ad_id: str) -> None:
    init_db()
    tmp_dir = tempfile.mkdtemp(prefix=f"{session_id}_")
    ledger_path = str(Path(tmp_dir) / "ledger.jsonl")
    db = SessionLocal()
    try:
        db.query(SessionModel).filter(SessionModel.session_id == session_id).delete()
        db.add(SessionModel(
            session_id=session_id, user_id=TEST_USER_ID,
            config={"session_type": "image"}, status="completed",
            ledger_path=ledger_path,
        ))
        db.commit()
    finally:
        db.close()
    from iterate.ledger_events import ImageEvaluated, ImageGenerated
    from iterate.ledger_writer import LedgerWriter
    w = LedgerWriter(ledger_path)
    w.record(ImageGenerated(
        ad_id=ad_id, brief_id="b1", cycle_number=0,
        action="image_gen_anchor", tokens_consumed=0,
        model_used="gemini-2.5-flash-image", seed="0",
        inputs={"variant_type": "anchor"},
        outputs={"image_path": f"output/images/{ad_id}_anchor.png"},
    ))
    w.record(ImageEvaluated(
        ad_id=ad_id, brief_id="b1", cycle_number=0,
        action="image_eval_anchor", tokens_consumed=0,
        model_used="gemini-2.0-flash", seed="0",
        inputs={"variant_type": "anchor"},
        outputs={
            "attribute_pass_pct": 0.8, "coherence_avg": 0.5,
            "composite_score": 0.35,
        },
    ))


def test_variants_endpoint_returns_v2_shape(authed_client: TestClient):
    sid = "sess_v2_happy"
    ad_id = "ad_v2_001"
    _seed_v2_session(sid, ad_id)
    resp = authed_client.get(f"/api/sessions/{sid}/ads/{ad_id}/variants")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["schema_version"] == "v2"
    assert len(body["variants"]) == 3
    winners = [v for v in body["variants"] if v["is_winner"]]
    assert len(winners) == 1
    assert winners[0]["variant_type"] == "anchor"
    assert "dimensions" in winners[0]
    assert "thumb_stop_potential" in winners[0]["dimensions"]
    losers = [v for v in body["variants"] if not v["is_winner"]]
    assert all("rejection_reason" in v for v in losers)
    formula = body["selection_criteria"]["formula"]
    assert "composite" in formula.lower() or "raw_score" in formula


def test_variants_endpoint_falls_back_to_v1_for_legacy(authed_client: TestClient):
    sid = "sess_v1_legacy"
    ad_id = "ad_v1_001"
    _seed_v1_session(sid, ad_id)
    resp = authed_client.get(f"/api/sessions/{sid}/ads/{ad_id}/variants")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["schema_version"] == "v1"
    assert "composite_score" in body["variants"][0]
