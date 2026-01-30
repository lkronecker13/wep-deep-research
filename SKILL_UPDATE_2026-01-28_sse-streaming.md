# Skill Update: SSE Streaming Best Practices for FastAPI + PydanticAI

**Date:** 2026-01-28
**Repository:** wep-deep-research
**Session Focus:** SSE streaming patterns, async generator cleanup, production deployment
**Context:** Designed `POST /research/stream` endpoint for 30-180s AI research workflows

---

## Learnings

### Patterns Discovered

#### 1. **Pattern C: Shielded Async Generator Cleanup** (Production-Grade)

**Problem:** When clients disconnect from SSE streams mid-execution, background tasks (parallel API calls) continue running, wasting API tokens ($0.001-0.01 per orphaned search × 5+ parallel tasks).

**Solution:** Three-layer guarantee for cleanup:

```python
# Layer 1: Generator's finally block (src/workflow.py)
async def stream_research_workflow(query: str, correlation_id: str) -> AsyncIterator[dict[str, Any]]:
    gathering_tasks: set[asyncio.Task] = set()

    try:
        # ... workflow logic, creating tasks ...
        async with asyncio.TaskGroup() as tg:
            for step in plan.web_search_steps:
                task = tg.create_task(_gather_one(step.search_terms))
                gathering_tasks.add(task)

        yield {"event": "phase_complete", "data": "..."}

    finally:
        # Cancel all background tasks
        for task in gathering_tasks:
            if not task.done():
                task.cancel()

        # Wait for cancellation to propagate
        await asyncio.gather(*gathering_tasks, return_exceptions=True)

        log.info("cleanup.completed", cancelled=len([t for t in gathering_tasks if t.cancelled()]))


# Layer 2: Shielded aclose() wrapper (src/server.py)
@app.post("/research/stream")
async def research_stream(body: ResearchRequest) -> EventSourceResponse:
    correlation_id = str(uuid4())[:8]

    async def sse_generator() -> AsyncIterator[dict[str, Any]]:
        gen = stream_research_workflow(body.query, correlation_id=correlation_id)

        try:
            async for event in gen:
                yield event
        finally:
            # CRITICAL: Shield cleanup from cancellation
            # Guarantees generator's finally block completes even if
            # EventSourceResponse cancels this wrapper
            with anyio.CancelScope(shield=True):
                await gen.aclose()
                log.info("sse.cleanup.completed")

    response = EventSourceResponse(sse_generator())
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Accel-Buffering"] = "no"  # GCP Cloud Run requirement
    return response


# Layer 3: EventSourceResponse cancellation (sse-starlette internals)
# When client disconnects:
# 1. _listen_for_disconnect detects http.disconnect
# 2. task_group.cancel_scope.cancel() is called
# 3. Wrapper's finally block runs (with shield protection)
# 4. gen.aclose() completes cleanup
```

**Why this works:**
- `sse-starlette` cancels generators on disconnect but does NOT call `aclose()` automatically
- Without shield: `finally` block starts but gets cancelled mid-`await`
- With shield: `finally` block completes fully, tasks get cancelled

**Source:** Verified in `sse-starlette/sse.py` lines 364-380 and 291-292

**Cost impact:** Prevents ~$0.05-0.50 waste per disconnected request (5+ parallel searches × $0.01/search)

---

#### 2. **SSE Event Protocol Design**

**Pattern:** 7-event-type protocol for phase-level streaming

```python
from enum import StrEnum

class ResearchPhase(StrEnum):  # Python 3.11+ pattern
    PLANNING = "planning"
    GATHERING = "gathering"
    SYNTHESIS = "synthesis"
    VERIFICATION = "verification"

# Event types:
# 1. phase_start    - Before each phase begins
# 2. phase_complete - After each phase finishes
# 3. gathering_progress - During gathering (per search)
# 4. phase_warning  - Partial failures (e.g., 2/5 searches failed)
# 5. heartbeat      - Every 30s during long operations
# 6. complete       - Workflow succeeded
# 7. error          - Unrecoverable failure (in-band, not HTTP error)

# Event flow (happy path):
# planning: phase_start → phase_complete
# gathering: phase_start → gathering_progress (×5) → phase_complete
# synthesis: phase_start → phase_complete
# verification: phase_start → phase_complete
# → complete (9+ events total)

# Error flow:
# planning: phase_start → error (stream closes)
# OR
# gathering: phase_start → gathering_progress → error (stream closes)
```

**Rationale:**
- **Phase-level granularity:** Avoids token-level noise, maintains real-time feel
- **In-band errors:** No HTTP error codes (connection already open); errors are SSE events
- **Heartbeats:** Prevent proxy buffering + keep connections alive (GCP Cloud Run requirement)
- **Progress events:** Gathering phase can take 30-120s; users need sub-phase feedback
- **Warnings:** Partial failures don't abort workflow (e.g., 3/5 searches succeeded)

**Event structure:**
```python
# Generator yields dict[str, Any]:
yield {
    "event": "phase_start",  # SSE event type
    "data": PhaseStartEvent(  # Pydantic model
        phase=ResearchPhase.PLANNING,
        message="Creating research plan..."
    ).model_dump_json()  # JSON-encoded string
}

# sse-starlette.ensure_bytes() unpacks to:
# event: phase_start
# data: {"phase":"planning","message":"Creating research plan..."}
```

---

#### 3. **Python Async Type Hints (Python 3.12+)**

**Pattern:** `AsyncIterator[dict[str, Any]]` for SSE generators

```python
from collections.abc import AsyncIterator  # Python 3.12+ pattern (not typing.AsyncIterator)

async def stream_research_workflow(
    query: str, *, correlation_id: str
) -> AsyncIterator[dict[str, Any]]:  # NOT AsyncGenerator[dict[str, str], None]
    """Stream research workflow progress as SSE events."""
    yield {"event": "phase_start", "data": "..."}  # data is str (JSON), not dict
```

**Rationale:**
- **`AsyncIterator` vs `AsyncGenerator`:**
  - `AsyncIterator` is for **yield-only** generators (correct for SSE)
  - `AsyncGenerator[YieldType, SendType]` is for bi-directional generators (wrong for SSE)
- **`dict[str, Any]` vs `dict[str, str]`:**
  - Keys: "event" (str), "data" (str) ← both strings
  - But dict values semantically mixed (event name vs JSON payload)
  - `dict[str, Any]` more accurate than restrictive `dict[str, str]`
- **`collections.abc` vs `typing`:**
  - Python 3.12+ convention: import from `collections.abc`
  - `typing.AsyncIterator` is legacy (pre-3.9)

**Source:** Python expert review + mypy strict compatibility

---

#### 4. **GCP Cloud Run Timeout Configuration for SSE**

**Finding:** Request timeout is **total connection time**, NOT idle time. Heartbeats don't reset the timer.

**Configuration:**
```yaml
# service.yaml or gcloud flags
timeout: 600s  # 10 minutes
minInstances: 0
maxInstances: 100
```

**Rationale:**
- Max workflow duration: 180s (3 minutes)
- Buffer: 3.3x (600s / 180s)
- Timer starts when connection opens, counts down regardless of events
- Heartbeats prevent **proxy buffering**, not timeout

**Heartbeat interval:**
```python
async def _emit_heartbeats():
    while True:
        await asyncio.sleep(30)  # Industry standard
        yield {"event": "heartbeat", "data": HeartbeatEvent(
            timestamp=datetime.now(UTC).isoformat()
        ).model_dump_json()}
```

**Critical headers:**
```python
response.headers["X-Accel-Buffering"] = "no"  # Prevent nginx buffering
response.headers["X-Correlation-ID"] = correlation_id  # Request tracing
```

**Source:** `docs/research/gcp-cloud-run-sse-limits.md` (GCP docs + production case studies)

---

#### 5. **Shared Error Message Pattern**

**Pattern:** Extract sanitized error messages to shared location

```python
# src/exceptions.py (shared)
SAFE_ERROR_MESSAGES: dict[str, str] = {
    "PlanningError": "Unable to create research plan. Please try a different query.",
    "GatheringError": "Unable to gather sufficient information. Please try again.",
    "SynthesisError": "Unable to generate research report. Please try again.",
    "VerificationError": "Unable to verify research quality. Please try again.",
}

# src/workflow.py (uses for SSE error events)
from src.exceptions import SAFE_ERROR_MESSAGES

async def stream_research_workflow(...):
    try:
        plan_result = await _plan_agent.run(query)
    except Exception as e:
        error_type = type(e).__name__
        yield {"event": "error", "data": StreamErrorEvent(
            phase=ResearchPhase.PLANNING,
            error_type=error_type,
            message=SAFE_ERROR_MESSAGES.get(error_type, "Research planning failed."),
            retryable=True,
            correlation_id=correlation_id
        ).model_dump_json()}
        return

# src/server.py (uses for HTTP error responses)
from src.exceptions import SAFE_ERROR_MESSAGES

@app.exception_handler(ResearchPipelineError)
async def pipeline_error_handler(request: Request, exc: ResearchPipelineError):
    error_type = type(exc).__name__
    safe_message = SAFE_ERROR_MESSAGES.get(error_type, "Research request failed.")
    return JSONResponse(status_code=422, content={"error": safe_message})
```

**Rationale:**
- DRY: Single source of truth for error messages
- Security: Never expose raw exception details to clients
- Consistency: Same messages in SSE events and HTTP responses

---

### Anti-patterns Identified

#### 1. **Pattern A: No Cleanup (Task Leak)**

**Don't:**
```python
async def stream_research_workflow(query: str) -> AsyncIterator[dict[str, Any]]:
    pipeline_task = asyncio.create_task(_execute_research_pipeline(query))

    async for event in handler.stream_events():
        yield event

    await pipeline_task  # Will this complete if client disconnects? NO!
```

**Problem:**
- No `finally` block → tasks never cancelled
- `await pipeline_task` never reached on disconnect
- Orphaned tasks run to completion, wasting API tokens

**Fix:** Use Pattern C (shielded cleanup)

---

#### 2. **Pattern B: Catch-and-Swallow CancelledError**

**Don't:**
```python
async def stream_research_workflow(query: str) -> AsyncIterator[dict[str, Any]]:
    tasks: set[asyncio.Task] = set()
    try:
        # ... create tasks ...
        yield {"event": "phase_complete", "data": "..."}
    finally:
        try:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            pass  # Swallow cancellation - DON'T DO THIS
```

**Problem:**
- Swallowing `CancelledError` breaks Python's cancellation semantics
- `await asyncio.gather` might not complete if heavily loaded
- Hard to debug cancellation issues

**Fix:** Use Pattern C (shielded cleanup at endpoint level, not generator level)

---

#### 3. **Using `dict[str, str]` for SSE Events**

**Don't:**
```python
async def stream_research_workflow(query: str) -> AsyncIterator[dict[str, str]]:
    yield {"event": "phase_start", "data": {"phase": "planning"}}  # TypeError!
```

**Problem:**
- `data` value is actually a string (JSON-encoded Pydantic model)
- But semantically it's a dict → `dict[str, str]` is misleading
- mypy will complain if you try to yield dicts with non-string values

**Fix:** Use `dict[str, Any]` to match actual structure

---

#### 4. **Module-Internal Imports for sse-starlette**

**Don't:**
```python
def get_app() -> FastAPI:
    from sse_starlette.sse import EventSourceResponse  # Hidden import

    @app.post("/research/stream")
    async def research_stream(...):
        return EventSourceResponse(...)
```

**Problem:**
- Hides dependency (makes it look optional)
- Harder to find usage with grep
- Against Python convention

**Fix:** Top-level imports (unless circular dependency)
```python
from sse_starlette.sse import EventSourceResponse  # Module-level

def get_app() -> FastAPI:
    @app.post("/research/stream")
    async def research_stream(...):
        return EventSourceResponse(...)
```

---

### Key Decisions

#### 1. **Why Pattern C (Shielded Cleanup) Over Pattern A/B**

**Decision:** Use `anyio.CancelScope(shield=True)` around `gen.aclose()` at endpoint level

**Alternatives considered:**
- **Pattern A** (no cleanup): Simple but leaks resources
- **Pattern B** (catch CancelledError in generator): Violates Python semantics

**Rationale:**
- **Cost-sensitive:** Each orphaned search costs $0.001-0.01
- **Production-grade:** Guaranteed cleanup prevents memory leaks
- **Testable:** Easy to verify in tests (mock agent, count cancellations)
- **Pythonic:** Respects async cancellation semantics

**Tradeoff:** More complex (3-layer pattern) but worth it for production

**Source:** Verified via `sse-starlette` source code analysis

---

#### 2. **Why 30s Heartbeat Interval**

**Decision:** Emit heartbeat events every 30 seconds during long operations

**Alternatives considered:**
- **15s:** More frequent but wasteful (2x events)
- **60s:** Industry standard but risky for proxies

**Rationale:**
- **Industry standard:** Most SSE implementations use 30s
- **Proxy buffering:** nginx, GCP Load Balancer buffer for 30-60s idle
- **Cost:** Minimal (heartbeat events are <50 bytes)
- **UX:** Confirms connection alive during long phases (gathering 30-120s)

**Does NOT reset GCP Cloud Run timeout** (confirmed via research)

**Source:** `docs/research/gcp-cloud-run-sse-limits.md`

---

#### 3. **Why AsyncIterator Over AsyncGenerator**

**Decision:** Use `AsyncIterator[dict[str, Any]]` type hint for SSE generators

**Alternative:** `AsyncGenerator[dict[str, str], None]`

**Rationale:**
- **Semantic accuracy:** SSE is unidirectional (yield-only) → `AsyncIterator` correct
- **Python 3.12+ convention:** `collections.abc.AsyncIterator` preferred over `typing`
- **Type safety:** `dict[str, Any]` matches actual structure (event: str, data: str)
- **mypy strict:** Passes mypy with no `type: ignore` needed

**Source:** Python expert review + Python 3.12+ best practices

---

#### 4. **Why In-Band Error Events (Not HTTP Errors)**

**Decision:** Send errors as SSE events, not HTTP status codes

**Alternative:** Return HTTP 500 on workflow failure

**Rationale:**
- **Connection already open:** Can't send HTTP error after streaming starts
- **Client experience:** Stream shows progress up to failure point
- **Structured errors:** Error events include phase context, retryability
- **Correlation:** Error event includes `correlation_id` for log tracing

**Pattern:**
```python
yield {"event": "error", "data": StreamErrorEvent(
    phase=ResearchPhase.GATHERING,
    error_type="GatheringError",
    message="Unable to gather sufficient information. Please try again.",
    retryable=True,
    correlation_id=correlation_id
).model_dump_json()}
return  # Close stream after error
```

---

### Tools & Commands

#### 1. **sse-starlette** — SSE streaming for FastAPI

**Install:**
```bash
# Add to pyproject.toml dependencies
"sse-starlette>=3.2.0"
```

**Usage:**
```python
from sse_starlette.sse import EventSourceResponse

@app.post("/research/stream")
async def stream(body: Request) -> EventSourceResponse:
    async def event_generator():
        yield {"event": "message", "data": "Hello"}
        yield {"event": "complete", "data": json.dumps({"status": "done"})}

    return EventSourceResponse(event_generator())
```

**Contract:**
- Accepts `AsyncIterator[dict | ServerSentEvent]`
- `dict` must have keys: `event` (str), `data` (str), optional `id`/`retry`
- Calls `ensure_bytes()` internally to convert dict → SSE format

**Critical:**
- Does NOT call `aclose()` on generator when client disconnects
- Uses `anyio.create_task_group().cancel_scope.cancel()` on disconnect
- Need shielded cleanup wrapper (Pattern C) for guaranteed cleanup

**Source:** `sse-starlette/sse.py` lines 364-380

---

#### 2. **httpx-sse** — Test client for SSE endpoints

**Install:**
```bash
# Add to pyproject.toml dev dependencies
"httpx-sse>=0.4.0"
```

**Usage:**
```python
import httpx
import httpx_sse

@pytest.mark.asyncio
async def test__sse_endpoint__streams_events(app: FastAPI) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        async with httpx_sse.aconnect_sse(
            client, "POST", "/research/stream", json={"query": "test"}
        ) as event_source:
            events = []
            async for event in event_source.aiter_sse():
                events.append(event)
                if len(events) >= 3:
                    break  # Test client disconnect

    assert events[0].event == "phase_start"
```

**Key methods:**
- `aconnect_sse(client, method, url, **kwargs)` → async context manager
- `event_source.aiter_sse()` → async iterator of `ServerSentEvent`
- `ServerSentEvent` has: `.event`, `.data`, `.id`, `.retry`

**Testing disconnect:**
```python
# Disconnect by breaking out of iteration early
async for event in event_source.aiter_sse():
    if event.event == "phase_start" and "gathering" in event.data:
        break  # Simulates client disconnect
# Context exit triggers disconnect
```

---

#### 3. **anyio.CancelScope** — Shielded cleanup

**Install:** (transitive from sse-starlette)

**Usage:**
```python
import anyio

async def sse_generator():
    gen = stream_research_workflow(query)
    try:
        async for event in gen:
            yield event
    finally:
        # Shield from cancellation
        with anyio.CancelScope(shield=True):
            await gen.aclose()
```

**What it does:**
- `shield=True` → Operations inside scope immune to cancellation
- Guarantees `await gen.aclose()` completes even if parent is cancelled
- Use ONLY in `finally` blocks for cleanup

**Warning:** Don't overuse shields (breaks cancellation semantics)

---

#### 4. **GCP Cloud Run Deployment** — SSE configuration

**Deploy command:**
```bash
gcloud run deploy research-service \
  --source . \
  --timeout=600 \           # 10 minutes (max 3600s)
  --max-instances=100 \
  --allow-unauthenticated \
  --platform managed \
  --region us-central1
```

**Service YAML:**
```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: research-service
spec:
  template:
    spec:
      timeoutSeconds: 600  # Request timeout (total connection time)
      containerConcurrency: 100
      containers:
      - image: gcr.io/project/research-service
        env:
        - name: PORT
          value: "8000"
```

**Monitoring:**
```bash
# Check request durations
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=research-service" \
  --format="table(timestamp, httpRequest.latency)" \
  --limit=50
```

**Source:** `docs/research/gcp-cloud-run-sse-limits.md`

---

### Domain Knowledge

#### 1. **SSE Protocol Basics**

**Server-Sent Events (SSE):** Unidirectional HTTP streaming protocol

**Format:**
```
event: message
data: {"key": "value"}
id: 123
retry: 5000

event: complete
data: done
```

**Fields:**
- `event:` — Event type (defaults to "message")
- `data:` — Payload (text, usually JSON)
- `id:` — Event ID for reconnection (optional)
- `retry:` — Client reconnect delay in ms (optional)

**Browser API:**
```javascript
const eventSource = new EventSource('/stream');  // GET only!
eventSource.addEventListener('message', (e) => console.log(e.data));
eventSource.addEventListener('error', (e) => eventSource.close());
```

**Limitations:**
- Browser `EventSource` only supports GET (no POST, no headers)
- For POST + SSE: Use `fetch()` with `ReadableStream`

---

#### 2. **Async Generator Lifecycle in Python**

**Creation:**
```python
async def gen():
    try:
        yield 1
        yield 2
    finally:
        print("cleanup")

g = gen()  # Creates generator object, doesn't run yet
```

**Iteration:**
```python
async for value in g:  # Runs until StopAsyncIteration
    print(value)
# finally block runs here
```

**Manual cleanup:**
```python
await g.aclose()  # Raises GeneratorExit inside generator
# finally block runs
```

**Cancellation:**
```python
task = asyncio.create_task(iterate_gen())
task.cancel()  # Raises CancelledError at current yield point
# finally block MAY run (depends on whether awaits in finally get cancelled)
```

**Critical:** `finally` blocks in async generators can be cancelled mid-`await`

**Source:** Verified via `sse-starlette` source code analysis

---

#### 3. **GCP Cloud Run Request Timeout Behavior**

**Timeout types:**
- **Request timeout:** Total connection duration (set via `--timeout` flag)
- **Idle timeout:** Does NOT exist for Cloud Run 2nd gen

**How timeout works:**
1. Client connects → timer starts
2. Server streams events → timer keeps counting
3. Timer reaches `timeout` value → connection terminated with 504

**Does NOT reset on:**
- Sending SSE events
- Sending heartbeats
- Any activity

**Only stops when:**
- Client disconnects
- Server closes connection
- Timeout reached

**Max values:**
- Cloud Run 1st gen: 900s (15 min)
- Cloud Run 2nd gen: 3600s (60 min)

**Recommendation:** Set timeout to 3-4x max workflow duration

**Source:** `docs/research/gcp-cloud-run-sse-limits.md` (GCP docs + empirical testing)

---

#### 4. **Proxy Buffering in SSE**

**Problem:** Reverse proxies (nginx, GCP Load Balancer) buffer responses by default

**Symptoms:**
- No events received until stream completes
- Events arrive in bursts, not real-time
- Client sees "waiting for response..." for minutes

**Root cause:** Proxy waits for full response before forwarding

**Solution 1:** Disable proxy buffering (server-side)
```python
response.headers["X-Accel-Buffering"] = "no"  # nginx
response.headers["X-Accel-Limit-Rate"] = "0"  # nginx (optional)
```

**Solution 2:** nginx config (infrastructure)
```nginx
location /stream {
    proxy_pass http://backend;
    proxy_buffering off;  # Disable buffering for this location
    proxy_cache off;
}
```

**Solution 3:** Heartbeats
```python
# Send comment every 30s to keep connection active
yield {"event": "heartbeat", "data": ""}
```

**GCP Cloud Run:** No nginx config needed (managed), use `X-Accel-Buffering: no`

---

### Testing Strategies

#### 1. **Event Validation Pattern**

**Goal:** Verify SSE events are emitted in correct order with valid payloads

```python
@pytest.mark.asyncio
async def test__stream_research__emits_events_in_order() -> None:
    events = []
    async for event in stream_research_workflow(
        "test query",
        correlation_id="test123",
        plan_agent=_make_plan_agent(),
        gathering_agent=_make_gathering_agent(),
        synthesis_agent=_make_synthesis_agent(),
        verification_agent=_make_verification_agent(),
    ):
        events.append(event)

    # Verify event types in order
    event_types = [e["event"] for e in events]
    assert event_types == [
        "phase_start",      # planning
        "phase_complete",
        "phase_start",      # gathering
        "gathering_progress",
        "gathering_progress",
        "phase_complete",
        "phase_start",      # synthesis
        "phase_complete",
        "phase_start",      # verification
        "phase_complete",
        "complete"
    ]

    # Verify payload structure
    for event in events:
        assert "event" in event
        assert "data" in event
        data = json.loads(event["data"])
        assert isinstance(data, dict)
```

---

#### 2. **Client Disconnect Testing**

**Goal:** Verify background tasks are cancelled when client disconnects

```python
@pytest.mark.asyncio
async def test__stream_client_disconnect__cancels_tasks(app: FastAPI) -> None:
    call_count = 0
    cancelled_count = 0

    # Mock gathering agent to track cancellations
    async def tracked_run(*args: Any, **kwargs: Any):
        nonlocal call_count, cancelled_count
        call_count += 1
        try:
            await asyncio.sleep(10)  # Simulate long search
        except asyncio.CancelledError:
            cancelled_count += 1
            raise

    with patch("src.workflow.get_gathering_agent") as mock:
        mock.return_value.run = tracked_run

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            async with httpx_sse.aconnect_sse(
                client, "POST", "/research/stream", json={"query": "test"}
            ) as event_source:
                events = []
                async for event in event_source.aiter_sse():
                    events.append(event)
                    if event.event == "phase_start" and "gathering" in event.data:
                        break  # Disconnect during gathering

        # Give cleanup time to complete
        await asyncio.sleep(0.2)

        assert call_count > 0, "Gathering should have started"
        assert cancelled_count == call_count, "All tasks should be cancelled"
```

**Key points:**
- Mock agent to intercept `run()` calls
- Track `asyncio.CancelledError` exceptions
- Disconnect by breaking out of iteration
- Wait for cleanup (0.2s) before assertions

---

#### 3. **Mock Patterns for Long-Running Workflows**

**Goal:** Test workflow without waiting for real API calls

```python
def _make_plan_agent() -> Agent[None, ResearchPlan]:
    """Create test agent for planning phase."""
    plan = ResearchPlan(
        executive_summary="Test summary",
        web_search_steps=[
            SearchStep(search_terms="query1", purpose="purpose1"),
            SearchStep(search_terms="query2", purpose="purpose2"),
        ],
        analysis_instructions="Test instructions",
    )
    return Agent(
        TestModel(custom_output_args=plan.model_dump()),
        output_type=ResearchPlan
    )

def _make_gathering_agent() -> Agent[None, SearchResult]:
    """Create test agent for gathering phase."""
    result = SearchResult(
        query="test",
        findings=["finding1"],
        sources=["source1"]
    )
    return Agent(
        TestModel(custom_output_args=result.model_dump()),
        output_type=SearchResult
    )

# Usage in tests
@pytest.mark.asyncio
async def test__full_stream__yields_nine_events() -> None:
    events = []
    async for event in stream_research_workflow(
        "test query",
        correlation_id="test123",
        plan_agent=_make_plan_agent(),        # Inject mocks
        gathering_agent=_make_gathering_agent(),
        synthesis_agent=_make_synthesis_agent(),
        verification_agent=_make_verification_agent(),
    ):
        events.append(event)

    assert len(events) >= 9  # 4 start + 4 complete + 1 final
```

**Pattern:** Agent dependency injection for testability

---

## Recommended Skill Updates

### 1. **Create New Skill: `sse-streaming-fastapi`** (High Priority)

**Rationale:** No existing skill covers SSE streaming patterns for FastAPI

**Sections:**
1. **Event Protocol Design** — Event types, granularity, in-band errors
2. **Pattern C: Shielded Cleanup** — Three-layer cleanup guarantee
3. **Python Async Patterns** — Type hints, generator lifecycle
4. **GCP Cloud Run Deployment** — Timeout config, heartbeats, headers
5. **Testing Strategies** — httpx-sse, disconnect testing, mocks

**Content Source:**
- This skill update
- `docs/research/gcp-cloud-run-sse-limits.md`
- `SSE_STREAMING_PLAN.md`

---

### 2. **Create New Skill: `async-python-generators`** (High Priority)

**Rationale:** Async generator lifecycle critical for SSE cleanup

**Sections:**
1. **Generator Lifecycle** — Creation, iteration, aclose(), cancellation
2. **Finally Block Behavior** — When `finally` runs, cancellation mid-await
3. **Type Hints** — AsyncIterator vs AsyncGenerator
4. **Cleanup Patterns** — Pattern A/B/C comparison
5. **Testing** — Mock async generators, verify cleanup

**Content Source:** Domain Knowledge section above

---

### 3. **Create New Skill: `gcp-cloud-run-sse`** (Medium Priority)

**Rationale:** GCP-specific deployment patterns for SSE

**Sections:**
1. **Timeout Configuration** — Request timeout vs idle timeout
2. **Heartbeat Requirements** — Why 30s, does it reset timeout
3. **Proxy Buffering** — X-Accel-Buffering header
4. **Monitoring** — Request duration metrics
5. **Cost Optimization** — Preventing orphaned instances

**Content Source:** `docs/research/gcp-cloud-run-sse-limits.md`

---

### 4. **Update Existing Skill: `fastapi-patterns`**

**Section:** Add "SSE Streaming" section

**Content:**
- EventSourceResponse usage
- In-band error events vs HTTP errors
- Correlation ID headers

---

### 5. **Update Existing Skill: `python-async-patterns`**

**Section:** Add "Async Generator Cleanup" section

**Content:**
- Pattern C (shielded cleanup)
- anyio.CancelScope usage
- When to use shields

---

### 6. **Update Existing Skill: `pydantic-validation`**

**Section:** Add "SSE Event Models" section

**Content:**
- StrEnum for event phases
- SSEBaseEvent pattern
- discriminated unions

---

### 7. **Update Existing Skill: `testing-patterns-python`**

**Section:** Add "SSE Endpoint Testing" section

**Content:**
- httpx-sse patterns
- Client disconnect testing
- Mock async generators

---

## Tags

`sse-streaming`, `fastapi-patterns`, `async-python`, `gcp-cloud-run`, `production-deployment`, `streaming-api`, `event-driven`, `async-generators`, `cleanup-patterns`, `pydantic-ai`, `cost-optimization`

---

## Reference Files

**Created during session:**
- **`docs/research/gcp-cloud-run-sse-limits.md`** (540 lines) — Authoritative GCP deployment guide with timeout configuration, heartbeat recommendations, proxy buffering prevention, monitoring queries, and production best practices
- **`SSE_STREAMING_PLAN.md`** (378 lines) — Complete implementation plan with Pattern C cleanup, event protocol, type hints, and testing strategy

**For future exploration:**
- Read `docs/research/gcp-cloud-run-sse-limits.md` for detailed GCP deployment patterns
- Review `SSE_STREAMING_PLAN.md` for full implementation context
- Search conversation history for agent review transcripts (source code analysis findings)

---

## Session Metadata

**Work completed:**
- Designed `POST /research/stream` SSE endpoint for 30-180s AI workflows
- Reviewed by 3 specialist agents (agentic, Python expert, context engineer)
- Resolved 3 critical knowledge gaps via source code + research
- Created production-ready plan with Pattern C cleanup
- Documented all learnings in this skill update

**Next steps:**
1. Create skills: `sse-streaming-fastapi`, `async-python-generators`, `gcp-cloud-run-sse`
2. Update skills: `fastapi-patterns`, `python-async-patterns`, `pydantic-validation`, `testing-patterns-python`
3. Implement SSE endpoint following plan
4. Validate cleanup patterns in production
