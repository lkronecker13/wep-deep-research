"""FastAPI application for deep research service."""

import structlog
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from src import __version__
from src.exceptions import ResearchPipelineError
from src.models import ResearchResult
from src.workflow import run_research_workflow

log = structlog.get_logger("src.server")


# --- Request/Response schemas ---


class ResearchRequest(BaseModel):
    """Incoming research request."""

    query: str = Field(
        min_length=1,
        max_length=1000,
        description="Research question to investigate (1-1000 characters)",
        examples=["What are the latest developments in quantum computing?"],
    )


class ErrorResponse(BaseModel):
    """Structured error response."""

    error: str = Field(
        description="Error type (PlanningError, GatheringError, SynthesisError, VerificationError, ValidationError, InternalServerError)",
        examples=["GatheringError"],
    )
    detail: str = Field(
        description="User-friendly error message explaining what went wrong",
        examples=["Unable to gather sufficient information. Please try again."],
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(
        description="Service health status",
        examples=["ok"],
    )
    version: str = Field(
        default="",
        description="Service version (only included in /health endpoint)",
        examples=["0.1.0"],
    )


# --- Exception handlers ---

# Map domain exception types to user-friendly messages
_SAFE_ERROR_MESSAGES: dict[str, str] = {
    "PlanningError": "Unable to create research plan. Please try a different query.",
    "GatheringError": "Unable to gather sufficient information. Please try again.",
    "SynthesisError": "Unable to generate research report. Please try again.",
    "VerificationError": "Unable to verify research quality. Please try again.",
}


async def _handle_pipeline_error(request: Request, exc: ResearchPipelineError) -> JSONResponse:
    error_type = type(exc).__name__
    log.warning("request.pipeline_error", error_type=error_type, detail=str(exc))
    safe_detail = _SAFE_ERROR_MESSAGES.get(error_type, "An error occurred processing your request.")
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(error=error_type, detail=safe_detail).model_dump(),
    )


async def _handle_validation_error(request: Request, exc: ValidationError) -> JSONResponse:
    log.warning("request.validation_error", detail=str(exc))
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(error="ValidationError", detail=str(exc)).model_dump(),
    )


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    log.exception("request.unexpected_error", error=str(exc))
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error="InternalServerError", detail="An unexpected error occurred.").model_dump(),
    )


# --- App factory ---


def get_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="Deep Research Service",
        description="""
AI-powered deep research service using multi-agent workflows.

## Overview

Conducts comprehensive research on any topic using a 4-phase AI agent workflow:

1. **Planning Agent** - Creates structured research plan with 1-5 targeted search steps
2. **Gathering Agent** - Executes web searches in parallel to collect information
3. **Synthesis Agent** - Combines findings into a coherent research report
4. **Verification Agent** - Validates quality, accuracy, and completeness

## Performance

- **Duration**: 30-180 seconds depending on query complexity
- **Cost**: ~$0.30-0.50 per query
- **Models**: Claude Sonnet 4.5 (reasoning) + Gemini 2.5 Flash (parallel searches)

## Architecture

Built with PydanticAI, FastAPI, and DBOS for durable workflow execution.
        """,
        version=__version__,
        contact={
            "name": "Wepoint",
            "url": "https://www.wepoint.com",
        },
        license_info={
            "name": "Apache 2.0",
            "url": "https://www.apache.org/licenses/LICENSE-2.0",
        },
    )

    application.add_exception_handler(ResearchPipelineError, _handle_pipeline_error)  # type: ignore[arg-type]
    application.add_exception_handler(ValidationError, _handle_validation_error)  # type: ignore[arg-type]
    application.add_exception_handler(Exception, _handle_unexpected_error)

    @application.post(
        "/research",
        response_model=ResearchResult,
        status_code=status.HTTP_200_OK,
        summary="Execute Research Workflow",
        description="""
Conducts deep research using a 4-phase AI agent workflow.

## Workflow Phases

1. **Planning** - Creates structured research plan with 1-5 search steps
2. **Gathering** - Executes web searches in parallel using Gemini 2.5 Flash
3. **Synthesis** - Combines findings into coherent report using Claude Sonnet 4.5
4. **Verification** - Validates quality and accuracy of the research

## Performance

- **Duration**: 30-180 seconds depending on query complexity
- **Cost**: ~$0.30-0.50 per query (API costs)
- **Parallel Execution**: Multiple web searches execute simultaneously for efficiency

## Response Structure

Returns complete research results including:
- Original query
- Research plan with search steps
- Raw search results from all queries
- Synthesized research report with findings
- Quality validation results
- Timing metrics for each phase
        """,
        tags=["Research"],
        response_description="Complete research results with plan, findings, report, and validation",
        responses={
            200: {
                "description": "Research completed successfully",
                "model": ResearchResult,
            },
            422: {
                "description": "Research pipeline error (planning, gathering, synthesis, or verification failed)",
                "model": ErrorResponse,
                "content": {
                    "application/json": {
                        "examples": {
                            "planning_error": {
                                "summary": "Planning Error",
                                "value": {
                                    "error": "PlanningError",
                                    "detail": "Unable to create research plan. Please try a different query.",
                                },
                            },
                            "gathering_error": {
                                "summary": "Gathering Error",
                                "value": {
                                    "error": "GatheringError",
                                    "detail": "Unable to gather sufficient information. Please try again.",
                                },
                            },
                            "synthesis_error": {
                                "summary": "Synthesis Error",
                                "value": {
                                    "error": "SynthesisError",
                                    "detail": "Unable to generate research report. Please try again.",
                                },
                            },
                            "verification_error": {
                                "summary": "Verification Error",
                                "value": {
                                    "error": "VerificationError",
                                    "detail": "Unable to verify research quality. Please try again.",
                                },
                            },
                        }
                    }
                },
            },
            500: {
                "description": "Internal server error",
                "model": ErrorResponse,
                "content": {
                    "application/json": {
                        "example": {
                            "error": "InternalServerError",
                            "detail": "An unexpected error occurred.",
                        }
                    }
                },
            },
        },
    )
    async def research(body: ResearchRequest) -> ResearchResult:
        return await run_research_workflow(body.query)

    @application.get(
        "/health",
        response_model=HealthResponse,
        status_code=status.HTTP_200_OK,
        summary="Health Check",
        description="""
General health check endpoint that returns service status and version.

Use this endpoint for monitoring and smoke testing the service.
        """,
        tags=["Health"],
        response_description="Service health status and version",
    )
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", version=__version__)

    @application.get(
        "/health/liveness",
        response_model=HealthResponse,
        status_code=status.HTTP_200_OK,
        summary="Liveness Probe",
        description="""
Kubernetes liveness probe endpoint.

Returns 200 OK if the service is running and can accept requests.
If this endpoint fails, Kubernetes will restart the pod.

Does not include version information to minimize overhead.
        """,
        tags=["Health"],
        response_description="Service is alive and accepting requests",
    )
    async def liveness() -> HealthResponse:
        return HealthResponse(status="alive")

    @application.get(
        "/health/readiness",
        response_model=HealthResponse,
        status_code=status.HTTP_200_OK,
        summary="Readiness Probe",
        description="""
Kubernetes readiness probe endpoint.

Returns 200 OK if the service is ready to handle research requests.
If this endpoint fails, Kubernetes will stop routing traffic to the pod.

Use this for load balancer health checks and deployment validation.
        """,
        tags=["Health"],
        response_description="Service is ready to handle research requests",
    )
    async def readiness() -> HealthResponse:
        return HealthResponse(status="ready")

    return application


app = get_app()
