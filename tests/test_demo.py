"""Unit tests for demo mode fixtures."""

import pytest

from src.demo import generate_demo_sse_stream, get_demo_research_result, is_demo_mode_allowed
from src.models import ResearchResult


class TestGetDemoResearchResult:
    """Tests for get_demo_research_result function."""

    def test__get_demo_research_result__returns_valid_pydantic_model(self) -> None:
        """Returns a valid ResearchResult model with all required fields."""
        result = get_demo_research_result()

        assert isinstance(result, ResearchResult)
        assert result.query == "What are the latest developments in quantum computing?"
        assert result.plan.executive_summary
        assert len(result.plan.web_search_steps) > 0
        assert len(result.search_results) > 0
        assert result.report.title
        assert len(result.report.key_findings) > 0
        assert result.validation.is_valid is True
        assert result.validation.confidence_score == 0.85
        assert result.timings.total_ms == 500

    def test__get_demo_research_result__caches_result(self) -> None:
        """Verify LRU cache returns same object instance."""
        first_call = get_demo_research_result()
        second_call = get_demo_research_result()

        # Cache returns exact same object (not just equal values)
        assert first_call is second_call

    def test__get_demo_research_result__model_copy_overrides_query(self) -> None:
        """Verify model_copy pattern allows query override without breaking cache."""
        cached_result = get_demo_research_result()
        custom_result = cached_result.model_copy(update={"query": "Custom query"})

        # Custom query preserved
        assert custom_result.query == "Custom query"

        # All other fields identical
        assert custom_result.plan == cached_result.plan
        assert custom_result.search_results == cached_result.search_results
        assert custom_result.report == cached_result.report
        assert custom_result.validation == cached_result.validation
        assert custom_result.timings == cached_result.timings


class TestIsDemoModeAllowed:
    """Tests for is_demo_mode_allowed function."""

    def test__is_demo_mode_allowed__allows_development(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Demo mode allowed in development environment."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        assert is_demo_mode_allowed() is True

    def test__is_demo_mode_allowed__allows_staging(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Demo mode allowed in staging environment."""
        monkeypatch.setenv("ENVIRONMENT", "staging")
        assert is_demo_mode_allowed() is True

    def test__is_demo_mode_allowed__blocks_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Demo mode blocked in production environment."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        assert is_demo_mode_allowed() is False

    def test__is_demo_mode_allowed__defaults_to_development(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Demo mode defaults to allowed when ENVIRONMENT not set."""
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        assert is_demo_mode_allowed() is True


class TestGenerateDemoSSEStream:
    """Tests for generate_demo_sse_stream function."""

    @pytest.mark.asyncio
    async def test__generate_demo_sse_stream__emits_all_phases(self) -> None:
        """Verify all 4 phases emit start and complete events."""
        query = "test query"
        events = [event async for event in generate_demo_sse_stream(query)]

        # Convert to strings for easier assertion
        event_strings = [e for e in events]

        # Verify phase start events (4 phases)
        assert any("event: phase_start" in e and "planning" in e for e in event_strings)
        assert any("event: phase_start" in e and "gathering" in e for e in event_strings)
        assert any("event: phase_start" in e and "synthesis" in e for e in event_strings)
        assert any("event: phase_start" in e and "verification" in e for e in event_strings)

        # Verify phase complete events (4 phases)
        assert any("event: phase_complete" in e and "planning" in e for e in event_strings)
        assert any("event: phase_complete" in e and "gathering" in e for e in event_strings)
        assert any("event: phase_complete" in e and "synthesis" in e for e in event_strings)
        assert any("event: phase_complete" in e and "verification" in e for e in event_strings)

        # Verify complete event at end
        assert any("event: complete" in e for e in event_strings)

        # Verify query in complete event
        complete_event = next(e for e in event_strings if "event: complete" in e)
        assert query in complete_event

    @pytest.mark.asyncio
    async def test__generate_demo_sse_stream__events_in_order(self) -> None:
        """Verify events emitted in correct phase order."""
        events = [event async for event in generate_demo_sse_stream("test")]

        # Find indices of phase start events
        planning_idx = next(i for i, e in enumerate(events) if "planning" in e and "phase_start" in e)
        gathering_idx = next(i for i, e in enumerate(events) if "gathering" in e and "phase_start" in e)
        synthesis_idx = next(i for i, e in enumerate(events) if "synthesis" in e and "phase_start" in e)
        verification_idx = next(i for i, e in enumerate(events) if "verification" in e and "phase_start" in e)
        complete_idx = next(i for i, e in enumerate(events) if "event: complete" in e)

        # Verify order
        assert planning_idx < gathering_idx < synthesis_idx < verification_idx < complete_idx

    @pytest.mark.asyncio
    async def test__generate_demo_sse_stream__preserves_custom_query(self) -> None:
        """Verify custom query propagated to complete event."""
        custom_query = "What are the implications of quantum entanglement?"
        events = [event async for event in generate_demo_sse_stream(custom_query)]

        # Find complete event
        complete_event = next(e for e in events if "event: complete" in e)

        # Verify custom query present (not the hardcoded default)
        assert custom_query in complete_event
        assert "What are the latest developments in quantum computing?" not in complete_event
