"""SSE event models for research workflow streaming."""

import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SSEEventType(str, Enum):
    """SSE event types for research workflow."""

    PHASE_START = "phase_start"
    PHASE_COMPLETE = "phase_complete"
    GATHERING_PROGRESS = "gathering_progress"
    HEARTBEAT = "heartbeat"
    COMPLETE = "complete"
    ERROR = "error"
    PHASE_WARNING = "phase_warning"


class SSEEvent(BaseModel):
    """Base SSE event model."""

    event: SSEEventType = Field(description="Event type identifier")
    data: dict[str, Any] = Field(description="Event payload data")

    def format(self) -> str:
        """Format as SSE message: 'event: type\\ndata: json\\n\\n'."""
        return f"event: {self.event.value}\ndata: {json.dumps(self.data)}\n\n"


class PhaseStartEvent(SSEEvent):
    """Event emitted when a workflow phase begins."""

    event: SSEEventType = SSEEventType.PHASE_START
    data: dict[str, str] = Field(
        description="Phase identifier",
        examples=[{"phase": "planning"}],
    )


class PhaseCompleteEvent(SSEEvent):
    """Event emitted when a workflow phase completes."""

    event: SSEEventType = SSEEventType.PHASE_COMPLETE
    data: dict[str, Any] = Field(
        description="Phase completion details with duration and summary",
        examples=[
            {
                "phase": "planning",
                "duration_ms": 3500,
                "output_summary": {
                    "executive_summary": "Research quantum computing by exploring...",
                    "search_steps": 3,
                },
            }
        ],
    )


class GatheringProgressEvent(SSEEvent):
    """Event emitted during gathering phase to show progress."""

    event: SSEEventType = SSEEventType.GATHERING_PROGRESS
    data: dict[str, Any] = Field(
        description="Search progress details",
        examples=[
            {
                "completed": 2,
                "total": 5,
                "current_query": "quantum computing breakthroughs 2024",
            }
        ],
    )


class HeartbeatEvent(SSEEvent):
    """Heartbeat event to prevent proxy buffering.

    Formatted as SSE comment (': keepalive\\n\\n') instead of
    named event to avoid requiring client-side handling.
    """

    event: SSEEventType = SSEEventType.HEARTBEAT
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Empty data for heartbeat",
    )

    def format(self) -> str:
        """Format as SSE comment for compatibility."""
        return ": keepalive\n\n"


class CompleteEvent(SSEEvent):
    """Event emitted when research workflow completes successfully."""

    event: SSEEventType = SSEEventType.COMPLETE
    data: dict[str, Any] = Field(
        description="Full ResearchResult serialized",
        examples=[
            {
                "query": "What is quantum computing?",
                "plan": {"executive_summary": "...", "web_search_steps": []},
                "search_results": [],
                "report": {"title": "...", "summary": "...", "key_findings": []},
                "validation": {"is_valid": True, "confidence_score": 0.85},
                "timings": {"planning_ms": 3500, "gathering_ms": 12000, "total_ms": 26000},
            }
        ],
    )


class ErrorEvent(SSEEvent):
    """Event emitted when an error occurs during workflow execution."""

    event: SSEEventType = SSEEventType.ERROR
    data: dict[str, str] = Field(
        description="Error details with phase context",
        examples=[
            {
                "error": "Unable to create research plan",
                "phase": "planning",
                "error_type": "PlanningError",
            }
        ],
    )


class PhaseWarningEvent(SSEEvent):
    """Event emitted when a non-fatal issue occurs during a phase."""

    event: SSEEventType = SSEEventType.PHASE_WARNING
    data: dict[str, str] = Field(
        description="Warning details",
        examples=[
            {
                "phase": "gathering",
                "warning": "2 of 5 searches failed, continuing with partial results",
            }
        ],
    )
