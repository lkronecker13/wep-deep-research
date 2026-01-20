import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger

# ============================================================================
# Configuration & Constants
# ============================================================================


class LogKeys(str, Enum):
    """Enum for log field keys to prevent typos and improve maintainability."""

    CORRELATION_ID = "correlation_id"
    CONTEXT = "context"
    TIMESTAMP = "timestamp"
    LOGGER = "logger"
    MESSAGE = "message"
    LEVEL = "level"
    EXTRA = "extra"


@dataclass(frozen=True)
class LogDefaults:
    """Default values for logging configuration."""

    context: str = "default"
    correlation_id: str = "unknown"
    log_level: str = "INFO"
    max_value_length: int = 50
    correlation_id_display_length: int = 8


# Immutable defaults instance
DEFAULTS = LogDefaults()


# ============================================================================
# Context Operations
# ============================================================================


def _get_context_value(key: str, default: str) -> str:
    """Get a value from context variables with fallback."""
    return str(structlog.contextvars.get_contextvars().get(key, default))


def get_correlation_id() -> str:
    """Get current correlation ID from context."""
    return _get_context_value(LogKeys.CORRELATION_ID.value, DEFAULTS.correlation_id)


# ============================================================================
# Log Processing (Universal)
# ============================================================================


def _process_log_fields(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    """Process log fields by restructuring event_dict for consistent formatting."""
    # Rename "event" to "message" for clarity
    event_dict[LogKeys.MESSAGE.value] = event_dict.pop("event", "")

    # Add context and correlation data
    event_dict[LogKeys.CONTEXT.value] = _get_context_value(LogKeys.CONTEXT.value, DEFAULTS.context)
    correlation_id = _get_context_value(LogKeys.CORRELATION_ID.value, DEFAULTS.correlation_id)

    # Extract non-standard fields to 'extra'
    standard_fields = (
        LogKeys.TIMESTAMP.value,
        LogKeys.LOGGER.value,
        LogKeys.MESSAGE.value,
        LogKeys.CONTEXT.value,
        LogKeys.LEVEL.value,
    )
    extra_fields = {key: event_dict.pop(key) for key in list(event_dict.keys()) if key not in standard_fields}

    # Add correlation ID to extra if it's not the default
    if correlation_id != DEFAULTS.correlation_id:
        extra_fields[LogKeys.CORRELATION_ID.value] = correlation_id

    # Add extra fields if any exist
    if extra_fields:
        event_dict[LogKeys.EXTRA.value] = extra_fields

    return event_dict


# ============================================================================
# Human-Readable Formatting
# ============================================================================


class HumanReadableFormatter:
    """Encapsulates human-readable log formatting logic for structlog processor."""

    def __init__(self, defaults: LogDefaults = DEFAULTS):
        self.defaults = defaults

    def __call__(self, _: WrappedLogger, __: str, event_dict: EventDict) -> str:
        """Format EventDict for human-readable output (structlog processor).

        Format: HH:MM:SS [LEVEL] logger: message [key_info] [correlation_id]
        """
        # Extract key components with safe defaults
        level = event_dict.get(LogKeys.LEVEL.value, "info").upper()
        logger_name = self.format_logger_name(event_dict.get(LogKeys.LOGGER.value, ""))
        message = event_dict.get(LogKeys.MESSAGE.value, "")
        timestamp = event_dict.get(LogKeys.TIMESTAMP.value, "")
        extra = event_dict.get(LogKeys.EXTRA.value, {})

        # Format components
        time_str = self.format_timestamp(timestamp)
        extra_str = self.format_extra_fields(extra)
        correlation_id = extra.get(LogKeys.CORRELATION_ID.value, "")
        corr_str = self.format_correlation_id(correlation_id)

        return f"{time_str} [{level}] {logger_name}: {message}{extra_str}{corr_str}"

    def format_field_value(self, value: Any) -> str:
        """Format a single field value, truncating if too long."""
        str_value = str(value)
        if len(str_value) > self.defaults.max_value_length:
            return f"{str_value[: self.defaults.max_value_length - 3]}..."
        return str_value

    def format_timestamp(self, timestamp_str: str) -> str:
        """Convert ISO timestamp to HH:MM:SS format."""
        if not timestamp_str:
            return ""

        try:
            # Parse ISO timestamp and format as HH:MM:SS
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            return dt.strftime("%H:%M:%S")
        except (ValueError, AttributeError):
            # Fallback: try to extract time portion manually
            return timestamp_str.split("T")[1][:8] if "T" in timestamp_str else ""

    def format_correlation_id(self, correlation_id: str) -> str:
        """Format correlation ID for display, truncating to readable length."""
        if not correlation_id:
            return ""
        truncated = correlation_id[: self.defaults.correlation_id_display_length]
        return f" [id:{truncated}]"

    def format_logger_name(self, logger_name: str) -> str:
        if not logger_name.startswith("src"):
            return logger_name

        # Remove the src prefix and return the meaningful part
        parts = logger_name.replace("src.", "").split(".")

        # Keep last 2 parts for context (e.g., "core.chat", "services.llm")
        if len(parts) >= 2:
            return f"{parts[-2]}.{parts[-1]}"
        return parts[-1] if parts else logger_name

    def format_extra_fields(self, extra: dict[str, Any]) -> str:
        if not extra:
            return ""

        formatted_parts = [f"{key}={self.format_field_value(value)}" for key, value in extra.items()]
        return f" [{', '.join(formatted_parts)}]"


# ============================================================================
# Configuration
# ============================================================================


def configure_structlog(testing: bool = False) -> None:
    """Configure structured logging with JSON or human-readable output format."""
    # Get logging level from environment with default
    log_level = os.environ.get("LOGGING_LEVEL", DEFAULTS.log_level).upper()
    level = getattr(logging, log_level, logging.INFO)

    logging.basicConfig(format="%(message)s", level=level, stream=sys.stdout)
    logging.getLogger().setLevel(level)

    # Build processor pipeline
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.contextvars.merge_contextvars,
        _process_log_fields,
        structlog.processors.TimeStamper(fmt="iso"),
        HumanReadableFormatter() if testing else structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=processors,  # type: ignore[arg-type]
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )


# ============================================================================
# Public API
# ============================================================================


def clear_context_fields() -> None:
    """Clear all context variables."""
    structlog.contextvars.clear_contextvars()


def bind_context_vars(**kwargs: Any) -> None:
    """Bind context variables for logging."""
    structlog.contextvars.bind_contextvars(**kwargs)


def get_context_vars() -> dict[str, Any]:
    return structlog.contextvars.get_contextvars()


def get_logger(name: str = "") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name or __name__)  # type: ignore
