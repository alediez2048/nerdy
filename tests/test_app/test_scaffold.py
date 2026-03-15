# PA-01: FastAPI scaffold tests
"""Tests for FastAPI application scaffold, Celery ping task, and database setup."""

from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.workers.tasks.ping import ping


@asynccontextmanager
async def _noop_lifespan(app):
    """Skip DB init during tests — no PostgreSQL needed."""
    yield


@pytest.fixture()
def client():
    """FastAPI test client with DB lifespan patched out."""
    with patch("app.api.main.lifespan", _noop_lifespan):
        from app.api.main import app

        app.router.lifespan_context = _noop_lifespan
        with TestClient(app) as c:
            yield c


# --- Health check ---


def test_health_check_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# --- CORS ---


def test_cors_headers_present(client):
    resp = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_rejects_unknown_origin(client):
    resp = client.options(
        "/health",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") != "http://evil.example.com"


# --- OpenAPI docs ---


def test_openapi_docs_available(client):
    resp = client.get("/docs")
    assert resp.status_code == 200


# --- Celery ping task ---


def test_celery_ping_returns_pong():
    result = ping()
    assert result == "pong"


# --- Configuration ---


def test_settings_loads_defaults():
    s = Settings(DATABASE_URL="postgresql://test:test@localhost/test", REDIS_URL="redis://localhost")
    assert "postgresql" in s.DATABASE_URL
    assert "redis" in s.REDIS_URL


# --- Database engine ---


def test_database_engine_created():
    from app.db import engine

    assert engine is not None
    assert "postgresql" in str(engine.url)
