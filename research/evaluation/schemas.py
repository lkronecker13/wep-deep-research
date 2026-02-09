"""Base Schemas for the Evaluation Framework.
Defines the base data structures for the Agent Evaluations using discrete labels
instead of numeric scores per LLM evaluation best practices."""

from datetime import datetime, timezone
from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Generic type variable for Agent input/output Eval Definition
AgentInput = TypeVar("AgentInput")
AgentOutput = TypeVar("AgentOutput", bound=BaseModel)

# Evaluation Result Label Definition


class EvaluationLabel(str, Enum):
    """Establish discrete binary classification labels for LLM-as-a-Judge evaluations.

    Following best practices, we avoid numeric scores in favor of categorical labels.
    - Clear decision boundaries help LLMs make consistent judgments.
    - Binary labels reduce ambiguity compared to numeric scores.
    - Higher inter-rater reliability is observed with discrete labels.
    """

    PASS = "pass"
    FAIL = "fail"

    @property
    def passed(self) -> bool:
        """Check if the evaluation label indicates a passing result."""
        return self == EvaluationLabel.PASS


# Test Priority Definition


class TestPriority(str, Enum):
    """Priority levels for test cases in QA workflows."""

    P0 = "blocker"
    P1 = "critical"
    P2 = "high"
    P3 = "medium"
    P4 = "low"


# Runtime Execution Metadata Definition


class ExecutionMetadata(BaseModel):
    """Runtime execution metrics for cost and performance tracking."""

    model_config = ConfigDict(frozen=True)
    duration_ms: float = Field(ge=0, description="Execution time in milliseconds")
    input_tokens: int | None = Field(default=None, ge=0, description="Input token count")
    output_tokens: int | None = Field(default=None, ge=0, description="Output token count")
    cost_usd: float | None = Field(default=None, ge=0, description="Estimated cost in USD")
    model_provider: str = Field(min_length=1, max_length=50, description="Model provider (e.g., 'anthropic', 'google')")
    model_name: str = Field(min_length=1, max_length=100, description="Model name (e.g., 'claude-sonnet-4-5')")


# Evaluation Result Addition


class EvaluationResult(BaseModel):
    """Result from a single LLM-as-a-Judge evaluation."""

    test_id: str = Field(min_length=1, max_length=255, description="Unique identifier for the evaluation test case.")
    agent_name: str = Field(min_length=1, max_length=100, description="Name of the agent being evaluated.")
    label: EvaluationLabel = Field(description="The binary evaluation label (pass/fail).")
    explanation: str = Field(
        min_length=1, max_length=2000, description="LLM-generated explanation for the assigned label."
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of when the evaluation was performed.",
    )
    evaluation_type: str = Field(min_length=1, max_length=255, description="Type of evaluation performed.")

    # Phoenix trace correlation ID for distributed tracing
    trace_id: str | None = Field(default=None, description="Unique trace identifier for correlating logs and traces.")
    span_id: str | None = Field(
        default=None, description="Span identifier for detailed traceability within distributed systems."
    )
    execution_metadata: ExecutionMetadata | None = Field(
        default=None, description="Runtime execution metadata for the evaluation process."
    )

    # Error handling for debugging
    error_message: str | None = Field(default=None, max_length=1000, description="Error message if evaluation failed")
    stack_trace: str | None = Field(default=None, max_length=5000, description="Stack trace for debugging")

    @property
    def passed(self) -> bool:
        """Check if the evaluation result indicates a passing outcome."""
        return self.label.passed


# Generic Base Evaluation Definition


class BaseEvalCase(BaseModel, Generic[AgentInput, AgentOutput]):
    """Base Evaluation Case Schema for any Agent Evaluation."""

    test_id: str = Field(min_length=1, max_length=255, description="Unique identifier for the evaluation test case.")
    description: str = Field(min_length=1, max_length=255, description="Description of the evaluation case.")
    input: AgentInput = Field(description="Input provided to the agent for evaluation.")
    expected_output: AgentOutput | None = Field(
        default=None, description="Expected output from the agent for the given input (Ground Truth)."
    )
    evaluation_criteria: str = Field(
        min_length=1, max_length=255, description="Criteria used for evaluating the agent's output."
    )

    # QA workflow fields
    priority: TestPriority = Field(default=TestPriority.P3, description="Test case priority for triage")
    tags: list[str] = Field(
        default_factory=list, description="Tags for categorization (e.g., 'smoke', 'regression', 'edge-case')"
    )
    enabled: bool = Field(default=True, description="Whether this test case is active in the suite")

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Ensure tags are lowercase and trimmed."""
        return [tag.lower().strip() for tag in v if tag.strip()]


# Evaluation Dataset Definition


class EvalDataset(BaseModel, Generic[AgentInput, AgentOutput]):
    """Schema for evaluation cases collection for regression testing."""

    name: str = Field(min_length=1, max_length=255, description="Name of the evaluation dataset.")
    description: str = Field(description="Description and purpose of the evaluation dataset.")
    eval_cases: list[BaseEvalCase[AgentInput, AgentOutput]] = Field(
        default_factory=list, description="List of evaluation cases in the dataset."
    )

    @model_validator(mode="after")
    def validate_unique_test_ids(self) -> "EvalDataset":
        """Ensure all test_ids are unique within the dataset."""
        test_ids = [tc.test_id for tc in self.eval_cases]
        duplicates = [tid for tid in test_ids if test_ids.count(tid) > 1]
        if duplicates:
            raise ValueError(f"Duplicate test_ids found: {set(duplicates)}")
        return self

    def get_by_id(self, test_id: str) -> BaseEvalCase[AgentInput, AgentOutput] | None:
        """Find a test case by its ID."""
        return next((tc for tc in self.eval_cases if tc.test_id == test_id), None)

    def get_enabled_cases(self) -> list[BaseEvalCase[AgentInput, AgentOutput]]:
        """Get only enabled test cases."""
        return [tc for tc in self.eval_cases if tc.enabled]

    def filter_by_priority(self, priority: TestPriority) -> list[BaseEvalCase[AgentInput, AgentOutput]]:
        """Filter test cases by priority (enabled only)."""
        return [tc for tc in self.eval_cases if tc.priority == priority and tc.enabled]

    def filter_by_tag(self, tag: str) -> list[BaseEvalCase[AgentInput, AgentOutput]]:
        """Filter test cases by tag (enabled only)."""
        return [tc for tc in self.eval_cases if tag.lower() in tc.tags and tc.enabled]
