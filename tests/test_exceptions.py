"""Tests for research pipeline exceptions."""

import pytest

from src.exceptions import (
    GatheringError,
    PlanningError,
    ResearchPipelineError,
    SynthesisError,
    VerificationError,
)


class TestResearchPipelineError:
    """Tests for base ResearchPipelineError."""

    def test__base_error__is_exception(self) -> None:
        error = ResearchPipelineError("test message")
        assert isinstance(error, Exception)
        assert str(error) == "test message"


class TestPlanningError:
    """Tests for PlanningError."""

    def test__planning_error__stores_attributes(self) -> None:
        error = PlanningError(topic="test topic", reason="test reason")
        assert error.topic == "test topic"
        assert error.reason == "test reason"

    def test__planning_error__formats_message(self) -> None:
        error = PlanningError(topic="AI research", reason="model unavailable")
        assert str(error) == "Failed to create research plan for 'AI research': model unavailable"

    def test__planning_error__inherits_from_base(self) -> None:
        error = PlanningError(topic="test", reason="test")
        assert isinstance(error, ResearchPipelineError)

    def test__planning_error__catchable_as_base(self) -> None:
        with pytest.raises(ResearchPipelineError):
            raise PlanningError(topic="test", reason="test")


class TestGatheringError:
    """Tests for GatheringError."""

    def test__gathering_error__stores_attributes(self) -> None:
        error = GatheringError(attempted=5, failed=5)
        assert error.attempted == 5
        assert error.failed == 5

    def test__gathering_error__formats_message(self) -> None:
        error = GatheringError(attempted=3, failed=3)
        assert str(error) == "All 3 search attempts failed. Cannot proceed with synthesis."

    def test__gathering_error__inherits_from_base(self) -> None:
        error = GatheringError(attempted=5, failed=5)
        assert isinstance(error, ResearchPipelineError)

    def test__gathering_error__catchable_as_base(self) -> None:
        with pytest.raises(ResearchPipelineError):
            raise GatheringError(attempted=5, failed=5)


class TestSynthesisError:
    """Tests for SynthesisError."""

    def test__synthesis_error__stores_attributes(self) -> None:
        error = SynthesisError(reason="insufficient data")
        assert error.reason == "insufficient data"

    def test__synthesis_error__formats_message(self) -> None:
        error = SynthesisError(reason="conflicting information")
        assert str(error) == "Failed to synthesize research report: conflicting information"

    def test__synthesis_error__inherits_from_base(self) -> None:
        error = SynthesisError(reason="test")
        assert isinstance(error, ResearchPipelineError)

    def test__synthesis_error__catchable_as_base(self) -> None:
        with pytest.raises(ResearchPipelineError):
            raise SynthesisError(reason="test")


class TestVerificationError:
    """Tests for VerificationError."""

    def test__verification_error__stores_attributes(self) -> None:
        error = VerificationError(reason="low confidence score")
        assert error.reason == "low confidence score"

    def test__verification_error__formats_message(self) -> None:
        error = VerificationError(reason="contradictory findings")
        assert str(error) == "Failed to verify research: contradictory findings"

    def test__verification_error__inherits_from_base(self) -> None:
        error = VerificationError(reason="test")
        assert isinstance(error, ResearchPipelineError)

    def test__verification_error__catchable_as_base(self) -> None:
        with pytest.raises(ResearchPipelineError):
            raise VerificationError(reason="test")
