"""Phoenix OpenTelemetry tracing integration for Arize Cloud.

This module handles initialization of Phoenix tracing and instrumentation
for LLM providers (Anthropic, Google GenAI). Tracing enables observability
of research workflows and evaluations in Arize Phoenix Cloud.

Environment Variables:
    PHOENIX_API_KEY: Arize Cloud API key for trace logging
    PHOENIX_COLLECTOR_ENDPOINT: Phoenix collector endpoint (optional)
"""

from __future__ import annotations

import os

from src.logging import get_logger

logger = get_logger("research.evaluation.tracing")


def init_phoenix_tracing() -> bool:
    """Initialize Phoenix OpenTelemetry tracing for Arize Cloud.

    Phoenix Client automatically reads PHOENIX_API_KEY and PHOENIX_COLLECTOR_ENDPOINT
    from environment variables.

    Returns:
        True if tracing was initialized successfully, False otherwise.
    """
    try:
        from phoenix.otel import register

        # Check if API key is configured
        if not os.environ.get("PHOENIX_API_KEY"):
            logger.warning(
                "phoenix_api_key_missing",
                message="Evaluations will not be logged to Arize Cloud",
            )
            return False

        # Register the tracer provider (Phoenix reads endpoint from env automatically)
        tracer_provider = register(project_name="deep-research-evals")

        # Enable instrumentors for LLM libraries
        _enable_instrumentors(tracer_provider)

        logger.info("phoenix_tracing_initialized", provider="arize_cloud")
        return True

    except ImportError as e:
        logger.warning("phoenix_import_failed", error=str(e), package="phoenix.otel")
        return False
    except Exception as e:
        logger.exception("phoenix_init_failed", error=str(e))
        return False


def _enable_instrumentors(tracer_provider: object) -> None:
    """Enable OpenInference instrumentors for agents and LLM libraries.

    Args:
        tracer_provider: The OpenTelemetry tracer provider from Phoenix.
    """
    # Note: PydanticAI uses InstrumentationSettings(version=2) on agents directly
    # The openinference-instrumentation-pydantic-ai package provides OpenInferenceSpanProcessor
    # but it conflicts with async TaskGroup execution, so we rely on the native instrumentation
    logger.info(
        "instrumentor_status",
        name="pydantic_ai",
        status="enabled",
        method="native",
    )

    # Instrument Anthropic (Claude)
    try:
        from openinference.instrumentation.anthropic import AnthropicInstrumentor

        AnthropicInstrumentor().instrument(tracer_provider=tracer_provider)
        logger.info("instrumentor_status", name="anthropic", status="enabled")
    except ImportError:
        logger.warning(
            "instrumentor_unavailable",
            name="anthropic",
            package="openinference-instrumentation-anthropic",
        )
    except Exception as e:
        logger.exception("instrumentor_failed", name="anthropic", error=str(e))

    # Instrument Google GenAI (Gemini)
    try:
        from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

        GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)
        logger.info("instrumentor_status", name="google_genai", status="enabled")
    except ImportError:
        logger.warning(
            "instrumentor_unavailable",
            name="google_genai",
            package="openinference-instrumentation-google-genai",
        )
    except Exception as e:
        logger.exception("instrumentor_failed", name="google_genai", error=str(e))


def is_tracing_enabled() -> bool:
    """Check if Phoenix tracing is configured.

    Returns:
        True if PHOENIX_API_KEY is set, False otherwise.
    """
    return bool(os.environ.get("PHOENIX_API_KEY"))
