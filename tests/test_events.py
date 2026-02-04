"""Tests for SSE event models."""

import json

from src.events import (
    CompleteEvent,
    ErrorEvent,
    GatheringProgressEvent,
    HeartbeatEvent,
    PhaseCompleteEvent,
    PhaseStartEvent,
    PhaseWarningEvent,
    SSEEventType,
)
from src.models import (
    PhaseTimings,
    ResearchPlan,
    ResearchReport,
    ResearchResult,
    SearchResult,
    SearchStep,
    ValidationResult,
)


def test__phase_start_event__formats_correctly() -> None:
    """PhaseStartEvent formats as valid SSE message."""
    event = PhaseStartEvent(data={"phase": "planning"})
    formatted = event.format()

    assert formatted.startswith("event: phase_start\n")
    assert "data: {" in formatted
    assert '"phase": "planning"' in formatted
    assert formatted.endswith("\n\n")


def test__phase_complete_event__formats_correctly() -> None:
    """PhaseCompleteEvent formats with duration and summary."""
    event = PhaseCompleteEvent(
        data={
            "phase": "gathering",
            "duration_ms": 12000,
            "output_summary": {
                "searches_completed": 3,
                "searches_requested": 5,
                "total_sources": 15,
            },
        }
    )
    formatted = event.format()

    assert formatted.startswith("event: phase_complete\n")
    assert "data: {" in formatted
    assert '"phase": "gathering"' in formatted
    assert '"duration_ms": 12000' in formatted
    assert formatted.endswith("\n\n")


def test__gathering_progress_event__formats_correctly() -> None:
    """GatheringProgressEvent formats with progress details."""
    event = GatheringProgressEvent(
        data={
            "completed": 2,
            "total": 5,
            "current_query": "quantum computing breakthroughs 2024",
        }
    )
    formatted = event.format()

    assert formatted.startswith("event: gathering_progress\n")
    assert "data: {" in formatted
    assert '"completed": 2' in formatted
    assert '"total": 5' in formatted
    assert formatted.endswith("\n\n")


def test__heartbeat_event__has_empty_data() -> None:
    """HeartbeatEvent has empty data dict."""
    event = HeartbeatEvent()
    assert event.data == {}
    assert event.event == SSEEventType.HEARTBEAT


def test__heartbeat_event__formats_as_comment() -> None:
    """HeartbeatEvent formats as SSE comment, not named event."""
    event = HeartbeatEvent()
    formatted = event.format()

    # Should be comment format, not event format
    assert formatted == ": keepalive\n\n"
    assert not formatted.startswith("event:")
    assert "data:" not in formatted


def test__complete_event__serializes_full_result() -> None:
    """CompleteEvent includes full ResearchResult."""
    result = ResearchResult(
        query="test query",
        plan=ResearchPlan(
            executive_summary="Summary",
            web_search_steps=[SearchStep(search_terms="q", purpose="p")],
            analysis_instructions="Instructions",
        ),
        search_results=[SearchResult(query="q", findings=["f"], sources=["s"])],
        report=ResearchReport(title="T", summary="S", key_findings=["kf"], sources=["src"]),
        validation=ValidationResult(is_valid=True, confidence_score=0.9),
        timings=PhaseTimings(planning_ms=10, gathering_ms=20, synthesis_ms=30, verification_ms=40, total_ms=100),
    )

    event = CompleteEvent(data=result.model_dump())
    formatted = event.format()

    assert formatted.startswith("event: complete\n")
    assert "data: {" in formatted
    assert '"query": "test query"' in formatted
    assert formatted.endswith("\n\n")

    # Verify data is valid JSON
    data_line = formatted.split("\n")[1]
    assert data_line.startswith("data: ")
    data_json = data_line[6:]  # Remove "data: " prefix
    parsed = json.loads(data_json)
    assert parsed["query"] == "test query"


def test__error_event__includes_phase_context() -> None:
    """ErrorEvent includes phase context for debugging."""
    event = ErrorEvent(
        data={
            "error": "Unable to create research plan",
            "phase": "planning",
            "error_type": "PlanningError",
        }
    )
    formatted = event.format()

    assert formatted.startswith("event: error\n")
    assert "data: {" in formatted
    assert '"phase": "planning"' in formatted
    assert '"error_type": "PlanningError"' in formatted
    assert formatted.endswith("\n\n")


def test__phase_warning_event__formats_correctly() -> None:
    """PhaseWarningEvent formats with warning message."""
    event = PhaseWarningEvent(
        data={
            "phase": "gathering",
            "warning": "2 of 5 searches failed, continuing with partial results",
        }
    )
    formatted = event.format()

    assert formatted.startswith("event: phase_warning\n")
    assert "data: {" in formatted
    assert '"phase": "gathering"' in formatted
    assert '"warning"' in formatted
    assert formatted.endswith("\n\n")


def test__all_events__end_with_double_newline() -> None:
    """All SSE events must end with double newline."""
    events = [
        PhaseStartEvent(data={"phase": "planning"}),
        PhaseCompleteEvent(data={"phase": "planning", "duration_ms": 100, "output_summary": {}}),
        GatheringProgressEvent(data={"completed": 1, "total": 5, "current_query": "test"}),
        HeartbeatEvent(),
        ErrorEvent(data={"error": "test", "phase": "planning", "error_type": "TestError"}),
        PhaseWarningEvent(data={"phase": "gathering", "warning": "test warning"}),
    ]

    for event in events:
        formatted = event.format()
        assert formatted.endswith("\n\n"), f"{event.event} does not end with double newline"


def test__sse_event_type__has_all_expected_types() -> None:
    """SSEEventType enum has all expected event types."""
    expected_types = {
        "phase_start",
        "phase_complete",
        "gathering_progress",
        "heartbeat",
        "complete",
        "error",
        "phase_warning",
    }

    actual_types = {e.value for e in SSEEventType}
    assert actual_types == expected_types
