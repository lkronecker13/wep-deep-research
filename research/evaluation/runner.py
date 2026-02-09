"""CLI runner for evaluation suite execution with Arize Phoenix Cloud integration.

Provides functionality to run evaluations across the production dataset
with support for filtering by domain, priority, and parallel execution.
All traces, spans, and evaluations are logged to Arize Phoenix Cloud.

Environment Variables (configured in .env):
    PHOENIX_API_KEY: Your Arize Cloud API key
    ANTHROPIC_API_KEY: For Claude-based evaluations
    GEMINI_API_KEY: For Gemini-based research gathering
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv

# Load environment variables first
load_dotenv()


def _init_phoenix_tracing() -> bool:
    """Initialize Phoenix OpenTelemetry tracing for Arize Cloud.

    Phoenix Client automatically reads PHOENIX_API_KEY and PHOENIX_COLLECTOR_ENDPOINT
    from environment variables.

    Returns:
        True if tracing was initialized successfully, False otherwise.
    """
    try:
        from phoenix.otel import register

        # Check if API key is configured
        if not os.environ.get("PHOENIX_API_KEY"):
            print("WARNING: PHOENIX_API_KEY not set. Evaluations will not be logged to Arize Cloud.")
            return False

        # Register the tracer provider (Phoenix reads endpoint from env automatically)
        tracer_provider = register(project_name="deep-research-evals")

        # Enable instrumentors for LLM libraries
        _enable_instrumentors(tracer_provider)

        print("Phoenix tracing initialized for Arize Cloud")
        return True

    except ImportError as e:
        print(f"WARNING: Phoenix tracing not available: {e}")
        return False
    except Exception as e:
        print(f"WARNING: Failed to initialize Phoenix tracing: {e}")
        return False


def _enable_instrumentors(tracer_provider: object) -> None:
    """Enable OpenInference instrumentors for agents and LLM libraries.

    Args:
        tracer_provider: The OpenTelemetry tracer provider from Phoenix.
    """
    # Note: PydanticAI uses InstrumentationSettings(version=2) on agents directly
    # The openinference-instrumentation-pydantic-ai package provides OpenInferenceSpanProcessor
    # but it conflicts with async TaskGroup execution, so we rely on the native instrumentation
    print("  - PydanticAI native instrumentation enabled (via InstrumentationSettings on agents)")

    # Instrument Anthropic (Claude)
    try:
        from openinference.instrumentation.anthropic import AnthropicInstrumentor

        AnthropicInstrumentor().instrument(tracer_provider=tracer_provider)
        print("  - Anthropic instrumentation enabled")
    except ImportError:
        print("  - Anthropic instrumentation not available (install openinference-instrumentation-anthropic)")
    except Exception as e:
        print(f"  - Anthropic instrumentation failed: {e}")

    # Instrument Google GenAI (Gemini)
    try:
        from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

        GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)
        print("  - Google GenAI instrumentation enabled")
    except ImportError:
        print("  - Google GenAI instrumentation not available (install openinference-instrumentation-google-genai)")
    except Exception as e:
        print(f"  - Google GenAI instrumentation failed: {e}")


# Initialize tracing at module load
_TRACING_ENABLED = _init_phoenix_tracing()

# Now import the rest after tracing is set up
# ruff: noqa: E402 - Imports must be after Phoenix tracing initialization
from research.evaluation.datasets import (
    ConsultingDomain,
    ProductionEvalQuestion,
    get_critical_subset,
    get_domain_questions,
    get_production_dataset,
    get_smoke_test_subset,
)
from research.evaluation.evaluators import (
    EvaluatorConfig,
    evaluate_gathering,
    evaluate_plan,
    evaluate_synthesis,
    evaluate_verification,
)
from research.evaluation.export import EvaluationRunSummary, export_evaluation_results
from research.evaluation.schemas import EvaluationLabel, EvaluationResult, ExecutionMetadata, TestPriority
from research.models import ResearchPlan, ResearchReport, SearchResult, ValidationResult
from research.run_research import run_research


async def run_single_evaluation(
    question: ProductionEvalQuestion,
    config: EvaluatorConfig | None = None,
) -> list[EvaluationResult]:
    """Run full research pipeline and evaluate all 4 agents for one question.

    The research workflow and evaluations are traced and logged to Arize Cloud
    when PHOENIX_API_KEY is configured.

    Args:
        question: The evaluation question to run.
        config: Optional evaluator configuration.

    Returns:
        List of EvaluationResults (one per agent, plus one per search result).
    """
    if config is None:
        # Enable Arize logging if tracing is enabled
        config = EvaluatorConfig(log_to_arize=_TRACING_ENABLED)

    results: list[EvaluationResult] = []

    print(f"\n{'=' * 60}")
    print(f"Running: {question.id} ({question.domain.value})")
    print(f"Priority: {question.priority.value}")
    print(f"Query: {question.query[:80]}...")
    print(f"{'=' * 60}")

    try:
        # Run the research workflow (auto-instrumented by Phoenix)
        workflow_result = await run_research(question.query)

        # Reconstruct pydantic models from dicts
        plan = ResearchPlan(**workflow_result["plan"])
        search_results = [SearchResult(**sr) for sr in workflow_result["search_results"]]
        report = ResearchReport(**workflow_result["report"])
        validation = ValidationResult(**workflow_result["validation"])

        # Evaluate planning agent
        print("  Evaluating planning agent...")
        plan_eval = evaluate_plan(
            plan=plan,
            query=question.query,
            test_id=question.id,
            config=config,
        )
        results.append(plan_eval)
        _print_eval_result("Plan", plan_eval)

        # Evaluate gathering agent (one eval per search result)
        for i, sr in enumerate(search_results):
            print(f"  Evaluating gathering agent (search {i + 1}/{len(search_results)})...")
            gathering_eval = evaluate_gathering(
                search_result=sr,
                test_id=f"{question.id}_gather_{i}",
                config=config,
            )
            results.append(gathering_eval)
            _print_eval_result(f"Gather {i + 1}", gathering_eval)

        # Evaluate synthesis agent
        print("  Evaluating synthesis agent...")
        synthesis_eval = evaluate_synthesis(
            report=report,
            query=question.query,
            test_id=question.id,
            config=config,
        )
        results.append(synthesis_eval)
        _print_eval_result("Synthesis", synthesis_eval)

        # Evaluate verification agent
        print("  Evaluating verification agent...")
        verification_eval = evaluate_verification(
            validation=validation,
            report=report,
            test_id=question.id,
            config=config,
        )
        results.append(verification_eval)
        _print_eval_result("Verification", verification_eval)

        # Summary for this question
        passed = sum(1 for r in results if r.passed)
        print(f"\n  Summary: {passed}/{len(results)} evaluations passed")

    except Exception as e:
        print(f"  ERROR: {e}")
        # Create a failed result for the workflow
        error_result = EvaluationResult(
            test_id=question.id,
            agent_name="workflow",
            label=EvaluationLabel.FAIL,
            explanation=f"Workflow execution failed: {e}",
            evaluation_type="workflow_execution",
            error_message=str(e),
            execution_metadata=ExecutionMetadata(
                duration_ms=0,
                model_provider="n/a",
                model_name="n/a",
            ),
        )
        results.append(error_result)

    return results


def _print_eval_result(name: str, result: EvaluationResult) -> None:
    """Print evaluation result with color coding."""
    label = result.label.value.upper()
    if result.passed:
        print(f"    {name}: {label}")
    else:
        print(f"    {name}: {label} - {result.explanation[:60]}...")


async def run_evaluation_suite(
    questions: list[ProductionEvalQuestion] | None = None,
    max_concurrent: int = 1,
    config: EvaluatorConfig | None = None,
) -> EvaluationRunSummary:
    """Run evaluations across the production dataset.

    All evaluations are logged to Arize Phoenix Cloud for tracking and analysis.

    Args:
        questions: List of questions to evaluate. Uses full dataset if None.
        max_concurrent: Maximum concurrent evaluations (default: 1 for sequential).
        config: Optional evaluator configuration.

    Returns:
        EvaluationRunSummary with all results and metrics.
    """
    if questions is None:
        questions = get_production_dataset()

    if config is None:
        config = EvaluatorConfig(log_to_arize=_TRACING_ENABLED)

    print(f"\n{'#' * 60}")
    print("# EVALUATION SUITE")
    print(f"{'#' * 60}")
    print(f"Questions: {len(questions)}")
    print(f"Max concurrent: {max_concurrent}")
    print(f"Arize Cloud logging: {'ENABLED' if _TRACING_ENABLED else 'DISABLED'}")
    print(f"{'#' * 60}")

    all_results: list[EvaluationResult] = []

    # Run evaluations with concurrency limit
    semaphore = asyncio.Semaphore(max_concurrent)

    async def run_with_semaphore(q: ProductionEvalQuestion) -> list[EvaluationResult]:
        async with semaphore:
            return await run_single_evaluation(q, config)

    # Execute all evaluations
    tasks = [run_with_semaphore(q) for q in questions]
    results_lists = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect results, handling any exceptions
    for i, result in enumerate(results_lists):
        if isinstance(result, Exception):
            print(f"\nQuestion {questions[i].id} failed with exception: {result}")
            error_result = EvaluationResult(
                test_id=questions[i].id,
                agent_name="workflow",
                label=EvaluationLabel.FAIL,
                explanation=f"Evaluation failed with exception: {result}",
                evaluation_type="workflow_execution",
                error_message=str(result),
                execution_metadata=ExecutionMetadata(
                    duration_ms=0,
                    model_provider="n/a",
                    model_name="n/a",
                ),
            )
            all_results.append(error_result)
        else:
            all_results.extend(result)

    # Calculate summary
    passed = sum(1 for r in all_results if r.passed)
    failed = len(all_results) - passed

    summary = EvaluationRunSummary(
        run_id=f"eval_{len(questions)}q",
        total_evaluations=len(all_results),
        passed=passed,
        failed=failed,
        results=all_results,
    )

    # Print summary
    print(f"\n{'#' * 60}")
    print("# EVALUATION SUITE COMPLETE")
    print(f"{'#' * 60}")
    print(f"Total evaluations: {summary.total_evaluations}")
    print(f"Passed: {summary.passed}")
    print(f"Failed: {summary.failed}")
    print(f"Pass rate: {summary.pass_rate}%")
    if _TRACING_ENABLED:
        print("\nResults logged to Arize Phoenix Cloud")
    print(f"{'#' * 60}")

    return summary


def main() -> None:
    """CLI entry point for evaluation runner."""
    parser = argparse.ArgumentParser(
        description="Run evaluation suite for deep research system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m research.evaluation.runner                              # Run full dataset (35 questions)
  python -m research.evaluation.runner --smoke-test                 # Run P0 only (7 questions)
  python -m research.evaluation.runner --critical                   # Run P0+P1 (14 questions)
  python -m research.evaluation.runner --domain ai                  # Run AI domain only (5 questions)
  python -m research.evaluation.runner --query "Your question"      # Run single custom query
  python -m research.evaluation.runner --export results/            # Export results to JSON

Environment Variables (set in .env):
  PHOENIX_API_KEY     Arize Cloud API key (for cloud logging)
  ANTHROPIC_API_KEY   For Claude-based evaluations
  GEMINI_API_KEY      For Gemini-based research gathering
        """,
    )

    parser.add_argument(
        "--query",
        type=str,
        metavar="QUERY",
        help="Run evaluation for a single custom query",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run only P0 priority questions (7 smoke tests)",
    )
    parser.add_argument(
        "--critical",
        action="store_true",
        help="Run only P0 and P1 priority questions (14 tests)",
    )
    parser.add_argument(
        "--domain",
        type=str,
        choices=[d.value for d in ConsultingDomain],
        help="Run only questions from specified domain (5 tests)",
    )
    parser.add_argument(
        "--export",
        type=str,
        metavar="PATH",
        help="Export results to JSON file or directory",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=1,
        help="Maximum concurrent evaluations (default: 1)",
    )
    parser.add_argument(
        "--no-arize",
        action="store_true",
        help="Disable Arize Cloud logging even if configured",
    )

    args = parser.parse_args()

    # Select questions based on filters
    if args.query:
        # Create a single ad-hoc question for the custom query
        questions = [
            ProductionEvalQuestion(
                id="custom_query",
                query=args.query,
                domain=ConsultingDomain.DATA,  # Default domain for ad-hoc
                priority=TestPriority.P0,
                tags=["custom", "ad-hoc"],
                description="Ad-hoc evaluation query",
            )
        ]
        print("Running custom query evaluation")
    elif args.smoke_test:
        questions = get_smoke_test_subset()
        print(f"Running smoke tests: {len(questions)} P0 questions")
    elif args.critical:
        questions = get_critical_subset()
        print(f"Running critical tests: {len(questions)} P0+P1 questions")
    elif args.domain:
        domain = ConsultingDomain(args.domain)
        questions = get_domain_questions(domain)
        print(f"Running {domain.value} domain: {len(questions)} questions")
    else:
        questions = get_production_dataset()
        print(f"Running full dataset: {len(questions)} questions")

    if not questions:
        print("No questions to evaluate.")
        sys.exit(0)

    # Configure evaluator
    config = None
    if args.no_arize:
        config = EvaluatorConfig(log_to_arize=False)

    # Run evaluation suite
    try:
        summary = asyncio.run(
            run_evaluation_suite(
                questions=questions,
                max_concurrent=args.max_concurrent,
                config=config,
            )
        )
    except KeyboardInterrupt:
        print("\nEvaluation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nEvaluation failed: {e}")
        sys.exit(1)

    # Export results if requested
    if args.export:
        try:
            export_path = export_evaluation_results(
                results=summary.results,
                output_path=args.export,
                run_id=summary.run_id,
            )
            print(f"\nResults exported to: {export_path}")
        except Exception as e:
            print(f"\nFailed to export results: {e}")
            sys.exit(1)

    # Exit with appropriate code
    if summary.failed > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
