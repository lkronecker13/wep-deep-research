"""FastAPI application for deep research service."""

import structlog
from fastapi import FastAPI, Request
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

    query: str = Field(min_length=1, max_length=1000)


class ErrorResponse(BaseModel):
    """Structured error response."""

    error: str
    detail: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str = ""


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
    application = FastAPI(title="Deep Research Service", version=__version__)

    application.add_exception_handler(ResearchPipelineError, _handle_pipeline_error)  # type: ignore[arg-type]
    application.add_exception_handler(ValidationError, _handle_validation_error)  # type: ignore[arg-type]
    application.add_exception_handler(Exception, _handle_unexpected_error)

    @application.post("/research", response_model=ResearchResult)
    async def research(body: ResearchRequest) -> ResearchResult:
        return await run_research_workflow(body.query)

    @application.get("/health")
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", version=__version__)

    @application.get("/health/liveness")
    async def liveness() -> HealthResponse:
        return HealthResponse(status="alive")

    @application.get("/health/readiness")
    async def readiness() -> HealthResponse:
        return HealthResponse(status="ready")

    return application


app = get_app()
