"""FastAPI application for deep research service."""

import asyncio
from typing import AsyncIterator

import structlog
from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, ValidationError

from src import __version__
from src.demo import generate_demo_sse_stream, get_demo_research_result, is_demo_mode_allowed
from src.events import CompleteEvent, ErrorEvent, SSEEvent
from src.exceptions import ResearchPipelineError
from src.models import ResearchResult
from src.workflow import run_research_workflow

log = structlog.get_logger("src.server")

# SSE Configuration
HEARTBEAT_INTERVAL = 30  # seconds
MAX_DURATION = 600  # 10 minutes (GCP Cloud Run configured timeout)
MAX_QUEUE_SIZE = 100  # Bounded queue to prevent memory leaks


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

    def _get_safe_error_message(exc: Exception) -> str:
        """Get safe error message for streaming response."""
        error_type = type(exc).__name__
        return _SAFE_ERROR_MESSAGES.get(error_type, "An error occurred processing your request.")

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
    async def research(
        body: ResearchRequest,
        demo: bool = Query(default=False, description="Enable demo mode with hardcoded response for frontend testing"),
    ) -> ResearchResult:
        if demo:
            if not is_demo_mode_allowed():
                raise HTTPException(
                    status_code=403,
                    detail="Demo mode not available in this environment",
                )
            log.warning("demo_mode_active", query=body.query, endpoint="/research")
            return get_demo_research_result(body.query)

        return await run_research_workflow(body.query)

    @application.post(
        "/research/stream",
        response_class=StreamingResponse,
        responses={
            200: {
                "description": "Server-Sent Events stream of research progress",
                "content": {"text/event-stream": {"example": "event: phase_complete\ndata: {...}\n\n"}},
            },
            422: {"model": ErrorResponse},
        },
        summary="Execute research with streaming progress updates",
        description="""
Execute the 4-phase deep research workflow with real-time progress updates via SSE.

**Event Types:**
- `phase_start`: Phase beginning (planning, gathering, synthesis, verification)
- `phase_complete`: Phase finished with duration and summary
- `gathering_progress`: Individual search completion (N of M)
- `heartbeat`: Keep-alive comment every 30s (`: keepalive`)
- `complete`: Final result with full ResearchResult
- `error`: Error occurred in specific phase

**Connection:** Automatically closes after workflow completion or 10-minute timeout.
**Reconnection:** Client should implement exponential backoff if connection drops.
        """,
        tags=["Research"],
    )
    async def research_stream(
        request: Request,
        research_request: ResearchRequest,
        demo: bool = Query(
            default=False, description="Enable demo mode with hardcoded SSE events for frontend testing"
        ),
    ) -> StreamingResponse:
        """Execute research workflow with SSE progress streaming."""

        if demo:
            if not is_demo_mode_allowed():
                raise HTTPException(
                    status_code=403,
                    detail="Demo mode not available in this environment",
                )
            log.warning("demo_mode_active", query=research_request.query, endpoint="/research/stream")

            return StreamingResponse(
                generate_demo_sse_stream(research_request.query),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                    "Connection": "keep-alive",
                },
            )

        async def event_generator() -> AsyncIterator[str]:
            """Generate SSE events from workflow execution."""
            # Bounded queue to prevent memory leaks
            event_queue: asyncio.Queue[SSEEvent] = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
            workflow_complete = asyncio.Event()
            workflow_error: Exception | None = None

            async def event_callback(event: SSEEvent) -> None:
                """Callback for workflow to emit events (with backpressure)."""
                try:
                    await asyncio.wait_for(event_queue.put(event), timeout=5.0)
                except asyncio.TimeoutError:
                    log.warning("event_queue_full", event=event.event)
                    # Queue full - drop event or apply backpressure strategy

            async def run_workflow_task() -> None:
                """Background task executing research workflow."""
                nonlocal workflow_error
                try:
                    result = await run_research_workflow(
                        query=research_request.query,
                        event_callback=event_callback,
                    )
                    # Send completion event with full result
                    await event_queue.put(CompleteEvent(data=result.model_dump()))
                except Exception as e:
                    log.error("workflow_error", error=str(e), exc_info=True)
                    workflow_error = e
                    await event_queue.put(
                        ErrorEvent(
                            data={
                                "error": _get_safe_error_message(e),
                                "error_type": e.__class__.__name__,
                                "phase": "unknown",
                            }
                        )
                    )
                finally:
                    workflow_complete.set()

            # Start workflow in background
            workflow_task = asyncio.create_task(run_workflow_task())

            # Stream events with heartbeat management
            start_time = asyncio.get_event_loop().time()
            next_heartbeat = start_time + HEARTBEAT_INTERVAL

            try:
                while not workflow_complete.is_set():
                    current_time = asyncio.get_event_loop().time()
                    elapsed = current_time - start_time

                    # Enforce maximum duration
                    if elapsed > MAX_DURATION:
                        log.warning("stream_timeout", elapsed=elapsed, max=MAX_DURATION)
                        workflow_task.cancel()  # Cancel long-running workflow
                        yield ErrorEvent(
                            data={
                                "error": "Research timeout - workflow exceeded 10 minutes",
                                "error_type": "TimeoutError",
                                "phase": "timeout",
                            }
                        ).format()
                        break

                    # Check for client disconnect EVERY iteration
                    if await request.is_disconnected():
                        log.info("client_disconnected", elapsed=elapsed)
                        workflow_task.cancel()  # Cancel background workflow
                        break

                    # Send heartbeat if needed (no drift accumulation)
                    if current_time >= next_heartbeat:
                        yield ": keepalive\n\n"  # SSE comment format
                        next_heartbeat += HEARTBEAT_INTERVAL  # No drift

                    # Wait for next event with timeout (short for responsive disconnect detection)
                    try:
                        event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                        yield event.format()
                    except asyncio.TimeoutError:
                        continue  # No event available, loop to check heartbeat/disconnect

                # Drain remaining events in queue
                while not event_queue.empty():
                    event = event_queue.get_nowait()
                    yield event.format()

            finally:
                # Ensure background task is cancelled (always cancel, idempotent if done)
                workflow_task.cancel()
                try:
                    await asyncio.wait_for(workflow_task, timeout=10.0)
                except asyncio.CancelledError:
                    log.info("workflow_cancelled")
                except asyncio.TimeoutError:
                    log.error("workflow_cancellation_timeout")
                except Exception as e:
                    log.exception("workflow_failed_during_cleanup", error=str(e))

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # Disable proxy buffering
                "Connection": "keep-alive",
            },
        )

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
