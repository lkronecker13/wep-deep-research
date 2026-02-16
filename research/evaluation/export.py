"""Export utilities for evaluation results.

Provides functionality to export evaluation results to JSON files
for regression tracking and shared storage.
"""

from __future__ import annotations

import os
import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from research.evaluation.schemas import EvaluationResult


class EvaluationRunSummary(BaseModel):
    """Summary of an evaluation run with aggregated metrics.

    Designed for regression tracking over time. Pass rate is stored as
    a percentage (0.0 - 100.0) for human readability.
    """

    run_id: str = Field(description="Unique identifier for this evaluation run")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the evaluation run was executed",
    )
    total_evaluations: int = Field(ge=0, description="Total number of evaluations performed")
    passed: int = Field(ge=0, description="Number of evaluations that passed")
    failed: int = Field(ge=0, description="Number of evaluations that failed")
    results: list[EvaluationResult] = Field(
        default_factory=list,
        description="Individual evaluation results",
    )

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, v: str) -> str:
        """Ensure run_id is filesystem-safe and non-empty."""
        v = v.strip()
        if not v:
            raise ValueError("run_id cannot be empty")
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("run_id must contain only alphanumeric characters, hyphens, and underscores")
        return v

    @field_validator("timestamp")
    @classmethod
    def validate_timezone_aware(cls, v: datetime) -> datetime:
        """Ensure timestamp is timezone-aware (UTC)."""
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v

    @model_validator(mode="after")
    def validate_evaluation_counts(self) -> "EvaluationRunSummary":
        """Ensure evaluation counts are logically consistent."""
        if self.total_evaluations != self.passed + self.failed:
            raise ValueError(
                f"total_evaluations ({self.total_evaluations}) must equal "
                f"passed ({self.passed}) + failed ({self.failed})"
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pass_rate(self) -> float:
        """Calculate pass rate as percentage (0.0 - 100.0)."""
        if self.total_evaluations == 0:
            return 0.0
        return round((self.passed / self.total_evaluations) * 100, 2)

    def get_failed_tests(self) -> list[EvaluationResult]:
        """Get all failed evaluation results for debugging."""
        return [r for r in self.results if not r.passed]

    def get_passed_tests(self) -> list[EvaluationResult]:
        """Get all passed evaluation results."""
        return [r for r in self.results if r.passed]

    def group_by_agent(self) -> dict[str, list[EvaluationResult]]:
        """Group results by agent name for per-agent analysis."""
        grouped: dict[str, list[EvaluationResult]] = defaultdict(list)
        for result in self.results:
            grouped[result.agent_name].append(result)
        return dict(grouped)

    def group_by_evaluation_type(self) -> dict[str, list[EvaluationResult]]:
        """Group results by evaluation type for per-metric analysis."""
        grouped: dict[str, list[EvaluationResult]] = defaultdict(list)
        for result in self.results:
            grouped[result.evaluation_type].append(result)
        return dict(grouped)


def _get_allowed_directories() -> list[Path]:
    """Get list of allowed directories for export path validation.

    Includes project directories and system temp directories for testing.
    """
    allowed = [
        Path.cwd().resolve(),
        (Path.cwd() / "research").resolve(),
        (Path.cwd() / "research" / "outputs").resolve(),
    ]

    # Add Unix temp directories
    unix_temp_dirs = [
        Path("/tmp"),
        Path("/private/var/folders"),  # macOS
    ]

    for temp_dir in unix_temp_dirs:
        try:
            resolved = temp_dir.resolve()
            if resolved.exists():
                allowed.append(resolved)
        except (OSError, RuntimeError):
            pass

    # Add Windows temp directories
    if os.name == "nt":
        for env_var in ["TEMP", "TMP", "LOCALAPPDATA"]:
            temp_env = os.environ.get(env_var)
            if temp_env:
                try:
                    resolved = Path(temp_env).resolve()
                    if resolved.exists():
                        allowed.append(resolved)
                except (OSError, RuntimeError):
                    pass

    return allowed


def _validate_output_path(output_path: Path) -> None:
    """Validate that output path is within allowed directories.

    Args:
        output_path: Resolved absolute path to validate.

    Raises:
        ValueError: If path is outside allowed directories.
    """
    allowed_dirs = _get_allowed_directories()

    if not any(output_path == d or output_path.is_relative_to(d) for d in allowed_dirs):
        raise ValueError(f"Output path must be within project or temp directory. Got: {output_path}")


def export_evaluation_results(
    results: list[EvaluationResult],
    output_path: str | Path = "research/outputs/evaluations/",
    run_id: str | None = None,
) -> Path:
    """Export evaluation results to a JSON file with path security validation.

    Creates a timestamped JSON file containing evaluation results and
    aggregated metrics for regression tracking.

    Args:
        results: List of EvaluationResult objects to export.
        output_path: Directory or file path for export. If directory,
            generates filename with timestamp. Default: research/outputs/evaluations/
        run_id: Optional unique identifier for this run. Generated if not provided.

    Returns:
        Path: Absolute path to the exported JSON file.

    Raises:
        ValueError: If output path is outside allowed directories or results is empty.
        OSError: If unable to create directory or write file.

    Example:
        >>> results = [eval_result_1, eval_result_2]
        >>> path = export_evaluation_results(results)
        >>> print(f"Exported to: {path}")
    """
    # Validate we have results
    if not results:
        raise ValueError("Cannot export empty results list")

    # Generate run_id if not provided
    if run_id is None:
        run_id = str(uuid.uuid4())[:8]

    # Resolve output path
    output_file = Path(output_path).resolve()

    # If path is a directory or ends with separator, generate filename
    if output_file.is_dir() or str(output_path).endswith(("/", "\\")):
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_file = output_file / f"eval_{run_id}_{timestamp}.json"

    # Validate path security
    _validate_output_path(output_file)

    # Ensure parent directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Calculate summary metrics
    passed_count = sum(1 for r in results if r.passed)
    failed_count = len(results) - passed_count

    # Create summary
    summary = EvaluationRunSummary(
        run_id=run_id,
        total_evaluations=len(results),
        passed=passed_count,
        failed=failed_count,
        results=results,
    )

    # Write JSON with pretty formatting (UTF-8 for Unicode support)
    output_file.write_text(summary.model_dump_json(indent=2), encoding="utf-8")

    print(f"Evaluation results exported to: {output_file}")
    print(f"   Run ID: {run_id}")
    print(f"   Total evaluations: {summary.total_evaluations}")
    print(f"   Pass rate: {summary.pass_rate}%")

    return output_file


if __name__ == "__main__":
    """CLI entry point for exporting evaluation results."""
    import json
    import sys

    def main() -> None:
        """Load results from JSON file and export with summary."""
        if len(sys.argv) < 2:
            print("Usage: python -m research.evaluation.export <results.json> [output_path]")
            print("  results.json: JSON file containing list of EvaluationResult objects")
            print("  output_path: Optional output directory or file path")
            sys.exit(1)

        input_file = Path(sys.argv[1])
        if not input_file.exists():
            print(f"Error: File not found: {input_file}", file=sys.stderr)
            sys.exit(1)

        data = json.loads(input_file.read_text())
        results = [EvaluationResult(**r) for r in data]

        output_path = sys.argv[2] if len(sys.argv) > 2 else "research/outputs/evaluations/"

        try:
            export_evaluation_results(results, output_path)
        except ValueError as e:
            print(f"Error: Invalid input - {e}", file=sys.stderr)
            sys.exit(1)
        except PermissionError as e:
            print(f"Error: Permission denied - {e}", file=sys.stderr)
            sys.exit(1)
        except OSError as e:
            print(f"Error: File system error - {e}", file=sys.stderr)
            sys.exit(1)

    main()
