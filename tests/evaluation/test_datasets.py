"""Unit tests for dataset loading and filtering."""

from research.evaluation.datasets import (
    ConsultingDomain,
    get_critical_subset,
    get_domain_questions,
    get_production_dataset,
    get_questions_by_priority,
    get_questions_by_tag,
    get_smoke_test_subset,
)
from research.evaluation.schemas import TestPriority


class TestDatasetLoading:
    """Tests for dataset loading functions."""

    def test__get_production_dataset__returns_35_questions(self):
        """Production dataset should contain all 35 evaluation questions."""
        dataset = get_production_dataset()
        assert len(dataset) == 35

    def test__get_production_dataset__returns_copy_not_reference(self):
        """Should return a copy to prevent mutation of cached data."""
        dataset1 = get_production_dataset()
        dataset2 = get_production_dataset()
        assert dataset1 is not dataset2
        assert dataset1 == dataset2


class TestDatasetFiltering:
    """Tests for dataset filtering functions."""

    def test__get_smoke_test_subset__returns_only_p0_questions(self):
        """Smoke test subset should contain only P0 (blocker) priority."""
        subset = get_smoke_test_subset()
        assert all(q.priority == TestPriority.P0 for q in subset)
        assert len(subset) == 7  # 1 per domain

    def test__get_critical_subset__returns_p0_and_p1_only(self):
        """Critical subset should contain only P0 and P1 questions."""
        subset = get_critical_subset()
        priorities = {q.priority for q in subset}
        assert priorities <= {TestPriority.P0, TestPriority.P1}
        assert len(subset) == 14  # 2 per domain

    def test__get_domain_questions__filters_by_domain(self):
        """Should return only questions for specified domain."""
        data_questions = get_domain_questions(ConsultingDomain.DATA)
        assert all(q.domain == ConsultingDomain.DATA for q in data_questions)
        assert len(data_questions) == 5

    def test__get_questions_by_priority__filters_correctly(self):
        """Should return questions matching priority level."""
        p1_questions = get_questions_by_priority(TestPriority.P1)
        assert all(q.priority == TestPriority.P1 for q in p1_questions)

    def test__get_questions_by_tag__is_case_insensitive(self):
        """Tag filtering should be case-insensitive."""
        subset1 = get_questions_by_tag("COMPLEX")
        subset2 = get_questions_by_tag("complex")
        assert subset1 == subset2
