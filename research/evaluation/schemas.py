"""Schemas for LLM-as-a-Judge evaluation results.

Simple, concrete schemas for evaluating the 4-agent research workflow.
No generic abstractions - just the models we actually use.
"""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class EvaluationLabel(str, Enum):
    """Binary pass/fail labels for LLM-as-a-Judge evaluations.

    Following best practices, we use discrete labels instead of numeric scores
    for clearer decision boundaries and higher inter-rater reliability.
    """

    PASS = "pass"
    FAIL = "fail"

    @property
    def passed(self) -> bool:
        """Check if the evaluation label indicates a passing result."""
        return self == EvaluationLabel.PASS


class TestPriority(str, Enum):
    """Priority levels for test cases."""

    P0 = "blocker"
    P1 = "critical"
    P2 = "high"
    P3 = "medium"
    P4 = "low"


class ExecutionMetadata(BaseModel):
    """Runtime execution metrics for cost and performance tracking."""

    model_config = ConfigDict(frozen=True)
    duration_ms: float = Field(ge=0, description="Execution time in milliseconds")
    input_tokens: int | None = Field(default=None, ge=0, description="Input token count")
    output_tokens: int | None = Field(default=None, ge=0, description="Output token count")
    cost_usd: float | None = Field(default=None, ge=0, description="Estimated cost in USD")
    model_provider: str = Field(min_length=1, max_length=50, description="Model provider (e.g., 'anthropic', 'google')")
    model_name: str = Field(min_length=1, max_length=100, description="Model name (e.g., 'claude-sonnet-4-5')")


class EvaluationResult(BaseModel):
    """Result from a single LLM-as-a-Judge evaluation."""

    test_id: str = Field(min_length=1, max_length=255, description="Unique identifier for the evaluation test case")
    agent_name: str = Field(min_length=1, max_length=100, description="Name of the agent being evaluated")
    label: EvaluationLabel = Field(description="The binary evaluation label (pass/fail)")
    explanation: str = Field(min_length=1, max_length=2000, description="LLM-generated explanation for the label")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of when the evaluation was performed",
    )
    evaluation_type: str = Field(min_length=1, max_length=255, description="Type of evaluation performed")

    # Phoenix trace correlation for distributed tracing
    trace_id: str | None = Field(default=None, description="Unique trace identifier for correlating logs and traces")
    span_id: str | None = Field(default=None, description="Span identifier for detailed traceability")
    execution_metadata: ExecutionMetadata | None = Field(default=None, description="Runtime execution metadata")

    # Error handling for debugging
    error_message: str | None = Field(default=None, max_length=1000, description="Error message if evaluation failed")
    stack_trace: str | None = Field(default=None, max_length=5000, description="Stack trace for debugging")

    @property
    def passed(self) -> bool:
        """Check if the evaluation result indicates a passing outcome."""
        return self.label.passed
