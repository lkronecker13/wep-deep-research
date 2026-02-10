"""Evaluation framework for LLM-as-a-Judge agent evaluations.

Uses discrete PASS/FAIL labels per LLM evaluation best practices.
Integrates with Arize Phoenix for observability and tracing.
"""

from research.evaluation.datasets import (
    ConsultingDomain,
    ProductionEvalQuestion,
    get_critical_subset,
    get_domain_questions,
    get_production_dataset,
    get_questions_by_priority,
    get_questions_by_tag,
    get_smoke_test_subset,
)
from research.evaluation.evaluators import (
    EvaluatorConfig,
    evaluate_gathering,
    evaluate_plan,
    evaluate_synthesis,
    evaluate_verification,
)
from research.evaluation.export import (
    EvaluationRunSummary,
    export_evaluation_results,
)
from research.evaluation.schemas import (
    EvaluationLabel,
    EvaluationResult,
    ExecutionMetadata,
    TestPriority,
)

__all__ = [
    # Evaluator functions
    "evaluate_plan",
    "evaluate_gathering",
    "evaluate_synthesis",
    "evaluate_verification",
    "EvaluatorConfig",
    # Schemas
    "EvaluationLabel",
    "EvaluationResult",
    "ExecutionMetadata",
    "TestPriority",
    # Export
    "EvaluationRunSummary",
    "export_evaluation_results",
    # Datasets
    "ConsultingDomain",
    "ProductionEvalQuestion",
    "get_production_dataset",
    "get_smoke_test_subset",
    "get_critical_subset",
    "get_domain_questions",
    "get_questions_by_tag",
    "get_questions_by_priority",
]
