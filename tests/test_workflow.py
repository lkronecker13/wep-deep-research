"""Tests for research workflow orchestration."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from src.exceptions import GatheringError, PlanningError, SynthesisError, VerificationError
from src.models import (
    PhaseTimings,
    ResearchPlan,
    ResearchReport,
    ResearchResult,
    SearchResult,
    SearchStep,
    ValidationResult,
)
from src.workflow import run_research_workflow

# --- Fixture Factories ---


def _make_plan_agent() -> Agent[None, ResearchPlan]:
    """Create test agent for planning phase."""
    plan = ResearchPlan(
        executive_summary="Test summary",
        web_search_steps=[
            SearchStep(search_terms="query1", purpose="purpose1"),
            SearchStep(search_terms="query2", purpose="purpose2"),
        ],
        analysis_instructions="Test instructions",
    )
    return Agent(TestModel(custom_output_args=plan.model_dump()), output_type=ResearchPlan)


def _make_gathering_agent() -> Agent[None, SearchResult]:
    """Create test agent for gathering phase."""
    result = SearchResult(query="test", findings=["finding1"], sources=["source1"])
    return Agent(TestModel(custom_output_args=result.model_dump()), output_type=SearchResult)


def _make_synthesis_agent() -> Agent[None, ResearchReport]:
    """Create test agent for synthesis phase."""
    report = ResearchReport(title="Test Report", summary="Test summary", key_findings=["kf1"], sources=["src1"])
    return Agent(TestModel(custom_output_args=report.model_dump()), output_type=ResearchReport)


def _make_verification_agent() -> Agent[None, ValidationResult]:
    """Create test agent for verification phase."""
    validation = ValidationResult(is_valid=True, confidence_score=0.9)
    return Agent(TestModel(custom_output_args=validation.model_dump()), output_type=ValidationResult)


# --- Tests ---


@pytest.mark.asyncio
async def test__full_pipeline__returns_research_result() -> None:
    result = await run_research_workflow(
        "test query",
        plan_agent=_make_plan_agent(),
        gathering_agent=_make_gathering_agent(),
        synthesis_agent=_make_synthesis_agent(),
        verification_agent=_make_verification_agent(),
    )
    assert isinstance(result, ResearchResult)
    assert result.query == "test query"
    assert result.plan.executive_summary == "Test summary"
    assert len(result.search_results) == 2
    assert result.report.title == "Test Report"
    assert result.validation.is_valid is True


@pytest.mark.asyncio
async def test__full_pipeline__returns_correct_timings() -> None:
    result = await run_research_workflow(
        "test query",
        plan_agent=_make_plan_agent(),
        gathering_agent=_make_gathering_agent(),
        synthesis_agent=_make_synthesis_agent(),
        verification_agent=_make_verification_agent(),
    )
    assert isinstance(result.timings, PhaseTimings)
    assert result.timings.planning_ms >= 0
    assert result.timings.gathering_ms >= 0
    assert result.timings.synthesis_ms >= 0
    assert result.timings.verification_ms >= 0
    assert result.timings.total_ms >= 0


@pytest.mark.asyncio
async def test__full_pipeline__returns_query_in_result() -> None:
    result = await run_research_workflow(
        "my custom query",
        plan_agent=_make_plan_agent(),
        gathering_agent=_make_gathering_agent(),
        synthesis_agent=_make_synthesis_agent(),
        verification_agent=_make_verification_agent(),
    )
    assert result.query == "my custom query"


@pytest.mark.asyncio
async def test__planning_failure__raises_planning_error() -> None:
    # Create an agent whose run method raises
    plan_agent = _make_plan_agent()
    plan_agent.run = AsyncMock(side_effect=RuntimeError("Plan failed"))

    with pytest.raises(PlanningError, match="Plan failed"):
        await run_research_workflow(
            "test query",
            plan_agent=plan_agent,
            gathering_agent=_make_gathering_agent(),
            synthesis_agent=_make_synthesis_agent(),
            verification_agent=_make_verification_agent(),
        )


@pytest.mark.asyncio
async def test__all_gathering_fails__raises_gathering_error() -> None:
    # Create an agent that raises on every search
    gathering_agent = _make_gathering_agent()
    gathering_agent.run = AsyncMock(side_effect=RuntimeError("Search failed"))

    with pytest.raises(GatheringError):
        await run_research_workflow(
            "test query",
            plan_agent=_make_plan_agent(),
            gathering_agent=gathering_agent,
            synthesis_agent=_make_synthesis_agent(),
            verification_agent=_make_verification_agent(),
        )


@pytest.mark.asyncio
async def test__partial_gathering_failure__succeeds_with_available_results() -> None:
    # Create an agent that fails on first call, succeeds on second
    gathering_agent = _make_gathering_agent()
    call_count = 0

    async def _run_with_partial_failure(*args: Any, **kwargs: Any) -> Any:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("First search failed")
        # Second call succeeds
        result = SearchResult(query="test", findings=["finding"], sources=["source"])
        return type("RunResult", (), {"output": result})()

    gathering_agent.run = AsyncMock(side_effect=_run_with_partial_failure)

    result = await run_research_workflow(
        "test query",
        plan_agent=_make_plan_agent(),
        gathering_agent=gathering_agent,
        synthesis_agent=_make_synthesis_agent(),
        verification_agent=_make_verification_agent(),
    )
    # Should succeed with 1 result
    assert len(result.search_results) == 1


@pytest.mark.asyncio
async def test__synthesis_failure__raises_synthesis_error() -> None:
    synthesis_agent = _make_synthesis_agent()
    synthesis_agent.run = AsyncMock(side_effect=RuntimeError("Synthesis failed"))

    with pytest.raises(SynthesisError, match="Synthesis failed"):
        await run_research_workflow(
            "test query",
            plan_agent=_make_plan_agent(),
            gathering_agent=_make_gathering_agent(),
            synthesis_agent=synthesis_agent,
            verification_agent=_make_verification_agent(),
        )


@pytest.mark.asyncio
async def test__verification_failure__raises_verification_error() -> None:
    verification_agent = _make_verification_agent()
    verification_agent.run = AsyncMock(side_effect=RuntimeError("Verification failed"))

    with pytest.raises(VerificationError, match="Verification failed"):
        await run_research_workflow(
            "test query",
            plan_agent=_make_plan_agent(),
            gathering_agent=_make_gathering_agent(),
            synthesis_agent=_make_synthesis_agent(),
            verification_agent=verification_agent,
        )


@pytest.mark.asyncio
async def test__default_agents__used_when_none_provided() -> None:
    with (
        patch("src.workflow.get_plan_agent", return_value=_make_plan_agent()) as mock_plan,
        patch("src.workflow.get_gathering_agent", return_value=_make_gathering_agent()) as mock_gathering,
        patch("src.workflow.get_synthesis_agent", return_value=_make_synthesis_agent()) as mock_synthesis,
        patch("src.workflow.get_verification_agent", return_value=_make_verification_agent()) as mock_verification,
    ):
        await run_research_workflow("test query")

        mock_plan.assert_called_once()
        mock_gathering.assert_called_once()
        mock_synthesis.assert_called_once()
        mock_verification.assert_called_once()


@pytest.mark.asyncio
async def test__custom_agents__override_defaults() -> None:
    with (
        patch("src.workflow.get_plan_agent") as mock_plan,
        patch("src.workflow.get_gathering_agent") as mock_gathering,
        patch("src.workflow.get_synthesis_agent") as mock_synthesis,
        patch("src.workflow.get_verification_agent") as mock_verification,
    ):
        # Inject custom agents
        await run_research_workflow(
            "test query",
            plan_agent=_make_plan_agent(),
            gathering_agent=_make_gathering_agent(),
            synthesis_agent=_make_synthesis_agent(),
            verification_agent=_make_verification_agent(),
        )

        # Default getters should NOT be called
        mock_plan.assert_not_called()
        mock_gathering.assert_not_called()
        mock_synthesis.assert_not_called()
        mock_verification.assert_not_called()
