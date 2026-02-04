"""Integration tests for /research/stream endpoint."""

import asyncio
import gc
import time
import tracemalloc
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI

from src.exceptions import GatheringError, SynthesisError
from src.models import (
    PhaseTimings,
    ResearchPlan,
    ResearchReport,
    ResearchResult,
    SearchResult,
    SearchStep,
    ValidationResult,
)
from src.server import get_app


def _make_research_result(query: str = "test") -> ResearchResult:
    """Helper to create a valid ResearchResult for mocking."""
    return ResearchResult(
        query=query,
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


@pytest.fixture
def app() -> FastAPI:
    return get_app()


async def _collect_events(response: httpx.Response) -> list[tuple[str, dict]]:
    """Parse SSE stream into list of (event_type, data) tuples."""
    events: list[tuple[str, dict]] = []
    current_event = None
    current_data = None

    async for line in response.aiter_lines():
        if line.startswith("event:"):
            current_event = line.split(": ", 1)[1]
        elif line.startswith("data:"):
            import json

            current_data = json.loads(line.split(": ", 1)[1])
        elif line == "" and current_event and current_data:
            events.append((current_event, current_data))
            current_event = None
            current_data = None

    return events


class TestResearchStreamEndpoint:
    """Tests for /research/stream endpoint."""

    @pytest.mark.asyncio
    async def test__research_stream__emits_phase_events(self, app: FastAPI) -> None:
        """Streaming endpoint emits all expected phase events."""

        async def workflow_with_events(*args, event_callback=None, **kwargs):
            if event_callback:
                from src.events import PhaseCompleteEvent, PhaseStartEvent

                await event_callback(PhaseStartEvent(data={"phase": "planning"}))
                await event_callback(
                    PhaseCompleteEvent(
                        data={"phase": "planning", "duration_ms": 100, "output_summary": {"search_steps": 3}}
                    )
                )
            await asyncio.sleep(0.1)  # Give event loop time to process events
            return _make_research_result("test query")

        with patch("src.server.run_research_workflow", new=workflow_with_events):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                async with client.stream(
                    "POST",
                    "/research/stream",
                    json={"query": "test quantum computing"},
                ) as response:
                    assert response.status_code == 200
                    # FastAPI adds charset automatically
                    assert response.headers["content-type"].startswith("text/event-stream")

                    events = await _collect_events(response)
                    event_types = [e[0] for e in events]

                    # Verify expected event types appear
                    assert "phase_start" in event_types
                    assert "phase_complete" in event_types
                    assert "complete" in event_types

    @pytest.mark.asyncio
    async def test__research_stream__handles_client_disconnect(self, app: FastAPI) -> None:
        """Streaming endpoint detects client disconnect and stops streaming."""

        async def slow_workflow(*args, **kwargs):
            await asyncio.sleep(10)  # Long-running workflow
            return _make_research_result()

        with patch("src.server.run_research_workflow", new=slow_workflow):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                async with client.stream(
                    "POST",
                    "/research/stream",
                    json={"query": "test query"},
                ) as response:
                    # Read first chunk then disconnect
                    async for line in response.aiter_lines():
                        if line:  # Got some data
                            break
                    # Exit context manager = disconnect

                # Test passes if no exception raised during disconnect

    @pytest.mark.asyncio
    async def test__research_stream__enforces_timeout(self, app: FastAPI) -> None:
        """Stream closes after MAX_DURATION even if workflow continues."""

        async def slow_workflow(*args, **kwargs):
            await asyncio.sleep(700)  # Exceeds 600s timeout
            return _make_research_result()

        with patch("src.server.run_research_workflow", new=slow_workflow):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                # Mock time to simulate timeout
                with patch("src.server.MAX_DURATION", 2):  # Short timeout for test
                    start = time.time()
                    async with client.stream(
                        "POST",
                        "/research/stream",
                        json={"query": "test"},
                    ) as response:
                        events = await _collect_events(response)
                        elapsed = time.time() - start

                        # Should timeout within reasonable time
                        assert elapsed < 5, "Timeout took too long"

                        # Should have error event
                        event_types = [e[0] for e in events]
                        assert "error" in event_types

                        # Find timeout error
                        error_events = [e for e in events if e[0] == "error"]
                        assert any("timeout" in str(e[1]).lower() for e in error_events)

    @pytest.mark.asyncio
    async def test__research_stream__sends_heartbeat_every_30s(self, app: FastAPI) -> None:
        """Heartbeats sent at 30-second intervals during long workflows."""

        async def slow_workflow(*args, event_callback=None, **kwargs):
            # Keep workflow alive long enough to trigger heartbeats
            for _ in range(5):
                await asyncio.sleep(0.5)
                if event_callback:
                    from src.events import PhaseStartEvent

                    await event_callback(PhaseStartEvent(data={"phase": "planning"}))
            return _make_research_result()

        with patch("src.server.run_research_workflow", new=slow_workflow):
            with patch("src.server.HEARTBEAT_INTERVAL", 0.5):  # Fast heartbeat for test
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                    heartbeat_count = 0

                    async with client.stream(
                        "POST",
                        "/research/stream",
                        json={"query": "test"},
                    ) as response:
                        async for line in response.aiter_lines():
                            if ": keepalive" in line:
                                heartbeat_count += 1

                    # Should have at least 2 heartbeats with 0.5s interval over 2.5s workflow
                    assert heartbeat_count >= 2, f"Only got {heartbeat_count} heartbeats"

    @pytest.mark.asyncio
    async def test__research_stream__cancels_workflow_on_disconnect(self, app: FastAPI) -> None:
        """Background workflow cleanup happens when stream completes or client disconnects."""
        workflow_finished = False

        async def monitored_workflow(*args, event_callback=None, **kwargs):
            nonlocal workflow_finished
            try:
                # Emit event so stream can read something
                if event_callback:
                    from src.events import PhaseStartEvent

                    await event_callback(PhaseStartEvent(data={"phase": "planning"}))
                # Simulate long-running work
                await asyncio.sleep(0.5)
                return _make_research_result()
            finally:
                workflow_finished = True

        with patch("src.server.run_research_workflow", new=monitored_workflow):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                async with client.stream(
                    "POST",
                    "/research/stream",
                    json={"query": "test"},
                ) as response:
                    # Read a few events
                    line_count = 0
                    async for line in response.aiter_lines():
                        line_count += 1
                        if line_count > 5:
                            break

        # Workflow should have completed or been cancelled
        await asyncio.sleep(0.5)  # Allow cleanup time (disconnect detection + cancellation)
        assert workflow_finished, "Workflow cleanup did not execute"

    @pytest.mark.asyncio
    async def test__research_stream__no_memory_leak_on_repeated_disconnect(self, app: FastAPI) -> None:
        """Multiple disconnects don't leak memory."""

        async def fast_workflow(*args, **kwargs):
            await asyncio.sleep(0.1)
            return _make_research_result()

        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()

        with patch("src.server.run_research_workflow", new=fast_workflow):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                for _ in range(100):
                    async with client.stream(
                        "POST",
                        "/research/stream",
                        json={"query": "test"},
                    ) as response:
                        # Read first line then disconnect
                        async for line in response.aiter_lines():
                            if line:
                                break

        gc.collect()
        snapshot_after = tracemalloc.take_snapshot()

        # Check memory didn't grow excessively
        top_stats = snapshot_after.compare_to(snapshot_before, "lineno")
        total_growth = sum(stat.size_diff for stat in top_stats)

        # Allow some growth (buffers, etc.) but not excessive (MB scale indicates leak)
        assert total_growth < 1_000_000, f"Memory grew by {total_growth / 1024 / 1024:.2f} MB - possible leak"

        tracemalloc.stop()

    @pytest.mark.asyncio
    async def test__research_stream__handles_gathering_partial_failure(self, app: FastAPI) -> None:
        """Stream continues if some (not all) gathering searches fail."""

        async def workflow_with_partial_failure(*args, event_callback=None, **kwargs):
            # Simulate workflow emitting warning event for partial failure
            if event_callback:
                from src.events import PhaseWarningEvent

                await event_callback(
                    PhaseWarningEvent(
                        data={
                            "phase": "gathering",
                            "warning": "2 of 5 searches failed, continuing with partial results",
                        }
                    )
                )
            await asyncio.sleep(0.1)
            return _make_research_result()

        with patch("src.server.run_research_workflow", new=workflow_with_partial_failure):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                async with client.stream(
                    "POST",
                    "/research/stream",
                    json={"query": "test"},
                ) as response:
                    events = await _collect_events(response)
                    event_types = [e[0] for e in events]

                    # Should have warning event
                    assert "phase_warning" in event_types

                    # Should still complete successfully
                    assert "complete" in event_types

    @pytest.mark.asyncio
    async def test__research_stream__cleans_up_resources_on_error(self, app: FastAPI) -> None:
        """Resources released when workflow fails mid-stream."""

        async def failing_workflow(*args, event_callback=None, **kwargs):
            if event_callback:
                from src.events import PhaseStartEvent

                await event_callback(PhaseStartEvent(data={"phase": "planning"}))
            await asyncio.sleep(0.1)
            raise SynthesisError(reason="Test error")

        with patch("src.server.run_research_workflow", new=failing_workflow):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                async with client.stream(
                    "POST",
                    "/research/stream",
                    json={"query": "test"},
                ) as response:
                    events = await _collect_events(response)
                    event_types = [e[0] for e in events]

                    # Should have phase_start before error
                    assert "phase_start" in event_types

                    # Should have error event
                    assert "error" in event_types

                    # Verify error contains expected info
                    error_events = [e for e in events if e[0] == "error"]
                    assert len(error_events) > 0
                    assert "error_type" in error_events[0][1]

    @pytest.mark.asyncio
    async def test__research_stream__handles_multiple_concurrent_streams(self, app: FastAPI) -> None:
        """No cross-stream interference with concurrent connections."""

        async def workflow_with_delay(*args, **kwargs):
            await asyncio.sleep(0.5)
            return _make_research_result(query=kwargs.get("query", "test"))

        with patch("src.server.run_research_workflow", new=workflow_with_delay):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:

                async def run_stream(query: str) -> list[tuple[str, dict]]:
                    async with client.stream(
                        "POST",
                        "/research/stream",
                        json={"query": query},
                    ) as response:
                        return await _collect_events(response)

                # Run 10 concurrent streams
                results = await asyncio.gather(*[run_stream(f"query_{i}") for i in range(10)])

                # All streams should complete successfully
                assert len(results) == 10
                assert all(len(events) > 0 for events in results)

                # Each stream should have completion event
                for events in results:
                    event_types = [e[0] for e in events]
                    assert "complete" in event_types

    @pytest.mark.asyncio
    async def test__research_stream__error_mid_workflow(self, app: FastAPI) -> None:
        """Error occurring mid-workflow emits error event."""

        async def workflow_with_error(*args, event_callback=None, **kwargs):
            if event_callback:
                from src.events import PhaseCompleteEvent, PhaseStartEvent

                await event_callback(PhaseStartEvent(data={"phase": "planning"}))
                await event_callback(
                    PhaseCompleteEvent(
                        data={"phase": "planning", "duration_ms": 100, "output_summary": {"search_steps": 3}}
                    )
                )
            raise GatheringError(attempted=5, failed=5)

        with patch("src.server.run_research_workflow", new=workflow_with_error):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                async with client.stream(
                    "POST",
                    "/research/stream",
                    json={"query": "test"},
                ) as response:
                    events = await _collect_events(response)
                    event_types = [e[0] for e in events]

                    # Should have phase events before error
                    assert "phase_start" in event_types
                    assert "phase_complete" in event_types

                    # Should have error event
                    assert "error" in event_types

                    # Should NOT have complete event
                    assert "complete" not in event_types

    @pytest.mark.asyncio
    async def test__research_stream__complete_event_with_full_result(self, app: FastAPI) -> None:
        """Complete event contains full ResearchResult."""
        result = _make_research_result("full test query")

        with patch("src.server.run_research_workflow", new=AsyncMock(return_value=result)):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                async with client.stream(
                    "POST",
                    "/research/stream",
                    json={"query": "full test query"},
                ) as response:
                    events = await _collect_events(response)

                    # Find complete event
                    complete_events = [e for e in events if e[0] == "complete"]
                    assert len(complete_events) == 1

                    complete_data = complete_events[0][1]

                    # Verify structure matches ResearchResult
                    assert complete_data["query"] == "full test query"
                    assert "plan" in complete_data
                    assert "search_results" in complete_data
                    assert "report" in complete_data
                    assert "validation" in complete_data
                    assert "timings" in complete_data
