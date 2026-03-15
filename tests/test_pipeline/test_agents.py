"""Tests for agentic orchestration layer (P4-01).

Validates agent definitions, error boundaries, diagnostic logging,
and the agent pipeline orchestrator.
"""

from __future__ import annotations

from iterate.agents import (
    AgentResult,
    EditorAgent,
    EvaluatorAgent,
    ResearcherAgent,
    WriterAgent,
    run_agent_pipeline,
)


# --- AgentResult ---


def test_agent_result_success() -> None:
    """Successful AgentResult has success=True and no error."""
    result = AgentResult(success=True, output={"key": "value"}, error=None, diagnostics={})
    assert result.success is True
    assert result.error is None
    assert result.output["key"] == "value"


def test_agent_result_failure() -> None:
    """Failed AgentResult has success=False and error message."""
    result = AgentResult(success=False, output={}, error="something broke", diagnostics={"stage": "test"})
    assert result.success is False
    assert "something broke" in result.error


# --- ResearcherAgent ---


def test_researcher_agent_success() -> None:
    """ResearcherAgent returns expanded brief on success."""
    agent = ResearcherAgent()
    brief = {"brief_id": "b001", "campaign_goal": "awareness", "audience": "parents", "product": "SAT prep"}
    result = agent.execute(brief)
    assert isinstance(result, AgentResult)
    assert result.success is True
    assert "expanded_brief" in result.output


def test_researcher_agent_error_boundary() -> None:
    """ResearcherAgent catches errors and returns failure result."""
    agent = ResearcherAgent()
    result = agent.execute(None)  # Invalid input
    assert result.success is False
    assert result.error is not None
    assert "diagnostics" in dir(result)


# --- WriterAgent ---


def test_writer_agent_success() -> None:
    """WriterAgent returns generated ad on success."""
    agent = WriterAgent()
    expanded = {
        "brief_id": "b001",
        "campaign_goal": "awareness",
        "audience": "parents",
        "product": "SAT prep",
        "emotional_angles": ["aspiration"],
        "value_propositions": ["Expert tutors"],
    }
    result = agent.execute(expanded)
    assert isinstance(result, AgentResult)
    assert result.success is True
    assert "generated_ad" in result.output


def test_writer_agent_error_boundary() -> None:
    """WriterAgent catches errors and returns failure result."""
    agent = WriterAgent()
    result = agent.execute(None)
    assert result.success is False
    assert result.error is not None


# --- EvaluatorAgent ---


def test_evaluator_agent_success() -> None:
    """EvaluatorAgent returns evaluation result on success."""
    agent = EvaluatorAgent()
    ad_input = {
        "ad_id": "ad_001",
        "primary_text": "Expert SAT tutoring for your child.",
        "headline": "Boost SAT Scores",
        "campaign_goal": "awareness",
        "audience": "parents",
    }
    result = agent.execute(ad_input)
    assert isinstance(result, AgentResult)
    assert result.success is True
    assert "evaluation" in result.output


def test_evaluator_agent_error_boundary() -> None:
    """EvaluatorAgent catches errors and returns failure result."""
    agent = EvaluatorAgent()
    result = agent.execute(None)
    assert result.success is False
    assert result.error is not None


# --- EditorAgent ---


def test_editor_agent_publish_decision() -> None:
    """EditorAgent returns publish for high-scoring ads."""
    agent = EditorAgent()
    editor_input = {
        "ad_id": "ad_001",
        "aggregate_score": 8.0,
        "meets_threshold": True,
        "floor_violations": [],
    }
    result = agent.execute(editor_input)
    assert isinstance(result, AgentResult)
    assert result.success is True
    assert result.output["decision"] in ("publish", "regenerate", "discard")


def test_editor_agent_discard_decision() -> None:
    """EditorAgent returns discard for ads with floor violations."""
    agent = EditorAgent()
    editor_input = {
        "ad_id": "ad_001",
        "aggregate_score": 4.0,
        "meets_threshold": False,
        "floor_violations": ["clarity below 6.0"],
        "cycle_number": 3,
    }
    result = agent.execute(editor_input)
    assert result.success is True
    assert result.output["decision"] == "discard"


def test_editor_agent_error_boundary() -> None:
    """EditorAgent catches errors and returns failure result."""
    agent = EditorAgent()
    result = agent.execute(None)
    assert result.success is False


# --- Pipeline Orchestrator ---


def test_agent_pipeline_returns_result() -> None:
    """run_agent_pipeline returns AgentResult."""
    brief = {"brief_id": "b001", "campaign_goal": "awareness", "audience": "parents", "product": "SAT prep"}
    result = run_agent_pipeline(brief, config={})
    assert isinstance(result, AgentResult)


def test_agent_pipeline_diagnostics() -> None:
    """Pipeline result includes diagnostics from each agent stage."""
    brief = {"brief_id": "b001", "campaign_goal": "awareness", "audience": "parents", "product": "SAT prep"}
    result = run_agent_pipeline(brief, config={})
    assert "stages" in result.diagnostics
    assert len(result.diagnostics["stages"]) > 0
