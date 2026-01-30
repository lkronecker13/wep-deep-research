# Plan: Streaming SSE Endpoint for Research API

## Scope

Add a `POST /research/stream` SSE endpoint that streams phase-level progress events as each workflow phase completes. The existing `POST /research` endpoint remains unchanged.

## Current State

- `POST /research` blocks until all 4 phases finish (~30-180s), then returns full `ResearchResult` JSON
- `src/workflow.py` has `run_research_workflow()` — 4-phase async pipeline
- `sse-starlette` v3.2.0 and `httpx-sse` v0.4.3 are installed but **not declared** in `pyproject.toml`

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| HTTP method | `POST /research/stream` | Query can be up to 1000 chars; reuses `ResearchRequest` body |
| Streaming protocol | SSE via `sse-starlette` | Already installed; `EventSourceResponse` handles dict→SSE encoding |
| Event granularity | Phase-level + heartbeats | start/complete per phase + 30s heartbeats + gathering progress |
| Architecture | New `stream_research_workflow()` in `workflow.py` + shielded cleanup wrapper in `server.py` | Generator yields `dict[str, Any]`; cleanup guaranteed via `anyio.CancelScope(shield=True)` |
| Error handling | Yield `error` event then `return` | Errors are in-band SSE events with structured metadata |
| Cleanup on disconnect | Pattern C: Shielded `gen.aclose()` at endpoint level | Guarantees background task cancellation, prevents API token waste |
| Type hints | `AsyncIterator[dict[str, Any]]` (Python 3.12+) | Yield-only generator; `collections.abc` preferred over `typing` |
| Testing | `httpx-sse` `aconnect_sse` with `ASGITransport` | Works with FastAPI; includes disconnect tests |
| GCP Cloud Run config | 600s timeout, 30s heartbeats, `X-Accel-Buffering: no` | Max workflow 180s with 3.3x buffer; prevents proxy buffering |

## SSE Event Protocol

### Event Types

| Event Type | When Emitted | Data Schema |
|------------|--------------|-------------|
| `phase_start` | Before each phase begins | `PhaseStartEvent` |
| `phase_complete` | After each phase finishes | `PhaseCompleteEvent` |
| `phase_warning` | After gathering if some searches failed | `PhaseWarningEvent` |
| `gathering_progress` | During gathering phase per search | `GatheringProgressEvent` |
| `heartbeat` | Every 30s during long operations | `HeartbeatEvent` |
| `complete` | After all 4 phases succeed | `StreamCompleteEvent` |
| `error` | On unrecoverable failure | `StreamErrorEvent` |

### Happy Path Flow

**Base case** (all searches succeed): **9 events** minimum
- 4 `phase_start` + 4 `phase_complete` + 1 `complete`

**With gathering progress** (5 searches): **14 events**
- 4 `phase_start` + 5 `gathering_progress` + 4 `phase_complete` + 1 `complete`

**With heartbeats** (120s workflow): **~18 events**
- 4 `phase_start` + 5 `gathering_progress` + 4 `heartbeat` + 4 `phase_complete` + 1 `complete`

### Error Path Flow

Yields events up to failure, then `error` event, then stream closes.

**Example** (gathering fails completely):
```
event: phase_start
data: {"phase":"planning","message":"Creating research plan..."}

event: phase_complete
data: {"phase":"planning","duration_ms":1234,"output":{...}}

event: phase_start
data: {"phase":"gathering","message":"Searching for information..."}

event: gathering_progress
data: {"completed":0,"total":5,"current_query":"quantum computing basics"}

event: error
data: {"phase":"gathering","error_type":"GatheringError","message":"Unable to gather sufficient information. Please try again.","retryable":true,"correlation_id":"a1b2c3d4"}
```

### Sample Event Payloads

```json
// phase_start
{"phase":"planning","message":"Creating research plan..."}

// phase_complete
{"phase":"planning","duration_ms":1234,"output":{"executive_summary":"...","web_search_steps":[...]}}

// gathering_progress
{"completed":2,"total":5,"current_query":"quantum computing applications"}

// phase_warning (partial gathering failure)
{"phase":"gathering","warnings":["2 out of 5 searches failed"],"proceeded_with":3}

// heartbeat
{"timestamp":"2026-01-28T12:34:56Z"}

// complete
{"query":"What is quantum computing?","timings":{"planning_ms":1200,"gathering_ms":5600,"synthesis_ms":3200,"verification_ms":800,"total_ms":10800}}

// error
{"phase":"synthesis","error_type":"SynthesisError","message":"Unable to generate research report. Please try again.","retryable":true,"correlation_id":"a1b2c3d4"}
```

---

## Files to Modify/Create (9 steps)

### 1. `pyproject.toml` — Add dependencies

Add to `dependencies`:
```toml
"sse-starlette>=3.2.0",
```

Add to `dev` optional-dependencies:
```toml
"httpx-sse>=0.4.0",
```

Then run `just sync`.

### 2. `src/exceptions.py` — Extract error messages

Move `_SAFE_ERROR_MESSAGES` from `src/server.py` to shared location:

```python
# src/exceptions.py (ADD at bottom)
SAFE_ERROR_MESSAGES: dict[str, str] = {
    "PlanningError": "Unable to create research plan. Please try a different query.",
    "GatheringError": "Unable to gather sufficient information. Please try again.",
    "SynthesisError": "Unable to generate research report. Please try again.",
    "VerificationError": "Unable to verify research quality. Please try again.",
}
```

Then update imports in `src/server.py`:
```python
from src.exceptions import SAFE_ERROR_MESSAGES  # Remove local definition
```

### 3. `src/models.py` — Add SSE event models

Add at the bottom (after `ResearchResult`):

```python
from enum import StrEnum
from typing import Any

class ResearchPhase(StrEnum):
    """Research workflow phases (Python 3.11+ pattern)."""
    PLANNING = "planning"
    GATHERING = "gathering"
    SYNTHESIS = "synthesis"
    VERIFICATION = "verification"

class SSEBaseEvent(BaseModel):
    """Base class for all SSE events."""
    # Subclasses override with Literal type
    pass

class PhaseStartEvent(SSEBaseEvent):
    phase: ResearchPhase
    message: str

class PhaseCompleteEvent(SSEBaseEvent):
    phase: ResearchPhase
    duration_ms: int = Field(ge=0)
    output: dict[str, Any]  # Mixed types from different phases

class PhaseWarningEvent(SSEBaseEvent):
    phase: ResearchPhase
    warnings: list[str]
    proceeded_with: int = Field(ge=0)

class GatheringProgressEvent(SSEBaseEvent):
    completed: int = Field(ge=0)
    total: int = Field(ge=1)
    current_query: str = Field(max_length=100)

class HeartbeatEvent(SSEBaseEvent):
    timestamp: str  # ISO 8601 format

class StreamCompleteEvent(SSEBaseEvent):
    query: str
    timings: PhaseTimings

class StreamErrorEvent(SSEBaseEvent):
    phase: ResearchPhase | None = None  # May fail before phase starts
    error_type: str
    message: str
    retryable: bool = True
    correlation_id: str
```

Update imports at top:
```python
from enum import StrEnum  # Add
from typing import Any  # Add if not present
```

### 4. `src/workflow.py` — Add `stream_research_workflow()`

Add imports:
```python
from collections.abc import AsyncIterator  # Python 3.12+ pattern
from datetime import datetime, UTC
from src.exceptions import SAFE_ERROR_MESSAGES  # Shared error messages
```

New async generator function below `run_research_workflow()`. See full implementation in detailed plan sections above.

**Key implementation details:**
- Return type: `AsyncIterator[dict[str, Any]]` (not `AsyncGenerator`)
- Yields: `{"event": str, "data": str}` where `data` is JSON-encoded Pydantic model
- Cleanup: `finally` block cancels tasks; guaranteed to complete via shielded `aclose()` in endpoint
- Error messages: Uses `SAFE_ERROR_MESSAGES` from `src/exceptions.py`
- Heartbeats: 30s interval per GCP Cloud Run research
- Progress: `gathering_progress` event per search step

### 5. `src/server.py` — Add `POST /research/stream` endpoint

Add imports at top (module-level, not inside function):
```python
import anyio  # For shielded cleanup
from collections.abc import AsyncIterator
from uuid import uuid4
from sse_starlette.sse import EventSourceResponse
from src.workflow import stream_research_workflow
```

Remove local `_SAFE_ERROR_MESSAGES` definition and import from exceptions:
```python
from src.exceptions import SAFE_ERROR_MESSAGES  # Replace local dict
```

Add endpoint inside `get_app()` with shielded cleanup pattern (Pattern C).

**Rationale for Pattern C (Shielded Cleanup):**
- Gathering phase spawns 5+ parallel API calls to Claude/Gemini
- Each search costs $0.001-0.01 in API fees
- Client disconnect without cleanup wastes tokens on orphaned tasks
- `anyio.CancelScope(shield=True)` guarantees `gen.aclose()` completes
- Generator's `finally` block can safely `await` task cancellation

### 6. `src/__init__.py` — Export new symbols

Add new imports and update `__all__` with SSE event models and streaming workflow function.

### 7. `tests/test_workflow.py` — Add streaming tests (~9 tests)

New `TestStreamResearchWorkflow` class:
- 4 happy path tests (base events, outputs, timings, progress)
- 5 error case tests (planning, gathering full/partial, synthesis, verification)

### 8. `tests/test_server.py` — Add SSE endpoint tests (~6 tests)

New `TestResearchStreamEndpoint` class:
- 4 basic functionality tests (events, validation, headers)
- 2 error handling tests (error events, **critical disconnect cleanup test**)

### 9. Update `TestAppFactory` — Add stream route test

Add `test__get_app__has_stream_route` to existing `TestAppFactory` class.

---

## Implementation Order

```
1. pyproject.toml          (add sse-starlette, httpx-sse) → just sync
2. src/exceptions.py       (extract SAFE_ERROR_MESSAGES to shared location)
3. src/server.py           (update to import SAFE_ERROR_MESSAGES from exceptions)
4. src/models.py           (add ResearchPhase enum + 7 SSE event models)
5. src/workflow.py         (add stream_research_workflow with AsyncIterator type)
6. src/server.py           (add POST /research/stream with shielded cleanup)
7. src/__init__.py         (export new symbols)
8. tests/test_workflow.py  (add 9 streaming workflow tests)
9. tests/test_server.py    (add 6 SSE endpoint tests including disconnect test)
→ just validate-branch
```

## Verification

### Local Development

```bash
just sync                  # Install new dependencies
just validate-branch       # format + lint + type-check + test (80%+ coverage)

# Manual smoke test (requires API keys):
just serve
curl -N -X POST http://localhost:8000/research/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "What is quantum computing?"}'
```

**Expected output:**
- SSE events stream progressively as each phase completes
- `event: phase_start`, `event: phase_complete`, `event: gathering_progress`, `event: complete`
- Total duration: 30-180s depending on query complexity
- Response headers include `X-Correlation-ID` and `X-Accel-Buffering: no`

### GCP Cloud Run Deployment (Phase 3)

**Service configuration:**
```yaml
timeout: 600s  # 10 minutes (3.3x buffer over 180s max workflow)
minInstances: 0
maxInstances: 100
```

**Deploy command:**
```bash
gcloud run deploy research-service \
  --source . \
  --timeout=600 \
  --max-instances=100 \
  --allow-unauthenticated
```

### Production Checklist

- [ ] `sse-starlette>=3.2.0` in `pyproject.toml` dependencies
- [ ] `httpx-sse>=0.4.0` in dev dependencies for tests
- [ ] All 9 workflow tests pass
- [ ] All 6 SSE endpoint tests pass (including disconnect test)
- [ ] mypy strict passes (no type: ignore)
- [ ] Test coverage ≥80%
- [ ] Cloud Run timeout set to 600s
- [ ] `X-Accel-Buffering: no` header present in response
- [ ] Correlation ID logged and returned in headers
- [ ] Background task cleanup verified in tests

### Known Limitations

1. **No reconnection support**: If client disconnects, workflow aborts. Client must retry from scratch.
2. **POST with SSE**: Browser `EventSource` API doesn't support POST. Use `fetch()` with `ReadableStream` or `httpx`.
3. **Single-instance only**: Event stream doesn't work across multiple Cloud Run instances. Use session affinity or Redis Pub/Sub for multi-instance.
4. **Token streaming deferred**: Phase-level events only. LLM token streaming requires PydanticAI `Agent.run_stream()` integration (future work).

### Research Documentation

Additional context created during planning:
- `docs/research/gcp-cloud-run-sse-limits.md` — GCP deployment guide with timeout configuration, heartbeat recommendations, and production best practices
- Agent review findings on cleanup patterns and Python best practices (available in conversation history)

---

## Key Technical Decisions (From Expert Review)

### Async Generator Cleanup (Pattern C)

**Problem:** When clients disconnect from SSE streams, orphaned background tasks continue consuming API tokens.

**Solution:** Shielded cleanup pattern guarantees task cancellation:
1. Generator yields SSE events during workflow execution
2. Generator's `finally` block cancels background tasks on disconnect
3. Endpoint wraps generator with `anyio.CancelScope(shield=True)` around `gen.aclose()`
4. Shield ensures `finally` block completes even if already cancelled

**Source:** Verified in `sse-starlette` source code - `EventSourceResponse` cancels generators on disconnect but doesn't call `aclose()` automatically.

### GCP Cloud Run Timeouts

**Finding:** Request timeout is **total connection time**, not idle time. Heartbeats don't reset the timer.

**Configuration:**
- Set timeout to 600s (10 min) for 180s max workflows
- Emit heartbeats every 30s (prevents proxy buffering)
- Add `X-Accel-Buffering: no` header

**Source:** GCP Cloud Run documentation + production case studies

### Python Type Hints

**Decision:** Use `AsyncIterator[dict[str, Any]]` instead of `AsyncGenerator[dict[str, str], None]`

**Rationale:**
- `AsyncIterator` is correct for yield-only generators (Python 3.12+ convention)
- `dict[str, Any]` matches actual yielded structure (event + JSON data)
- Import from `collections.abc` (preferred over `typing` in modern Python)

**Source:** Python 3.12+ best practices + mypy strict compatibility
