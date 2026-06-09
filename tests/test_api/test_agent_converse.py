# PJ-04: Agent /converse scaffold tests
"""Locks in three loop invariants + the closure-bound user_id property.

The Gemini SDK is stubbed at ``app.api.agent.loop.run_conversation_turn``
where the tests need to control the model's output, OR at
``client.models.generate_content`` for the loop-internal tests.
"""
import tempfile
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db  # noqa: F401  — registers all models
from app.api.agent import loop as agent_loop
from app.api.agent.toolbox import ToolBox
from app.models.base import Base
from app.models.brand_profile import BrandProfile
from app.models.conversation_message import ConversationMessage


@asynccontextmanager
async def _noop_lifespan(app):
    yield


_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
_engine = create_engine(f"sqlite:///{_tmp_db.name}")
Base.metadata.create_all(_engine)
_TestSession = sessionmaker(bind=_engine)


def _override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


_USER_ALICE = {"user_id": "alice", "email": "alice@nerdy.com", "name": "Alice"}
_USER_BOB = {"user_id": "bob", "email": "bob@nerdy.com", "name": "Bob"}
_current_user = {"v": _USER_ALICE}


def _override_user():
    return _current_user["v"]


@pytest.fixture(autouse=True)
def _clean_db():
    yield
    db = _TestSession()
    db.query(ConversationMessage).delete()
    db.query(BrandProfile).delete()
    db.commit()
    db.close()
    _current_user["v"] = _USER_ALICE


@pytest.fixture()
def client():
    from app.api.deps import get_current_user
    from app.api.main import app
    from app.db import get_db

    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_user
    with (
        patch("app.api.main.lifespan", _noop_lifespan),
        patch("app.api.routes.agent.init_db"),
    ):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Closure-binding property tests (GRILL Q2)
# ---------------------------------------------------------------------------


def test_toolbox_user_id_not_in_function_schema():
    """The function declarations sent to Gemini must NOT list ``user_id``
    as a parameter anywhere. This is the schema-level enforcement of the
    closure-binding rule from PJ-00 §3 decision 12.
    """
    decls = agent_loop.build_function_declarations()
    assert decls, "expected at least one tool declaration"
    for decl in decls:
        properties = (decl.get("parameters") or {}).get("properties") or {}
        assert "user_id" not in properties, (
            f"tool {decl['name']!r} leaks user_id to the LLM: {properties.keys()}"
        )


def test_toolbox_dispatch_strips_user_id_from_llm_args():
    """Even if a jailbroken model emits ``save_field(user_id='bob', ...)``,
    the ToolBox dispatcher filters ``user_id`` from the args and uses
    ``self.user_id`` (verified Clerk JWT). Cross-tenant write is impossible.
    """
    db = _TestSession()
    # PJ-05 dispatch enforces the whitelist using the profile's current
    # phase. Seed Alice in 'core' so save_field is on her whitelist.
    db.add(BrandProfile(user_id="alice", onboarding_phase="core"))
    # Bob exists so the test verifies a wrongful write would hit him.
    bob = BrandProfile(user_id="bob", business_name="Bob's Burgers")
    db.add(bob)
    db.commit()

    tb = ToolBox(user_id="alice", db=db, touchpoint="onboarding", session_id=None)
    # Model tries to set Bob's business_name. user_id is filtered.
    result = tb.dispatch(
        "save_field",
        {"user_id": "bob", "name": "business_name", "value": "Pwned"},
    )
    # PJ-05 contract: ok=True + stored field name on success.
    assert result.get("ok") is True
    assert result.get("field") == "business_name"

    # Alice got the write; Bob's row was NOT touched.
    db.refresh(bob)
    db_alice = db.query(BrandProfile).filter_by(user_id="alice").first()
    assert db_alice is not None
    assert db_alice.business_name == "Pwned"
    assert bob.business_name == "Bob's Burgers"
    db.close()


# ---------------------------------------------------------------------------
# Endpoint behavior
# ---------------------------------------------------------------------------


def test_first_converse_creates_profile(client):
    """Empty user → onboarding POST → brand_profile row inserted."""
    with patch(
        "app.api.routes.agent.run_conversation_turn",
        return_value={
            "assistant_message": "Hi! What's your business?",
            "exit_reason": "ask_user",
        },
    ):
        resp = client.post(
            "/api/agent/converse",
            json={"touchpoint": "onboarding", "user_message": None},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["phase"] == "identify"
    assert body["good_enough_now"] is False
    assert body["assistant_message"].startswith("Hi!")

    db = _TestSession()
    row = db.query(BrandProfile).filter_by(user_id="alice").one()
    assert row.onboarding_phase == "identify"
    db.close()


def test_converse_persists_user_and_assistant_messages(client):
    """One turn writes one user row and one assistant row."""
    with patch(
        "app.api.routes.agent.run_conversation_turn",
        return_value={
            "assistant_message": "Got it.",
            "exit_reason": "ask_user",
        },
    ):
        client.post(
            "/api/agent/converse",
            json={
                "touchpoint": "onboarding",
                "user_message": "I run a tutoring service.",
            },
        )

    db = _TestSession()
    rows = (
        db.query(ConversationMessage)
        .filter_by(user_id="alice", touchpoint="onboarding")
        .order_by(ConversationMessage.id)
        .all()
    )
    assert [r.role for r in rows] == ["user", "assistant"]
    assert rows[0].content == "I run a tutoring service."
    assert rows[1].content == "Got it."
    db.close()


def test_403_for_non_onboarding_without_profile(client):
    """Fresh user POSTs to ``post_session`` → 403 (must onboard first)."""
    resp = client.post(
        "/api/agent/converse",
        json={"touchpoint": "post_session", "session_id": "sess_xyz"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "brand_profile_not_initialized"


def test_invalid_touchpoint_returns_400(client):
    """A touchpoint not in the allowlist → 400."""
    resp = client.post(
        "/api/agent/converse",
        json={"touchpoint": "lol_invalid", "user_message": "hi"},
    )
    assert resp.status_code == 400


def test_history_loads_last_20_messages(client):
    """Seed 25 messages — only the 20 newest reach the loop."""
    db = _TestSession()
    db.add(BrandProfile(user_id="alice"))
    db.commit()
    for i in range(25):
        db.add(ConversationMessage(
            user_id="alice", touchpoint="onboarding",
            role="user" if i % 2 == 0 else "assistant",
            content=f"msg-{i:02d}",
        ))
    db.commit()
    db.close()

    captured = {}

    def fake_loop(toolbox, history, system_prompt, function_decls=None):
        captured["history_len"] = len(history)
        captured["first_msg"] = history[0]["content"] if history else None
        captured["last_msg"] = history[-1]["content"] if history else None
        return {"assistant_message": "ok", "exit_reason": "ask_user"}

    with patch("app.api.routes.agent.run_conversation_turn", side_effect=fake_loop):
        resp = client.post(
            "/api/agent/converse",
            json={"touchpoint": "onboarding", "user_message": "msg-NEW"},
        )
    assert resp.status_code == 200
    # 20 messages from seed + 1 just-persisted user message = capped at 20.
    assert captured["history_len"] == 20
    # The newest message ("msg-NEW") is in the slice.
    assert captured["last_msg"] == "msg-NEW"
    # The oldest of the slice is msg-06 (we dropped msg-00..msg-05).
    assert captured["first_msg"] == "msg-06"


# ---------------------------------------------------------------------------
# Loop invariants — max iteration cap (cost guard)
# ---------------------------------------------------------------------------


def test_empty_history_seeds_kickoff_message():
    """First-turn case: empty history + no user_message. The Gemini SDK
    rejects empty contents; the loop must seed a placeholder so the
    agent can greet from the system prompt."""
    # Build a fake response that calls ask_user terminally.
    def _fake_response():
        fake_part = SimpleNamespace(
            function_call=SimpleNamespace(
                name="ask_user",
                args={"message": "Hi! What's your business?"},
            )
        )
        return SimpleNamespace(
            candidates=[SimpleNamespace(content=SimpleNamespace(parts=[fake_part]))],
            text=None,
        )

    db = _TestSession()
    db.add(BrandProfile(user_id="alice", onboarding_phase="identify"))
    db.commit()
    tb = ToolBox(user_id="alice", db=db, touchpoint="onboarding", session_id=None)

    captured = {}

    def _capture(**kwargs):
        captured["contents"] = kwargs.get("contents")
        return _fake_response()

    with patch("google.genai.Client") as mock_ctor:
        with patch("app.api.agent.loop._agent_key", return_value="fake-key"):
            mock_client = MagicMock()
            mock_client.models.generate_content.side_effect = _capture
            mock_ctor.return_value = mock_client
            out = agent_loop.run_conversation_turn(tb, history=[], system_prompt="test")

    # Loop completed → SDK didn't reject with "contents required".
    assert out["exit_reason"] == "ask_user"
    assert captured["contents"], "loop should seed a kickoff message"
    assert len(captured["contents"]) >= 1
    db.close()


def test_max_iterations_caps_loop():
    """If the model never emits a terminal tool, the loop exits after 8
    iterations with a fallback message — not an infinite billable loop.
    """
    # Build a fake Gemini response that always emits a save_field call
    # (non-terminal) with a known field name.
    def _fake_response():
        fake_part = SimpleNamespace(
            function_call=SimpleNamespace(
                name="save_field",
                args={"name": "business_name", "value": "looping"},
            )
        )
        fake_content = SimpleNamespace(parts=[fake_part])
        fake_candidate = SimpleNamespace(content=fake_content)
        return SimpleNamespace(candidates=[fake_candidate], text=None)

    db = _TestSession()
    db.add(BrandProfile(user_id="alice"))
    db.commit()
    tb = ToolBox(user_id="alice", db=db, touchpoint="onboarding", session_id=None)

    with patch("google.genai.Client") as mock_client_ctor:
        with patch("app.api.agent.loop._agent_key", return_value="fake-key"):
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = _fake_response()
            mock_client_ctor.return_value = mock_client

            # Seed one history entry so contents isn't empty (the SDK requires
            # at least one content; an empty conversation hits an early-return
            # guard we don't care about in this test).
            history = [{"role": "user", "content": "hello"}]
            out = agent_loop.run_conversation_turn(
                tb, history=history, system_prompt="test"
            )

    assert out["exit_reason"] == "max_iter"
    assert out["iterations"] == agent_loop.MAX_TOOL_ITERATIONS == 8
    assert "stuck" in out["assistant_message"].lower()
    db.close()
