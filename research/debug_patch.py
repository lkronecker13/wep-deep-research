"""Monkey-patch PydanticAI to log validation failures.

This module patches the PydanticAI retry mechanism to capture raw responses
and validation errors before they're lost in the retry loop. Used for debugging
the Gemini output validation failures.

Usage:
    import research.debug_patch  # noqa - Import at module load to apply patch
"""

from __future__ import annotations

import pydantic_ai._agent_graph as ag

from src.logging import get_logger

log = get_logger("debug.validation")

# Store original method
_original_increment_retries = ag.GraphAgentState.increment_retries


def _patched_increment_retries(
    self: ag.GraphAgentState,
    max_result_retries: int,
    error: BaseException | None = None,
    model_settings: dict | None = None,
) -> None:
    """Patched version that logs validation errors before retrying."""
    if error:
        # Extract raw response from message history
        raw_response = None
        if self.message_history:
            last_message = self.message_history[-1]
            raw_response = str(last_message)

        log.error(
            "validation_error_before_retry",
            error_type=type(error).__name__,
            error_details=str(error),
            retry_count=self.retries,
            raw_response=raw_response,
        )

        # If it's a Pydantic ValidationError, log the structured errors
        if hasattr(error, "__cause__") and hasattr(error.__cause__, "errors"):
            try:
                validation_errors = error.__cause__.errors()
                log.error(
                    "pydantic_validation_details",
                    errors=validation_errors,
                    retry_count=self.retries,
                )
            except Exception as e:
                log.warning("failed_to_extract_validation_errors", extraction_error=str(e))

    # Call original method
    return _original_increment_retries(self, max_result_retries, error, model_settings)


# Apply patch
ag.GraphAgentState.increment_retries = _patched_increment_retries  # type: ignore[method-assign]

log.info("debug_patch_applied", patched_method="GraphAgentState.increment_retries")
