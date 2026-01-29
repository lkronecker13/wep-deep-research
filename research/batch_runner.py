"""Batch execution orchestrator for deep research POC validation."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from time import perf_counter

from pydantic import BaseModel, Field

from research.run_research import run_research
from research.test_dataset import ResearchCategory, TestDataset, get_test_dataset


class BatchMode(str, Enum):
    """Batch execution modes."""

    SAMPLE = "sample"
    CATEGORY = "category"
    FULL = "full"


class BatchConfig(BaseModel):
    """Configuration for batch execution."""

    mode: BatchMode = Field(description="Execution mode")
    sample_size: int | None = Field(default=None, description="Number of questions for sample mode")
    category: ResearchCategory | None = Field(default=None, description="Category filter for category mode")
    run_id: str = Field(description="Unique identifier for this batch run")


class QueryResult(BaseModel):
    """Result of executing a single research query."""

    question_id: str = Field(description="Question identifier from dataset")
    query: str = Field(description="Research query text")
    category: ResearchCategory = Field(description="Question category")
    success: bool = Field(description="Whether query completed successfully")
    duration_ms: int = Field(description="Execution duration in milliseconds")
    validation_score: float | None = Field(default=None, description="Validation confidence score (0.0-1.0)")
    error: str | None = Field(default=None, description="Error message if failed")
    timestamp: datetime = Field(description="Query execution timestamp")


class BatchSummary(BaseModel):
    """Aggregate summary of batch execution results."""

    run_id: str = Field(description="Batch run identifier")
    config: BatchConfig = Field(description="Batch configuration")
    start_time: datetime = Field(description="Batch start timestamp")
    end_time: datetime = Field(description="Batch end timestamp")
    total_duration_ms: int = Field(description="Total batch duration in milliseconds")
    total_queries: int = Field(description="Total number of queries executed")
    successful: int = Field(description="Number of successful queries")
    failed: int = Field(description="Number of failed queries")
    success_rate: float = Field(description="Success rate (0.0-1.0)")
    avg_validation_score: float | None = Field(
        default=None, description="Average validation score of successful queries"
    )
    avg_duration_ms: int = Field(description="Average query duration in milliseconds")
    category_stats: dict[str, dict[str, int | float]] = Field(
        description="Per-category statistics (total, successful, success_rate, avg_score)"
    )
    failed_queries: list[dict[str, str]] = Field(description="List of failed queries with error details")


async def execute_batch(config: BatchConfig, dataset: TestDataset) -> BatchSummary:
    """
    Execute batch of research queries and generate summary.

    Args:
        config: Batch execution configuration
        dataset: Test dataset to execute against

    Returns:
        BatchSummary with aggregate results and metrics
    """
    # Select questions based on mode
    if config.mode == BatchMode.SAMPLE:
        questions = dataset.sample(config.sample_size or 10)
    elif config.mode == BatchMode.CATEGORY:
        if not config.category:
            raise ValueError("Category mode requires category to be specified")
        questions = dataset.by_category(config.category)
    else:  # FULL
        questions = dataset.questions

    print(f"\n{'=' * 80}")
    print(f"Batch Test Run: {config.run_id}")
    print(f"Mode: {config.mode.value}")
    if config.mode == BatchMode.SAMPLE:
        print(f"Sample Size: {len(questions)}")
    elif config.mode == BatchMode.CATEGORY:
        print(f"Category: {config.category.value if config.category else 'N/A'}")
    print(f"Total Queries: {len(questions)}")
    print(f"{'=' * 80}\n")

    # Create output directories
    outputs_dir = Path(__file__).parent / "outputs" / "batch"
    results_dir = outputs_dir / "results" / config.run_id
    summary_dir = outputs_dir / "summary"

    results_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)

    # Execute queries sequentially
    batch_start_time = datetime.now()
    batch_start_perf = perf_counter()
    query_results: list[QueryResult] = []

    for i, question in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] Running: {question.query[:80]}{'...' if len(question.query) > 80 else ''}")

        query_start = perf_counter()
        query_timestamp = datetime.now()

        try:
            # Execute research workflow
            result = await run_research(question.query)

            # Calculate duration
            duration_ms = int((perf_counter() - query_start) * 1000)

            # Extract validation score
            validation_score = result.get("validation", {}).get("confidence_score")

            # Save individual result
            result_file = results_dir / f"query_{question.id}.json"
            result_file.write_text(json.dumps(result, indent=2))

            # Record success
            query_result = QueryResult(
                question_id=question.id,
                query=question.query,
                category=question.category,
                success=True,
                duration_ms=duration_ms,
                validation_score=validation_score,
                timestamp=query_timestamp,
            )
            query_results.append(query_result)

            print(f"  ✅ Success ({duration_ms}ms, score: {validation_score:.2f})\n")

        except Exception as e:
            # Calculate duration even on failure
            duration_ms = int((perf_counter() - query_start) * 1000)

            # Record failure
            query_result = QueryResult(
                question_id=question.id,
                query=question.query,
                category=question.category,
                success=False,
                duration_ms=duration_ms,
                error=str(e),
                timestamp=query_timestamp,
            )
            query_results.append(query_result)

            print(f"  ❌ Failed ({duration_ms}ms): {str(e)[:100]}\n")

    # Calculate total batch duration
    batch_end_time = datetime.now()
    total_duration_ms = int((perf_counter() - batch_start_perf) * 1000)

    # Generate summary
    summary = _generate_summary(
        config=config,
        query_results=query_results,
        start_time=batch_start_time,
        end_time=batch_end_time,
        total_duration_ms=total_duration_ms,
    )

    # Save summary
    summary_file = summary_dir / f"batch_summary_{config.run_id}.json"
    summary_file.write_text(summary.model_dump_json(indent=2))

    return summary


def _generate_summary(
    config: BatchConfig,
    query_results: list[QueryResult],
    start_time: datetime,
    end_time: datetime,
    total_duration_ms: int,
) -> BatchSummary:
    """
    Generate aggregate batch summary from query results.

    Args:
        config: Batch configuration
        query_results: List of individual query results
        start_time: Batch start timestamp
        end_time: Batch end timestamp
        total_duration_ms: Total batch duration

    Returns:
        BatchSummary with calculated metrics
    """
    total_queries = len(query_results)
    successful_results = [r for r in query_results if r.success]
    failed_results = [r for r in query_results if not r.success]

    successful = len(successful_results)
    failed = len(failed_results)
    success_rate = successful / total_queries if total_queries > 0 else 0.0

    # Calculate average validation score (only from successful queries)
    validation_scores = [r.validation_score for r in successful_results if r.validation_score is not None]
    avg_validation_score = sum(validation_scores) / len(validation_scores) if validation_scores else None

    # Calculate average duration
    avg_duration_ms = int(sum(r.duration_ms for r in query_results) / total_queries) if total_queries > 0 else 0

    # Calculate per-category statistics
    category_stats: dict[str, dict[str, int | float]] = {}

    for category in ResearchCategory:
        category_results = [r for r in query_results if r.category == category]
        if not category_results:
            continue

        category_successful = [r for r in category_results if r.success]
        category_total = len(category_results)
        category_success_count = len(category_successful)
        category_success_rate = category_success_count / category_total if category_total > 0 else 0.0

        category_scores = [r.validation_score for r in category_successful if r.validation_score is not None]
        category_avg_score = sum(category_scores) / len(category_scores) if category_scores else 0.0

        category_stats[category.value] = {
            "total": category_total,
            "successful": category_success_count,
            "success_rate": round(category_success_rate, 2),
            "avg_score": round(category_avg_score, 2),
        }

    # Collect failed query details
    failed_queries = [
        {
            "id": r.question_id,
            "query": r.query[:100] + "..." if len(r.query) > 100 else r.query,
            "error": r.error[:200] + "..." if r.error and len(r.error) > 200 else (r.error or ""),
        }
        for r in failed_results
    ]

    return BatchSummary(
        run_id=config.run_id,
        config=config,
        start_time=start_time,
        end_time=end_time,
        total_duration_ms=total_duration_ms,
        total_queries=total_queries,
        successful=successful,
        failed=failed,
        success_rate=round(success_rate, 2),
        avg_validation_score=round(avg_validation_score, 2) if avg_validation_score else None,
        avg_duration_ms=avg_duration_ms,
        category_stats=category_stats,
        failed_queries=failed_queries,
    )


def print_summary(summary: BatchSummary) -> None:
    """
    Print formatted batch summary to console.

    Args:
        summary: BatchSummary to display
    """
    print(f"\n{'=' * 80}")
    print("BATCH TEST SUMMARY")
    print(f"{'=' * 80}\n")

    # Overall statistics
    print(f"Run ID: {summary.run_id}")
    print(f"Mode: {summary.config.mode.value}")
    print(f"Start Time: {summary.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"End Time: {summary.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Duration: {summary.total_duration_ms / 1000:.1f}s")
    print()

    print(f"Total Queries: {summary.total_queries}")
    print(f"Successful: {summary.successful} ({summary.success_rate:.0%})")
    print(f"Failed: {summary.failed}")
    print()

    if summary.avg_validation_score is not None:
        print(f"Average Validation Score: {summary.avg_validation_score:.2f}")
    print(f"Average Query Duration: {summary.avg_duration_ms / 1000:.1f}s")
    print()

    # Category breakdown
    if summary.category_stats:
        print(f"{'-' * 80}")
        print("CATEGORY BREAKDOWN")
        print(f"{'-' * 80}\n")

        # Table header
        print(f"{'Category':<20} {'Total':>8} {'Success':>8} {'Rate':>8} {'Avg Score':>10}")
        print(f"{'-' * 80}")

        for category, stats in summary.category_stats.items():
            print(
                f"{category:<20} "
                f"{stats['total']:>8} "
                f"{stats['successful']:>8} "
                f"{stats['success_rate']:>7.0%} "
                f"{stats['avg_score']:>10.2f}"
            )
        print()

    # Failed queries
    if summary.failed_queries:
        print(f"{'-' * 80}")
        print("FAILED QUERIES")
        print(f"{'-' * 80}\n")

        for failure in summary.failed_queries:
            print(f"ID: {failure['id']}")
            print(f"Query: {failure['query']}")
            print(f"Error: {failure['error']}")
            print()

    print(f"{'=' * 80}\n")


def main() -> None:
    """CLI entry point for batch runner."""
    parser = argparse.ArgumentParser(
        description="Run batch research tests on synthetic dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run 10 random questions
  python -m research.batch_runner --mode sample --size 10

  # Run all technical questions
  python -m research.batch_runner --mode category --category technical

  # Run full dataset (100+ questions)
  python -m research.batch_runner --mode full
        """,
    )

    parser.add_argument(
        "--mode",
        type=str,
        required=True,
        choices=["sample", "category", "full"],
        help="Batch execution mode",
    )

    parser.add_argument(
        "--size",
        type=int,
        help="Sample size (required for sample mode)",
    )

    parser.add_argument(
        "--category",
        type=str,
        choices=[c.value for c in ResearchCategory],
        help="Category filter (required for category mode)",
    )

    args = parser.parse_args()

    # Validate argument combinations
    if args.mode == "sample" and args.size is None:
        parser.error("--size is required when using sample mode")

    if args.mode == "category" and args.category is None:
        parser.error("--category is required when using category mode")

    # Load dataset
    try:
        dataset = get_test_dataset()
    except Exception as e:
        print(f"❌ Failed to load test dataset: {e}")
        sys.exit(1)

    # Generate run ID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.mode == "sample":
        run_id = f"sample_{args.size}_{timestamp}"
    elif args.mode == "category":
        run_id = f"category_{args.category}_{timestamp}"
    else:
        run_id = f"full_{timestamp}"

    # Create batch config
    config = BatchConfig(
        mode=BatchMode(args.mode),
        sample_size=args.size if args.mode == "sample" else None,
        category=ResearchCategory(args.category) if args.mode == "category" and args.category else None,
        run_id=run_id,
    )

    # Execute batch
    try:
        summary = asyncio.run(execute_batch(config, dataset))
    except KeyboardInterrupt:
        print("\n\n❌ Batch execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Batch execution failed: {e}")
        sys.exit(1)

    # Print summary
    print_summary(summary)

    # Exit with appropriate code
    sys.exit(0 if summary.failed == 0 else 1)


if __name__ == "__main__":
    main()
