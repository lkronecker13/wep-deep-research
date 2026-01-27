"""Tests for FastAPI server."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI

from src.exceptions import GatheringError, PlanningError, SynthesisError, VerificationError
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


class TestResearchEndpoint:
    """Tests for /research endpoint."""

    @pytest.mark.asyncio
    async def test__valid_query__returns_200(self, app: FastAPI) -> None:
        with patch("src.server.run_research_workflow", new=AsyncMock(return_value=_make_research_result("test query"))):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/research", json={"query": "test query"})
                assert response.status_code == 200
                data = response.json()
                assert data["query"] == "test query"

    @pytest.mark.asyncio
    async def test__empty_query__returns_422(self, app: FastAPI) -> None:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/research", json={"query": ""})
            assert response.status_code == 422
            data = response.json()
            # FastAPI's default validation error format
            assert "detail" in data

    @pytest.mark.asyncio
    async def test__query_too_long__returns_422(self, app: FastAPI) -> None:
        long_query = "x" * 1001
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/research", json={"query": long_query})
            assert response.status_code == 422
            data = response.json()
            # FastAPI's default validation error format
            assert "detail" in data

    @pytest.mark.asyncio
    async def test__planning_error__returns_422(self, app: FastAPI) -> None:
        with patch(
            "src.server.run_research_workflow",
            new=AsyncMock(side_effect=PlanningError(topic="test", reason="Plan failed")),
        ):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/research", json={"query": "test query"})
                assert response.status_code == 422
                data = response.json()
                assert data["error"] == "PlanningError"
                assert data["detail"] == "Unable to create research plan. Please try a different query."

    @pytest.mark.asyncio
    async def test__gathering_error__returns_422(self, app: FastAPI) -> None:
        with patch(
            "src.server.run_research_workflow",
            new=AsyncMock(side_effect=GatheringError(attempted=3, failed=3)),
        ):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/research", json={"query": "test query"})
                assert response.status_code == 422
                data = response.json()
                assert data["error"] == "GatheringError"
                assert data["detail"] == "Unable to gather sufficient information. Please try again."

    @pytest.mark.asyncio
    async def test__synthesis_error__returns_422(self, app: FastAPI) -> None:
        with patch(
            "src.server.run_research_workflow",
            new=AsyncMock(side_effect=SynthesisError(reason="Synthesis failed")),
        ):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/research", json={"query": "test query"})
                assert response.status_code == 422
                data = response.json()
                assert data["error"] == "SynthesisError"
                assert data["detail"] == "Unable to generate research report. Please try again."

    @pytest.mark.asyncio
    async def test__verification_error__returns_422(self, app: FastAPI) -> None:
        with patch(
            "src.server.run_research_workflow",
            new=AsyncMock(side_effect=VerificationError(reason="Verification failed")),
        ):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/research", json={"query": "test query"})
                assert response.status_code == 422
                data = response.json()
                assert data["error"] == "VerificationError"
                assert data["detail"] == "Unable to verify research quality. Please try again."

    @pytest.mark.asyncio
    async def test__unexpected_error__returns_500(self, app: FastAPI) -> None:
        with patch(
            "src.server.run_research_workflow",
            new=AsyncMock(side_effect=RuntimeError("Unexpected error")),
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
            ) as client:
                response = await client.post("/research", json={"query": "test query"})
                assert response.status_code == 500
                data = response.json()
                assert data["error"] == "InternalServerError"


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    @pytest.mark.asyncio
    async def test__health__returns_ok(self, app: FastAPI) -> None:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "version" in data

    @pytest.mark.asyncio
    async def test__liveness__returns_alive(self, app: FastAPI) -> None:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health/liveness")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "alive"

    @pytest.mark.asyncio
    async def test__readiness__returns_ready(self, app: FastAPI) -> None:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health/readiness")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"


class TestAppFactory:
    """Tests for app factory function."""

    def test__get_app__returns_fastapi(self) -> None:
        from fastapi import FastAPI

        app = get_app()
        assert isinstance(app, FastAPI)

    def test__get_app__has_research_route(self) -> None:
        app = get_app()
        routes = [route.path for route in app.routes]
        assert "/research" in routes

    def test__get_app__has_health_routes(self) -> None:
        app = get_app()
        routes = [route.path for route in app.routes]
        assert "/health" in routes
        assert "/health/liveness" in routes
        assert "/health/readiness" in routes
