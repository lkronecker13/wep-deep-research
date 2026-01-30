"""Tests for research pipeline Pydantic models."""

import pytest
from pydantic import ValidationError

from src.models import (
    PhaseTimings,
    ResearchPlan,
    ResearchReport,
    ResearchResult,
    SearchResult,
    SearchStep,
    ValidationResult,
)


class TestSearchStep:
    """Tests for SearchStep model."""

    def test__valid_creation__succeeds(self) -> None:
        step = SearchStep(search_terms="test query", purpose="test purpose")
        assert step.search_terms == "test query"
        assert step.purpose == "test purpose"

    def test__empty_search_terms__raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            SearchStep(search_terms="", purpose="test purpose")

    def test__empty_purpose__raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            SearchStep(search_terms="test query", purpose="")

    def test__roundtrip_serialization__preserves_data(self) -> None:
        step = SearchStep(search_terms="test query", purpose="test purpose")
        json_data = step.model_dump_json()
        restored = SearchStep.model_validate_json(json_data)
        assert restored == step


class TestResearchPlan:
    """Tests for ResearchPlan model."""

    def test__valid_creation__succeeds(self) -> None:
        plan = ResearchPlan(
            executive_summary="Test summary",
            web_search_steps=[SearchStep(search_terms="query", purpose="purpose")],
            analysis_instructions="Test instructions",
        )
        assert plan.executive_summary == "Test summary"
        assert len(plan.web_search_steps) == 1
        assert plan.analysis_instructions == "Test instructions"

    def test__zero_search_steps__raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            ResearchPlan(
                executive_summary="Summary",
                web_search_steps=[],
                analysis_instructions="Instructions",
            )

    def test__six_search_steps__raises_validation_error(self) -> None:
        steps = [SearchStep(search_terms=f"query{i}", purpose=f"purpose{i}") for i in range(6)]
        with pytest.raises(ValidationError):
            ResearchPlan(
                executive_summary="Summary",
                web_search_steps=steps,
                analysis_instructions="Instructions",
            )

    def test__five_search_steps__succeeds(self) -> None:
        steps = [SearchStep(search_terms=f"query{i}", purpose=f"purpose{i}") for i in range(5)]
        plan = ResearchPlan(
            executive_summary="Summary",
            web_search_steps=steps,
            analysis_instructions="Instructions",
        )
        assert len(plan.web_search_steps) == 5

    def test__one_search_step__succeeds(self) -> None:
        plan = ResearchPlan(
            executive_summary="Summary",
            web_search_steps=[SearchStep(search_terms="query", purpose="purpose")],
            analysis_instructions="Instructions",
        )
        assert len(plan.web_search_steps) == 1

    def test__roundtrip_serialization__preserves_data(self) -> None:
        plan = ResearchPlan(
            executive_summary="Summary",
            web_search_steps=[SearchStep(search_terms="query", purpose="purpose")],
            analysis_instructions="Instructions",
        )
        json_data = plan.model_dump_json()
        restored = ResearchPlan.model_validate_json(json_data)
        assert restored == plan


class TestSearchResult:
    """Tests for SearchResult model."""

    def test__valid_creation__succeeds(self) -> None:
        result = SearchResult(query="test query", findings=["finding1"], sources=["source1"])
        assert result.query == "test query"
        assert result.findings == ["finding1"]
        assert result.sources == ["source1"]

    def test__empty_findings__uses_default_factory(self) -> None:
        result = SearchResult(query="test query")
        assert result.findings == []
        assert result.sources == []

    def test__findings_list__preserves_order(self) -> None:
        result = SearchResult(query="query", findings=["a", "b", "c"], sources=["x", "y", "z"])
        assert result.findings == ["a", "b", "c"]
        assert result.sources == ["x", "y", "z"]

    def test__roundtrip_serialization__preserves_data(self) -> None:
        result = SearchResult(query="query", findings=["finding"], sources=["source"])
        json_data = result.model_dump_json()
        restored = SearchResult.model_validate_json(json_data)
        assert restored == result


class TestResearchReport:
    """Tests for ResearchReport model."""

    def test__valid_creation__succeeds(self) -> None:
        report = ResearchReport(
            title="Test Report",
            summary="Test summary",
            key_findings=["finding1"],
            sources=["source1"],
            limitations="Test limitations",
        )
        assert report.title == "Test Report"
        assert report.summary == "Test summary"
        assert report.key_findings == ["finding1"]
        assert report.sources == ["source1"]
        assert report.limitations == "Test limitations"

    def test__empty_lists__use_default_factory(self) -> None:
        report = ResearchReport(title="Title", summary="Summary")
        assert report.key_findings == []
        assert report.sources == []
        assert report.limitations == ""

    def test__limitations_defaults_to_empty_string(self) -> None:
        report = ResearchReport(title="Title", summary="Summary")
        assert report.limitations == ""

    def test__roundtrip_serialization__preserves_data(self) -> None:
        report = ResearchReport(
            title="Title",
            summary="Summary",
            key_findings=["finding"],
            sources=["source"],
            limitations="limitations",
        )
        json_data = report.model_dump_json()
        restored = ResearchReport.model_validate_json(json_data)
        assert restored == report


class TestValidationResult:
    """Tests for ValidationResult model."""

    def test__valid_creation__succeeds(self) -> None:
        result = ValidationResult(
            is_valid=True,
            confidence_score=0.95,
            issues_found=["issue1"],
            recommendations=["recommendation1"],
        )
        assert result.is_valid is True
        assert result.confidence_score == 0.95
        assert result.issues_found == ["issue1"]
        assert result.recommendations == ["recommendation1"]

    def test__confidence_score_zero__succeeds(self) -> None:
        result = ValidationResult(is_valid=False, confidence_score=0.0)
        assert result.confidence_score == 0.0

    def test__confidence_score_one__succeeds(self) -> None:
        result = ValidationResult(is_valid=True, confidence_score=1.0)
        assert result.confidence_score == 1.0

    def test__confidence_score_negative__raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            ValidationResult(is_valid=False, confidence_score=-0.1)

    def test__confidence_score_above_one__raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            ValidationResult(is_valid=True, confidence_score=1.1)

    def test__empty_lists__use_default_factory(self) -> None:
        result = ValidationResult(is_valid=True, confidence_score=0.8)
        assert result.issues_found == []
        assert result.recommendations == []

    def test__roundtrip_serialization__preserves_data(self) -> None:
        result = ValidationResult(
            is_valid=True,
            confidence_score=0.9,
            issues_found=["issue"],
            recommendations=["recommendation"],
        )
        json_data = result.model_dump_json()
        restored = ValidationResult.model_validate_json(json_data)
        assert restored == result


class TestPhaseTimings:
    """Tests for PhaseTimings model."""

    def test__valid_creation__succeeds(self) -> None:
        timings = PhaseTimings(planning_ms=100, gathering_ms=200, synthesis_ms=300, verification_ms=400, total_ms=1000)
        assert timings.planning_ms == 100
        assert timings.total_ms == 1000

    def test__zero_values__succeeds(self) -> None:
        timings = PhaseTimings(planning_ms=0, gathering_ms=0, synthesis_ms=0, verification_ms=0, total_ms=0)
        assert timings.planning_ms == 0

    def test__negative_value__raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            PhaseTimings(planning_ms=-1, gathering_ms=0, synthesis_ms=0, verification_ms=0, total_ms=0)

    def test__roundtrip_serialization__preserves_data(self) -> None:
        timings = PhaseTimings(planning_ms=10, gathering_ms=20, synthesis_ms=30, verification_ms=40, total_ms=100)
        json_data = timings.model_dump_json()
        restored = PhaseTimings.model_validate_json(json_data)
        assert restored == timings


class TestResearchResult:
    """Tests for ResearchResult model."""

    def test__valid_creation__succeeds(self) -> None:
        # build all sub-models
        plan = ResearchPlan(
            executive_summary="Summary",
            web_search_steps=[SearchStep(search_terms="q", purpose="p")],
            analysis_instructions="Instructions",
        )
        result = ResearchResult(
            query="test query",
            plan=plan,
            search_results=[SearchResult(query="q", findings=["f"], sources=["s"])],
            report=ResearchReport(title="T", summary="S", key_findings=["kf"], sources=["src"]),
            validation=ValidationResult(is_valid=True, confidence_score=0.9),
            timings=PhaseTimings(planning_ms=10, gathering_ms=20, synthesis_ms=30, verification_ms=40, total_ms=100),
        )
        assert result.query == "test query"
        assert len(result.search_results) == 1

    def test__empty_query__raises_validation_error(self) -> None:
        plan = ResearchPlan(
            executive_summary="Summary",
            web_search_steps=[SearchStep(search_terms="q", purpose="p")],
            analysis_instructions="Instructions",
        )
        with pytest.raises(ValidationError):
            ResearchResult(
                query="",
                plan=plan,
                search_results=[],
                report=ResearchReport(title="T", summary="S"),
                validation=ValidationResult(is_valid=True, confidence_score=0.9),
                timings=PhaseTimings(planning_ms=0, gathering_ms=0, synthesis_ms=0, verification_ms=0, total_ms=0),
            )

    def test__roundtrip_serialization__preserves_data(self) -> None:
        plan = ResearchPlan(
            executive_summary="Summary",
            web_search_steps=[SearchStep(search_terms="q", purpose="p")],
            analysis_instructions="Instructions",
        )
        result = ResearchResult(
            query="test query",
            plan=plan,
            search_results=[SearchResult(query="q")],
            report=ResearchReport(title="T", summary="S"),
            validation=ValidationResult(is_valid=True, confidence_score=0.9),
            timings=PhaseTimings(planning_ms=10, gathering_ms=20, synthesis_ms=30, verification_ms=40, total_ms=100),
        )
        json_data = result.model_dump_json()
        restored = ResearchResult.model_validate_json(json_data)
        assert restored == result
