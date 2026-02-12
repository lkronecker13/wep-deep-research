"""Shared test fixtures for evaluation tests."""

import pandas as pd
import pytest

from research.evaluation.schemas import (
    EvaluationLabel,
    EvaluationResult,
    ExecutionMetadata,
)


@pytest.fixture
def sample_evaluation_result() -> EvaluationResult:
    """Sample passing evaluation result."""
    return EvaluationResult(
        test_id="test-001",
        agent_name="planning_agent",
        label=EvaluationLabel.PASS,
        explanation="The plan is comprehensive and well-structured.",
        evaluation_type="plan_quality",
        execution_metadata=ExecutionMetadata(
            duration_ms=1500.0,
            model_provider="anthropic",
            model_name="claude-sonnet-4-5",
        ),
    )


@pytest.fixture
def failing_evaluation_result() -> EvaluationResult:
    """Sample failing evaluation result."""
    return EvaluationResult(
        test_id="test-002",
        agent_name="gathering_agent",
        label=EvaluationLabel.FAIL,
        explanation="Sources lack credibility and depth.",
        evaluation_type="source_quality",
        execution_metadata=ExecutionMetadata(
            duration_ms=2100.0,
            model_provider="anthropic",
            model_name="claude-sonnet-4-5",
        ),
    )


@pytest.fixture
def mock_llm_result_pass() -> pd.DataFrame:
    """Mock DataFrame from llm_classify with PASS result."""
    return pd.DataFrame([{"label": "pass", "explanation": "Meets all quality criteria."}])


@pytest.fixture
def mock_llm_result_fail() -> pd.DataFrame:
    """Mock DataFrame from llm_classify with FAIL result."""
    return pd.DataFrame([{"label": "fail", "explanation": "Does not meet minimum standards."}])


@pytest.fixture
def mock_llm_result_invalid() -> pd.DataFrame:
    """Mock DataFrame with invalid label."""
    return pd.DataFrame([{"label": "maybe", "explanation": "Unclear result."}])
