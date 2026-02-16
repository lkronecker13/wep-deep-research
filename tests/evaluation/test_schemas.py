"""Unit tests for evaluation schemas and data models."""

import pytest
from pydantic import ValidationError

from research.evaluation.schemas import (
    EvaluationLabel,
    EvaluationResult,
    ExecutionMetadata,
)


class TestEvaluationLabel:
    """Tests for EvaluationLabel enum."""

    def test__evaluation_label__pass_has_passed_property_true(self):
        """PASS label should have passed=True property."""
        assert EvaluationLabel.PASS.passed is True

    def test__evaluation_label__fail_has_passed_property_false(self):
        """FAIL label should have passed=False property."""
        assert EvaluationLabel.FAIL.passed is False


class TestExecutionMetadata:
    """Tests for ExecutionMetadata validation."""

    def test__execution_metadata__validates_positive_duration(self):
        """Duration must be non-negative."""
        metadata = ExecutionMetadata(
            duration_ms=100.0,
            model_provider="anthropic",
            model_name="claude-sonnet-4-5",
        )
        assert metadata.duration_ms == 100.0

    def test__execution_metadata__rejects_negative_duration(self):
        """Negative duration should raise validation error."""
        with pytest.raises(ValidationError):
            ExecutionMetadata(
                duration_ms=-100.0,
                model_provider="anthropic",
                model_name="claude-sonnet-4-5",
            )

    def test__execution_metadata__validates_token_counts(self):
        """Token counts must be non-negative if provided."""
        metadata = ExecutionMetadata(
            duration_ms=100.0,
            input_tokens=500,
            output_tokens=200,
            model_provider="anthropic",
            model_name="claude-sonnet-4-5",
        )
        assert metadata.input_tokens == 500
        assert metadata.output_tokens == 200


class TestEvaluationResult:
    """Tests for EvaluationResult model."""

    def test__evaluation_result__passed_property_reflects_label(
        self, sample_evaluation_result, failing_evaluation_result
    ):
        """passed property should match the label."""
        assert sample_evaluation_result.passed is True
        assert failing_evaluation_result.passed is False

    def test__evaluation_result__requires_minimum_fields(self):
        """Minimum required fields should create valid result."""
        result = EvaluationResult(
            test_id="test-001",
            agent_name="test_agent",
            label=EvaluationLabel.PASS,
            explanation="Test explanation.",
            evaluation_type="test_type",
        )
        assert result.test_id == "test-001"
        assert result.passed is True

    def test__evaluation_result__truncates_long_explanation(self):
        """Explanations longer than 2000 chars should be rejected."""
        long_explanation = "x" * 2001
        with pytest.raises(ValidationError):
            EvaluationResult(
                test_id="test-001",
                agent_name="test_agent",
                label=EvaluationLabel.PASS,
                explanation=long_explanation,
                evaluation_type="test_type",
            )
