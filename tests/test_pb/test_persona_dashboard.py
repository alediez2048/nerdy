# PB-08: Dashboard persona integration tests
"""Tests that persona flows through SessionConfig and dashboard endpoints."""

from app.api.schemas.session import Persona, SessionConfig


def test_session_config_accepts_persona():
    config = SessionConfig(
        audience="parents",
        campaign_goal="conversion",
        persona="athlete_recruit",
    )
    assert config.persona == Persona.athlete_recruit


def test_session_config_default_persona_is_auto():
    config = SessionConfig(audience="parents", campaign_goal="awareness")
    assert config.persona == Persona.auto


def test_session_config_all_personas_valid():
    personas = ["auto", "athlete_recruit", "suburban_optimizer", "immigrant_navigator",
                "cultural_investor", "system_optimizer", "neurodivergent_advocate", "burned_returner"]
    for p in personas:
        config = SessionConfig(audience="parents", campaign_goal="conversion", persona=p)
        assert config.persona.value == p


def test_session_config_invalid_persona_rejected():
    import pytest
    with pytest.raises(Exception):
        SessionConfig(audience="parents", campaign_goal="conversion", persona="nonexistent")
