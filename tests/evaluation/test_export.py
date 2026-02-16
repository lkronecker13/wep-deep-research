"""Unit tests for evaluation export and aggregation logic."""

import pytest

from research.evaluation.export import EvaluationRunSummary


class TestEvaluationRunSummary:
    """Tests for EvaluationRunSummary aggregation model."""

    def test__evaluation_run_summary__calculates_pass_rate_correctly(
        self, sample_evaluation_result, failing_evaluation_result
    ):
        """Pass rate should be calculated as (passed / total) * 100."""
        summary = EvaluationRunSummary(
            run_id="test-run",
            total_evaluations=10,
            passed=7,
            failed=3,
            results=[sample_evaluation_result, failing_evaluation_result],
        )
        assert summary.pass_rate == 70.0

    def test__evaluation_run_summary__zero_evaluations_gives_zero_pass_rate(self):
        """Pass rate should be 0.0 when no evaluations run."""
        summary = EvaluationRunSummary(
            run_id="test-run",
            total_evaluations=0,
            passed=0,
            failed=0,
            results=[],
        )
        assert summary.pass_rate == 0.0

    def test__evaluation_run_summary__validates_count_consistency(self, sample_evaluation_result):
        """Should validate that passed + failed == total."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            EvaluationRunSummary(
                run_id="test-run",
                total_evaluations=10,
                passed=7,
                failed=4,  # 7 + 4 != 10
                results=[sample_evaluation_result],
            )
