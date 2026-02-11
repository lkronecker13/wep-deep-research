"""Unit tests for evaluator helper functions."""

import pandas as pd
import pytest

from research.evaluation.evaluators import (
    EvaluatorConfig,
    _create_error_result,
    _parse_llm_result,
)
from research.evaluation.schemas import EvaluationLabel


class TestParseLLMResult:
    """Tests for _parse_llm_result helper function."""

    def test__parse_llm_result__handles_valid_pass_label(self, mock_llm_result_pass):
        """Should correctly parse PASS label."""
        label, explanation, error = _parse_llm_result(mock_llm_result_pass)
        assert label == EvaluationLabel.PASS
        assert explanation == "Meets all quality criteria."
        assert error is None

    def test__parse_llm_result__handles_valid_fail_label(self, mock_llm_result_fail):
        """Should correctly parse FAIL label."""
        label, explanation, error = _parse_llm_result(mock_llm_result_fail)
        assert label == EvaluationLabel.FAIL
        assert explanation == "Does not meet minimum standards."
        assert error is None

    def test__parse_llm_result__handles_invalid_label(self, mock_llm_result_invalid):
        """Should default to FAIL for invalid labels."""
        label, explanation, error = _parse_llm_result(mock_llm_result_invalid)
        assert label == EvaluationLabel.FAIL
        assert "invalid label" in error.lower()

    def test__parse_llm_result__handles_nan_explanation(self):
        """Should provide default explanation for NaN."""
        df = pd.DataFrame([{"label": "pass", "explanation": pd.NA}])
        label, explanation, error = _parse_llm_result(df)
        assert explanation == "No explanation provided by the LLM."

    def test__parse_llm_result__truncates_long_explanation(self):
        """Should truncate explanations to 2000 characters."""
        long_text = "x" * 3000
        df = pd.DataFrame([{"label": "pass", "explanation": long_text}])
        label, explanation, error = _parse_llm_result(df)
        assert len(explanation) == 2000


class TestCreateErrorResult:
    """Tests for _create_error_result helper function."""

    def test__create_error_result__builds_valid_result(self):
        """Should construct valid error result with all fields."""
        from time import perf_counter

        start_time = perf_counter()
        config = EvaluatorConfig()
        error = ValueError("Test error")

        result = _create_error_result(
            start_time=start_time,
            test_id="test-001",
            agent_name="test_agent",
            evaluation_type="test_type",
            config=config,
            span_id="span-123",
            error=error,
        )

        assert result.test_id == "test-001"
        assert result.agent_name == "test_agent"
        assert result.label == EvaluationLabel.FAIL
        assert "Test error" in result.explanation
        assert result.error_message == "Test error"
        assert result.stack_trace is not None
        assert result.execution_metadata is not None


class TestEvaluatorConfig:
    """Tests for EvaluatorConfig model."""

    def test__evaluator_config__has_correct_defaults(self):
        """Should use expected default values."""
        config = EvaluatorConfig()
        assert config.model_provider == "anthropic"
        assert config.model_name == "claude-sonnet-4-5"
        assert config.temperature == 0.0
        assert config.log_to_arize is True

    def test__evaluator_config__is_immutable(self):
        """Should be frozen and prevent mutation."""
        config = EvaluatorConfig()
        with pytest.raises(Exception):  # Pydantic raises ValidationError or AttributeError
            config.temperature = 0.5
