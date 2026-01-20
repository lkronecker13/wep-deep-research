"""Functional tests for the logger module."""

import json
from typing import Any

import pytest
from pytest import LogCaptureFixture, MonkeyPatch

from src.logging import (
    bind_context_vars,
    clear_context_fields,
    configure_structlog,
    get_logger,
)

# ============================================================================
# Helpers
# ============================================================================


def parse_log_json(caplog: LogCaptureFixture, index: int = 0) -> dict[str, Any]:
    try:
        return json.loads(caplog.records[index].message)
    except (json.JSONDecodeError, IndexError) as e:
        records = [r.message for r in caplog.records]
        raise AssertionError(f"Failed to parse log {index}: {e}. Records: {records}")


def assert_json_log_structure(log_data: dict[str, Any]) -> None:
    required_fields = {"timestamp", "level", "logger", "message", "context"}
    missing_fields = required_fields - log_data.keys()
    assert not missing_fields, f"Missing required fields: {missing_fields}"


def assert_human_readable_format(log_message: str) -> None:
    with pytest.raises((json.JSONDecodeError, ValueError)):
        json.loads(log_message)

    # Should contain basic readable components
    assert "[" in log_message and "]" in log_message
    assert ":" in log_message


@pytest.fixture(autouse=True)
def setup_logger():
    configure_structlog()
    yield
    clear_context_fields()


# ============================================================================
# Core Functionality Tests
# ============================================================================


@pytest.mark.parametrize(
    "correlation_id",
    [
        "simple-123",
        "very-long-correlation-id-with-lots-of-characters-12345",
        "req-abc-123",
    ],
)
def test__correlation_id__appears_in_logs(caplog: LogCaptureFixture, correlation_id: str):
    bind_context_vars(correlation_id=correlation_id)

    get_logger("test").info("Test message")

    log_data = parse_log_json(caplog)
    assert log_data["extra"]["correlation_id"] == correlation_id


def test__correlation_id__propagates_across_loggers(caplog: LogCaptureFixture):
    bind_context_vars(correlation_id="propagate-test")

    get_logger("auth").info("Auth step")
    get_logger("db").info("DB step")
    get_logger("api").info("Response step")

    for i in range(3):
        log_data = parse_log_json(caplog, i)
        assert log_data["extra"]["correlation_id"] == "propagate-test"


def test__context__isolates_between_requests(caplog: LogCaptureFixture):
    # First request
    bind_context_vars(correlation_id="req-1", user_id="user-1")
    get_logger("handler").info("First request")

    # Clear context (simulates end of request)
    clear_context_fields()

    # Second request
    bind_context_vars(correlation_id="req-2")  # Note: no user_id
    get_logger("handler").info("Second request")

    first_log = parse_log_json(caplog, 0)
    second_log = parse_log_json(caplog, 1)

    assert first_log["extra"]["correlation_id"] == "req-1"
    assert first_log["extra"]["user_id"] == "user-1"

    assert second_log["extra"]["correlation_id"] == "req-2"
    assert "user_id" not in second_log.get("extra", {})


# ============================================================================
# Output Format Tests
# ============================================================================


def test__custom_fields__go_to_extra_section(caplog: LogCaptureFixture):
    get_logger("api").info("API call", user_id="user-123", endpoint="/api/chat", status_code=200)

    log_data = parse_log_json(caplog)

    # Standard fields at root
    assert_json_log_structure(log_data)

    # Custom fields in extra
    extra = log_data["extra"]
    assert extra["user_id"] == "user-123"
    assert extra["endpoint"] == "/api/chat"
    assert extra["status_code"] == 200

    # Standard fields not in extra
    standard_fields = {"timestamp", "level", "message", "logger", "context"}
    assert not (standard_fields & extra.keys())


@pytest.mark.parametrize(
    "testing,should_be_json",
    [
        (False, True),  # Production mode = JSON
        (True, False),  # Testing mode = Human readable
    ],
)
def test__output_format__changes_based_on_testing_flag(caplog: LogCaptureFixture, testing: bool, should_be_json: bool):
    configure_structlog(testing=testing)
    bind_context_vars(correlation_id="format-test")

    get_logger("format").info("Format test", field="value")

    log_message = caplog.records[0].message

    if should_be_json:
        log_data = parse_log_json(caplog)
        assert_json_log_structure(log_data)
        assert log_data["extra"]["correlation_id"] == "format-test"
    else:
        assert_human_readable_format(log_message)
        assert "Format test" in log_message
        assert "field=value" in log_message
        assert "[id:format-t]" in log_message  # Truncated correlation ID


# Human-Readable Formatter Tests


def test__human_readable_formatter__formats_complete_log(caplog: LogCaptureFixture):
    configure_structlog(testing=True)
    bind_context_vars(correlation_id="complete-test-789")

    get_logger("services.llm").warning("LLM call completed", duration_ms=2500, model="gpt-4o-mini")

    output = caplog.records[0].message

    # Verify format components
    assert "[WARNING]" in output
    assert "services.llm:" in output
    assert "LLM call completed" in output
    assert "duration_ms=2500" in output
    assert "model=gpt-4o-mini" in output
    assert "[id:complete]" in output  # Truncated to 8 chars

    # Verify timestamp format (HH:MM:SS at start)
    import re

    assert re.match(r"^\d{2}:\d{2}:\d{2}", output)


# ============================================================================
# Configuration Tests
# ============================================================================


def test__log_level__filters_messages(monkeypatch: MonkeyPatch, caplog: LogCaptureFixture):
    monkeypatch.setenv("LOGGING_LEVEL", "WARNING")
    configure_structlog()

    logger = get_logger("test")
    logger.debug("Should not appear")
    logger.info("Should not appear")
    logger.warning("Should appear")
    logger.error("Should appear")

    messages = [parse_log_json(caplog, i)["message"] for i in range(len(caplog.records))]

    assert "Should not appear" not in " ".join(messages)
    assert "Should appear" in " ".join(messages)
    assert len(caplog.records) == 2  # Only WARNING and ERROR


def test__invalid_log_level__defaults_to_info(monkeypatch: MonkeyPatch, caplog: LogCaptureFixture):
    monkeypatch.setenv("LOGGING_LEVEL", "INVALID")
    configure_structlog()

    logger = get_logger("test")
    logger.debug("Debug message")
    logger.info("Info message")

    # Should default to INFO level, so debug filtered out
    assert len(caplog.records) == 1
    log_data = parse_log_json(caplog)
    assert log_data["message"] == "Info message"


# ============================================================================
# Edge Cases & Integration Tests
# ============================================================================


def test__edge_case_values__are_handled_correctly(caplog: LogCaptureFixture):
    """Test that various edge case values (long, empty, special chars) are handled properly."""
    configure_structlog(testing=True)

    # Test long values get truncated in human-readable format
    very_long_value = "x" * 100
    get_logger("test").info("Long value test", long_field=very_long_value)
    human_output = caplog.records[0].message
    assert "long_field=" in human_output
    assert "..." in human_output
    assert very_long_value not in human_output

    caplog.clear()
    configure_structlog(testing=False)  # Switch to JSON format

    # Test empty, None, zero, false values are preserved in JSON
    get_logger("test").info("Edge case test", empty_string="", none_value=None, zero_value=0, false_value=False)

    log_data = parse_log_json(caplog)
    extra = log_data["extra"]
    assert extra["empty_string"] == ""
    assert extra["none_value"] is None
    assert extra["zero_value"] == 0
    assert extra["false_value"] is False

    caplog.clear()

    # Test special characters are preserved
    special_chars = 'Test with "quotes", commas, and [brackets]'
    get_logger("test").info("Special chars", special_field=special_chars)

    log_data = parse_log_json(caplog)
    assert log_data["extra"]["special_field"] == special_chars


def test__end_to_end_logging_workflow__maintains_context_and_formats_correctly(caplog: LogCaptureFixture):
    """Test complete logging workflow: set context, log across services, verify output."""
    configure_structlog(testing=False)  # JSON format for structured validation

    # Simulate request start - set context
    bind_context_vars(correlation_id="req-123", user_id="user-456", request_path="/api/users")

    # Simulate logging across different services in a request
    auth_logger = get_logger("src.auth.service")
    auth_logger.info("User authentication started", method="jwt")

    db_logger = get_logger("src.database.users")
    db_logger.info("Database query executed", table="users", query_time_ms=45)

    api_logger = get_logger("src.api.response")
    api_logger.warning("Rate limit approaching", current_requests=950, limit=1000)

    # Verify all logs have correct context and structure
    assert len(caplog.records) == 3

    for i, (service, expected_message) in enumerate(
        [
            ("auth.service", "User authentication started"),
            ("database.users", "Database query executed"),
            ("api.response", "Rate limit approaching"),
        ]
    ):
        log_data = parse_log_json(caplog, i)

        # Verify required structure
        assert log_data["message"] == expected_message
        assert log_data["level"] in ["info", "warning"]
        assert log_data["context"] == "default"
        assert service in log_data["logger"]

        # Verify context propagation
        extra = log_data["extra"]
        assert extra["correlation_id"] == "req-123"
        assert extra["user_id"] == "user-456"
        assert extra["request_path"] == "/api/users"

    # Verify service-specific fields are preserved
    auth_log = parse_log_json(caplog, 0)
    assert auth_log["extra"]["method"] == "jwt"

    db_log = parse_log_json(caplog, 1)
    assert db_log["extra"]["table"] == "users"
    assert db_log["extra"]["query_time_ms"] == 45

    rate_log = parse_log_json(caplog, 2)
    assert rate_log["extra"]["current_requests"] == 950
    assert rate_log["extra"]["limit"] == 1000


def test__concurrent_requests__maintain_isolated_contexts(caplog: LogCaptureFixture):
    """Test that context isolation works correctly when simulating concurrent requests."""
    configure_structlog(testing=False)

    # Simulate first request context
    bind_context_vars(correlation_id="req-001", session_id="sess-abc", feature="checkout")
    get_logger("src.checkout").info("Checkout process started")

    # Simulate second request context (different context)
    clear_context_fields()  # Simulate end of first request
    bind_context_vars(correlation_id="req-002", session_id="sess-xyz", feature="search")
    get_logger("src.search").info("Search query processed")

    # Simulate third request context
    clear_context_fields()
    bind_context_vars(correlation_id="req-003", user_type="premium", feature="analytics")
    get_logger("src.analytics").info("Analytics event recorded")

    # Verify each log has only its own context
    assert len(caplog.records) == 3

    # First request log
    checkout_log = parse_log_json(caplog, 0)
    checkout_extra = checkout_log["extra"]
    assert checkout_extra["correlation_id"] == "req-001"
    assert checkout_extra["session_id"] == "sess-abc"
    assert checkout_extra["feature"] == "checkout"
    assert "user_type" not in checkout_extra  # Should not leak from later request

    # Second request log
    search_log = parse_log_json(caplog, 1)
    search_extra = search_log["extra"]
    assert search_extra["correlation_id"] == "req-002"
    assert search_extra["session_id"] == "sess-xyz"
    assert search_extra["feature"] == "search"
    assert "user_type" not in search_extra  # Should not leak from later request

    # Third request log
    analytics_log = parse_log_json(caplog, 2)
    analytics_extra = analytics_log["extra"]
    assert analytics_extra["correlation_id"] == "req-003"
    assert analytics_extra["user_type"] == "premium"
    assert analytics_extra["feature"] == "analytics"
    assert "session_id" not in analytics_extra  # Should not leak from previous requests
