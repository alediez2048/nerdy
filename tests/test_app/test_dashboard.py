# PA-09: Dashboard API tests
"""Tests for session-scoped dashboard endpoints and competitive summary."""

import tempfile
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
import app.models.user  # noqa: F401
import app.models.session  # noqa: F401
import app.models.curation  # noqa: F401
import app.models.campaign  # noqa: F401
from app.models.session import Session as SessionModel


@asynccontextmanager
async def _noop_lifespan(app):
    yield


_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
_engine = create_engine(f"sqlite:///{_tmp.name}")
Base.metadata.create_all(_engine)
_TestSession = sessionmaker(bind=_engine)


def _override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


def _override_user():
    return {"user_id": "alice", "email": "alice@nerdy.com", "name": "Alice"}


@pytest.fixture(autouse=True)
def _clean():
    yield
    db = _TestSession()
    db.query(SessionModel).delete()
    db.commit()
    db.close()


def _seed_session(session_id: str = "sess_dash", user_id: str = "alice") -> str:
    """Insert a session row directly."""
    db = _TestSession()
    row = SessionModel(
        session_id=session_id,
        user_id=user_id,
        config={"audience": "parents", "campaign_goal": "conversion"},
        status="completed",
    )
    db.add(row)
    db.commit()
    db.close()
    return session_id


@pytest.fixture()
def client():
    from app.api.main import app
    from app.api.deps import get_current_user
    from app.db import get_db

    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_user

    with (
        patch("app.api.main.lifespan", _noop_lifespan),
        patch("app.api.routes.dashboard.init_db"),
    ):
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()


# --- Dashboard endpoint tests ---


def test_summary_returns_data(client):
    sid = _seed_session()

    with patch("app.api.routes.dashboard._get_dashboard_data") as mock_dash:
        mock_dash.return_value = {
            "pipeline_summary": {"total_ads_generated": 50, "total_ads_published": 38},
        }
        resp = client.get(f"/api/sessions/{sid}/summary")

    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == sid
    assert data["pipeline_summary"]["total_ads_generated"] == 50


def test_summary_falls_back_to_results_summary_when_ledger_export_empty(client):
    """Overview / costs API: DB results_summary fills KPIs when ledger file is missing."""
    sid = _seed_session("sess_fb")
    db = _TestSession()
    row = db.query(SessionModel).filter(SessionModel.session_id == sid).first()
    assert row is not None
    row.results_summary = {
        "ads_generated": 12,
        "ads_published": 10,
        "ads_discarded": 0,
        "avg_score": 7.2,
        "cost_so_far": 3.45,
    }
    row.ledger_path = None
    db.commit()
    db.close()

    with patch("app.api.routes.dashboard._get_dashboard_data", return_value={}):
        resp = client.get(f"/api/sessions/{sid}/summary")

    assert resp.status_code == 200
    ps = resp.json()["pipeline_summary"]
    assert ps["total_ads_generated"] == 12
    assert ps["total_ads_published"] == 10
    assert ps["total_cost_usd"] == 3.45
    assert ps["cost_source"] == "results_summary"


def test_costs_falls_back_to_results_summary_when_ledger_export_empty(client):
    sid = _seed_session("sess_cost_fb")
    db = _TestSession()
    row = db.query(SessionModel).filter(SessionModel.session_id == sid).first()
    assert row is not None
    row.results_summary = {"cost_so_far": 2.5}
    row.ledger_path = None
    db.commit()
    db.close()

    with patch("app.api.routes.dashboard._get_dashboard_data", return_value={}):
        resp = client.get(f"/api/sessions/{sid}/costs")

    assert resp.status_code == 200
    te = resp.json()["token_economics"]
    assert te["total_cost_usd"] == 2.5
    assert te["cost_source"] == "results_summary"


def test_cycles_returns_data(client):
    sid = _seed_session()

    with patch("app.api.routes.dashboard._get_dashboard_data") as mock_dash:
        mock_dash.return_value = {
            "iteration_cycles": [{"ad_id": "ad_1", "score_before": 5.0, "score_after": 7.5}],
            "quality_trends": {"batch_scores": []},
        }
        resp = client.get(f"/api/sessions/{sid}/cycles")

    assert resp.status_code == 200
    assert len(resp.json()["iteration_cycles"]) == 1


def test_ads_returns_library(client):
    sid = _seed_session()

    with patch("app.api.routes.dashboard._get_dashboard_data") as mock_dash:
        mock_dash.return_value = {
            "ad_library": [
                {"ad_id": "ad_1", "aggregate_score": 7.8, "status": "published"},
                {"ad_id": "ad_2", "aggregate_score": 5.2, "status": "discarded"},
            ],
        }
        resp = client.get(f"/api/sessions/{sid}/ads")

    assert resp.status_code == 200
    assert len(resp.json()["ad_library"]) == 2


def test_404_for_nonexistent_session(client):
    resp = client.get("/api/sessions/fake_session/summary")
    assert resp.status_code == 404


def test_404_for_other_user_session(client):
    _seed_session("sess_bob", user_id="bob")
    resp = client.get("/api/sessions/sess_bob/summary")
    assert resp.status_code == 404


def test_spc_returns_health(client):
    sid = _seed_session()

    with patch("app.api.routes.dashboard._get_dashboard_data") as mock_dash:
        mock_dash.return_value = {
            "system_health": {
                "spc": {"mean": 7.5, "ucl": 8.5, "lcl": 6.5, "breach_indices": []},
                "compliance_stats": {"total_checked": 50, "passed": 48, "failed": 2},
            },
        }
        resp = client.get(f"/api/sessions/{sid}/spc")

    assert resp.status_code == 200
    assert resp.json()["system_health"]["spc"]["mean"] == 7.5


def test_competitive_summary(client):
    resp = client.get("/api/competitive/summary")
    assert resp.status_code == 200


def test_global_dashboard_cost_uses_session_rollup(client):
    """Global dashboard summary cost reflects app session summaries."""
    _seed_session("sess_one")
    _seed_session("sess_two")

    db = _TestSession()
    rows = db.query(SessionModel).order_by(SessionModel.session_id).all()
    rows[0].results_summary = {"cost_so_far": 7.2}
    rows[1].results_summary = {"cost_so_far": 10.0}
    db.commit()
    db.close()

    with (
        patch("app.api.routes.dashboard.SessionLocal", _TestSession),
        patch("app.api.routes.dashboard.Path.exists", return_value=True),
        patch("output.export_dashboard.merge_ledger_events", return_value=[]),
        patch("output.export_dashboard.filter_events_by_timeframe", side_effect=lambda events, timeframe: events),
        patch(
            "output.export_dashboard.build_dashboard_data_from_events",
            return_value={"pipeline_summary": {"total_cost_usd": 86.85}},
        ),
        patch("evaluate.cost_reporter.compute_global_total_cost_usd", return_value=17.2),
    ):
        resp = client.get("/api/dashboard/global?timeframe=all")

    assert resp.status_code == 200
    assert resp.json()["pipeline_summary"]["total_cost_usd"] == 17.2
