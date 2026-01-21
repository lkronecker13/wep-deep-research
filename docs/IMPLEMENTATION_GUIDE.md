# Deep Research Implementation Guide

Practical guide for implementing durable agent workflows based on durable-exec patterns.

## Quick Start

### 1. Install Dependencies

```bash
# Add to pyproject.toml dependencies
pydantic-ai>=0.0.15
httpx>=0.27.0
tavily-python>=0.5.0
logfire>=0.59.0

# For DBOS durability (optional, add when needed)
dbos>=1.0.0
asyncpg>=0.30.0

# Install
just sync
```

### 2. Environment Configuration

Create `.env` file:

```bash
# LLM API Keys
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_AI_API_KEY=...

# Search API
TAVILY_API_KEY=tvly-...

# Observability
LOGFIRE_TOKEN=...

# Database (for DBOS)
DATABASE_URL=postgresql://postgres:password@localhost:5432/deep_research
```

### 3. Basic Agent Example

Create `src/agents/example.py`:

```python
from pydantic_ai import Agent
from pydantic import BaseModel

class Question(BaseModel):
    """Research question with constraints."""
    query: str
    max_depth: int = 3
    max_sources: int = 10

class Answer(BaseModel):
    """Structured research answer."""
    summary: str
    key_findings: list[str]
    sources: list[str]

# Define agent
simple_research_agent = Agent(
    model='anthropic:claude-sonnet-4-5',
    system_prompt='''You are a research assistant.
    Provide clear, well-sourced answers to research questions.
    Always cite your sources.''',
    result_type=Answer
)

# Use agent
async def main():
    question = Question(
        query="What are the latest developments in quantum computing?",
        max_depth=3,
        max_sources=5
    )

    result = await simple_research_agent.run(question.query)
    print(result.data.summary)
    print(result.data.key_findings)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
```

Run with:
```bash
uv run python src/agents/example.py
```

## Core Patterns

### Pattern 1: Type-Safe Agent Outputs

Always use Pydantic models for structured outputs:

```python
from pydantic import BaseModel, Field
from datetime import datetime

class SearchStep(BaseModel):
    """Individual search task in research plan."""
    query: str = Field(description="Search query to execute")
    purpose: str = Field(description="Why this search is needed")
    expected_sources: list[str] = Field(
        default_factory=list,
        description="Expected source types (academic, news, technical)"
    )

class ResearchPlan(BaseModel):
    """Structured research strategy."""
    executive_summary: str = Field(
        description="2-3 sentence overview of research approach"
    )
    search_steps: list[SearchStep] = Field(
        min_length=1,
        max_length=5,
        description="Ordered list of search tasks"
    )
    estimated_duration_minutes: int = Field(
        ge=1,
        le=60,
        description="Estimated time to complete research"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Agent with structured output
plan_agent = Agent(
    model='anthropic:claude-sonnet-4-5',
    result_type=ResearchPlan,  # Enforces type safety
    system_prompt='You are a research planning expert...'
)

# Usage guarantees type safety
result = await plan_agent.run("Research quantum computing")
plan: ResearchPlan = result.data  # Fully typed
print(plan.search_steps[0].query)  # IDE autocomplete works
```

### Pattern 2: Tool Integration

#### Simple Tool

```python
from pydantic_ai import Agent
from pydantic_ai.tools import Tool
from typing import Annotated
import httpx

class WebSearchTool(Tool):
    """Web search using Tavily API."""

    name = "web_search"
    description = "Search the web for current information with citations"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def __call__(
        self,
        query: Annotated[str, "The search query"],
        max_results: Annotated[int, "Maximum number of results"] = 5
    ) -> str:
        """Execute search and return formatted results."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "query": query,
                        "max_results": max_results,
                        "include_answer": True,
                        "include_raw_content": False
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                # Format results
                results = []
                for item in data.get('results', []):
                    results.append(
                        f"Title: {item['title']}\n"
                        f"URL: {item['url']}\n"
                        f"Content: {item['content']}\n"
                    )

                return "\n---\n".join(results)

            except Exception as e:
                return f"Search error: {str(e)}"

# Use tool in agent
search_agent = Agent(
    model='google-gla:gemini-2.5-flash',
    tools=[WebSearchTool(api_key=os.getenv('TAVILY_API_KEY'))]
)
```

#### Agent-as-Tool Pattern

```python
from pydantic_ai import Agent, RunContext

# Primary agent
synthesis_agent = Agent(
    model='anthropic:claude-sonnet-4-5',
    deps_type=SearchAgent,  # Inject dependency
    result_type=ResearchReport
)

# Tool that invokes another agent
@synthesis_agent.tool
async def extra_search(
    ctx: RunContext[Agent],
    query: str
) -> str:
    """Perform additional search if initial results insufficient."""
    # Invoke dependency agent
    result = await ctx.deps.run(query)
    return result.data

# Usage
search_agent = Agent(model='google-gla:gemini-2.5-flash', tools=[WebSearchTool()])
result = await synthesis_agent.run(
    "Synthesize findings...",
    deps=search_agent  # Inject at runtime
)
```

### Pattern 3: Parallel Execution

Execute independent tasks concurrently:

```python
import asyncio
from typing import Any

async def parallel_research(plan: ResearchPlan) -> list[SearchResult]:
    """Execute multiple searches concurrently."""
    results: list[SearchResult] = []

    async def execute_search(step: SearchStep) -> SearchResult:
        """Execute single search task."""
        result = await search_agent.run(step.query)
        return SearchResult(
            query=step.query,
            content=result.data,
            timestamp=datetime.utcnow()
        )

    # Parallel execution with TaskGroup
    async with asyncio.TaskGroup() as tg:
        tasks = [
            tg.create_task(execute_search(step))
            for step in plan.search_steps
        ]

    # Gather results (automatically happens when TaskGroup exits)
    results = [task.result() for task in tasks]

    return results
```

**Performance Comparison**:
- Sequential: 5 searches × 3s = 15s total
- Parallel: max(3s, 3s, 3s, 3s, 3s) = 3s total

### Pattern 4: Event-Driven State Management

Track workflow progress with domain events:

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from enum import Enum

class EventType(str, Enum):
    """Domain event types."""
    RESEARCH_INITIATED = "research.initiated"
    PLAN_CREATED = "research.plan_created"
    SEARCH_COMPLETED = "research.search_completed"
    REPORT_GENERATED = "research.report_generated"
    RESEARCH_COMPLETED = "research.completed"
    RESEARCH_FAILED = "research.failed"

@dataclass
class DomainEvent:
    """Base class for all domain events."""
    event_type: EventType
    workflow_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class ResearchInitiated(DomainEvent):
    """Emitted when research workflow starts."""
    query: str
    constraints: dict[str, Any]

    def __post_init__(self):
        self.event_type = EventType.RESEARCH_INITIATED

@dataclass
class PlanCreated(DomainEvent):
    """Emitted when research plan is generated."""
    plan: ResearchPlan

    def __post_init__(self):
        self.event_type = EventType.PLAN_CREATED

# Workflow aggregate
class ResearchWorkflow:
    """Aggregate root collecting events during research execution."""

    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        self.events: list[DomainEvent] = []
        self._plan: ResearchPlan | None = None
        self._report: ResearchReport | None = None

    async def execute(self, query: str, constraints: dict[str, Any]) -> ResearchReport:
        """Execute research workflow with event tracking."""
        # Emit initiation event
        self.events.append(ResearchInitiated(
            workflow_id=self.workflow_id,
            query=query,
            constraints=constraints
        ))

        # Phase 1: Planning
        plan_result = await plan_agent.run(query)
        self._plan = plan_result.data
        self.events.append(PlanCreated(
            workflow_id=self.workflow_id,
            plan=self._plan
        ))

        # Phase 2: Gathering (with per-task events)
        search_results = []
        async with asyncio.TaskGroup() as tg:
            for step in self._plan.search_steps:
                task = tg.create_task(self._search_with_event(step))

        # Phase 3: Synthesis
        report_result = await synthesis_agent.run(self._plan, search_results)
        self._report = report_result.data
        self.events.append(ReportGenerated(
            workflow_id=self.workflow_id,
            report=self._report
        ))

        # Completion event
        self.events.append(ResearchCompleted(
            workflow_id=self.workflow_id,
            report=self._report
        ))

        return self._report

    async def _search_with_event(self, step: SearchStep) -> SearchResult:
        """Execute search and emit completion event."""
        result = await search_agent.run(step.query)
        search_result = SearchResult(
            query=step.query,
            content=result.data
        )

        self.events.append(SearchCompleted(
            workflow_id=self.workflow_id,
            search_step=step.query,
            result=search_result
        ))

        return search_result
```

**Event Benefits**:
- Progress tracking for UI updates
- Audit trail for debugging
- Event sourcing for workflow replay
- Integration points for other services

### Pattern 5: Dependency Injection

Pass context and dependencies to agents:

```python
from pydantic import BaseModel
from sqlalchemy.orm import Session
from pydantic_ai import Agent, RunContext

class ResearchDeps(BaseModel):
    """Dependencies injected into agents."""
    db_session: Session
    search_agent: Agent
    user_id: str
    max_cost_usd: float = 5.0

    class Config:
        arbitrary_types_allowed = True  # For SQLAlchemy Session

# Agent with dependencies
synthesis_agent = Agent(
    model='anthropic:claude-sonnet-4-5',
    deps_type=ResearchDeps,
    result_type=ResearchReport
)

@synthesis_agent.tool
async def save_finding(
    ctx: RunContext[ResearchDeps],
    finding: str
) -> str:
    """Save intermediate finding to database."""
    # Access injected dependencies
    db = ctx.deps.db_session
    user_id = ctx.deps.user_id

    # Save to DB
    record = Finding(
        content=finding,
        user_id=user_id,
        created_at=datetime.utcnow()
    )
    db.add(record)
    db.commit()

    return f"Saved finding {record.id}"

@synthesis_agent.tool
async def deep_search(
    ctx: RunContext[ResearchDeps],
    query: str
) -> str:
    """Perform deep search using injected search agent."""
    # Use dependency agent
    result = await ctx.deps.search_agent.run(query)
    return result.data

# Usage with dependency injection
async def run_research(query: str, db: Session, user_id: str):
    deps = ResearchDeps(
        db_session=db,
        search_agent=search_agent,
        user_id=user_id
    )

    result = await synthesis_agent.run(query, deps=deps)
    return result.data
```

## DBOS Integration

### Setup DBOS

```bash
# Install DBOS
pip install dbos asyncpg

# Create database
createdb deep_research

# Configure in .env
DATABASE_URL=postgresql://postgres:password@localhost:5432/deep_research
```

### Wrap Agents for Durability

```python
from dbos import DBOS, DBOSAgent
import os

# Configure DBOS
DBOS.config = {
    'system_database_url': os.getenv('DATABASE_URL')
}

# Wrap Pydantic AI agents
durable_plan_agent = DBOSAgent(plan_agent)
durable_search_agent = DBOSAgent(search_agent)
durable_synthesis_agent = DBOSAgent(synthesis_agent)

@DBOS.workflow()
async def durable_research_workflow(query: str) -> ResearchReport:
    """Durable workflow with automatic state persistence."""
    workflow_id = DBOS.workflow_id

    # Phase 1: Planning (checkpointed automatically)
    plan_result = await durable_plan_agent.run(query)
    plan = plan_result.data

    # Phase 2: Parallel searches (each checkpointed)
    search_workflows = [
        await DBOS.start_workflow_async(
            durable_search_agent.run,
            step.query,
            workflow_id=f"{workflow_id}-search-{i}"
        )
        for i, step in enumerate(plan.search_steps)
    ]

    # Wait for all searches
    search_results = [await wf for wf in search_workflows]

    # Phase 3: Synthesis (checkpointed)
    report_result = await durable_synthesis_agent.run(plan, search_results)

    return report_result.data
```

### Resume Failed Workflows

```python
import sys

async def main():
    # Check for resume ID
    resume_id = sys.argv[1] if len(sys.argv) > 1 else None

    if resume_id:
        print(f"Resuming workflow: {resume_id}")
        # DBOS automatically resumes from last checkpoint
        result = await DBOS.resume_workflow(resume_id)
    else:
        # Start new workflow
        query = "What are the latest developments in quantum computing?"
        result = await durable_research_workflow(query)

    print(result)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
```

**Resume Example**:
```bash
# Run workflow
python src/workflows/deep_research_dbos.py
# Output: Workflow ID: wf-abc123
# [Fails during synthesis phase]

# Resume from checkpoint
python src/workflows/deep_research_dbos.py wf-abc123
# Skips completed planning and search phases
# Resumes from synthesis
```

## Observability with Logfire

### Instrument Application

```python
import logfire
from pydantic_ai import Agent

# Configure Logfire
logfire.configure(
    service_name='deep-research',
    environment='production',
    send_to_logfire=True
)

# Auto-instrument Pydantic AI
logfire.instrument_pydantic_ai()

# Agents automatically emit traces
plan_agent = Agent(
    model='anthropic:claude-sonnet-4-5',
    name='research-planner',  # Shows in Logfire UI
    result_type=ResearchPlan
)

# Manual spans for workflow phases
async def execute_research(query: str) -> ResearchReport:
    """Execute research with detailed tracing."""

    with logfire.span(
        'research.workflow',
        query=query,
        workflow_id=workflow_id
    ) as workflow_span:

        # Phase 1: Planning
        with logfire.span('research.planning'):
            plan = await plan_agent.run(query)
            workflow_span.set_attribute('num_searches', len(plan.search_steps))

        # Phase 2: Gathering
        with logfire.span(
            'research.gathering',
            num_searches=len(plan.search_steps)
        ):
            results = await parallel_search(plan)

        # Phase 3: Synthesis
        with logfire.span('research.synthesis'):
            report = await synthesis_agent.run(plan, results)

        # Record metrics
        workflow_span.set_attribute('total_sources', len(report.sources))
        workflow_span.set_attribute('report_length', len(report.content))

    return report
```

### Custom Metrics

```python
# Track costs
@logfire.instrument('agent.cost_tracking')
async def run_with_cost_tracking(agent: Agent, query: str):
    """Run agent and track token costs."""
    result = await agent.run(query)

    # Log cost metrics
    logfire.info(
        'agent_execution',
        agent_name=agent.name,
        model=agent.model,
        input_tokens=result.usage.input_tokens,
        output_tokens=result.usage.output_tokens,
        total_cost_usd=result.usage.total_cost
    )

    return result
```

## Testing Strategy

### Unit Tests with TestModel

```python
import pytest
from pydantic_ai.models.test import TestModel
from pydantic_ai import Agent

@pytest.mark.asyncio
async def test__plan_agent__creates_valid_plan():
    """Plan agent generates valid ResearchPlan structure."""
    # Arrange: Use TestModel to avoid API calls
    test_agent = Agent(
        model=TestModel(),
        result_type=ResearchPlan
    )

    # Act
    result = await test_agent.run("Research quantum computing")

    # Assert
    assert result.data is not None
    assert isinstance(result.data, ResearchPlan)
    assert len(result.data.search_steps) > 0
    assert result.data.estimated_duration_minutes > 0

@pytest.mark.asyncio
async def test__parallel_search__executes_concurrently():
    """Parallel searches execute faster than sequential."""
    import time

    plan = ResearchPlan(
        executive_summary="Test plan",
        search_steps=[SearchStep(query=f"Query {i}") for i in range(5)],
        estimated_duration_minutes=10
    )

    start = time.time()
    results = await parallel_research(plan)
    duration = time.time() - start

    # Assert: Should take ~1 search duration, not 5x
    assert duration < 2.0  # Generous threshold
    assert len(results) == 5
```

### Integration Tests

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test__complete_workflow__produces_report():
    """Complete research workflow from query to report."""
    # Requires actual API keys in test environment
    query = "Latest developments in quantum computing"

    workflow = ResearchWorkflow(workflow_id="test-001")
    report = await workflow.execute(query, constraints={})

    # Verify report quality
    assert report is not None
    assert len(report.key_findings) >= 3
    assert len(report.sources) >= 5
    assert report.summary is not None

    # Verify event tracking
    assert len(workflow.events) >= 5
    assert workflow.events[0].event_type == EventType.RESEARCH_INITIATED
    assert workflow.events[-1].event_type == EventType.RESEARCH_COMPLETED
```

### Event Assertion Tests

```python
@pytest.mark.asyncio
async def test__workflow_events__emitted_correctly():
    """Workflow emits all expected domain events."""
    workflow = ResearchWorkflow(workflow_id="test-001")
    await workflow.execute("Test query", constraints={})

    # Assert event sequence
    event_types = [e.event_type for e in workflow.events]

    assert EventType.RESEARCH_INITIATED in event_types
    assert EventType.PLAN_CREATED in event_types
    assert EventType.REPORT_GENERATED in event_types
    assert EventType.RESEARCH_COMPLETED in event_types

    # Assert event order
    initiated_idx = event_types.index(EventType.RESEARCH_INITIATED)
    completed_idx = event_types.index(EventType.RESEARCH_COMPLETED)
    assert initiated_idx < completed_idx
```

## Common Patterns & Anti-Patterns

### ✅ DO

1. **Use Pydantic models for all structured data**
   ```python
   result_type=ResearchPlan  # Type-safe output
   ```

2. **Leverage async/await everywhere**
   ```python
   async def execute_search(query: str) -> SearchResult:
   ```

3. **Emit domain events for state changes**
   ```python
   self.events.append(PlanCreated(plan=plan))
   ```

4. **Use dependency injection for testability**
   ```python
   deps_type=ResearchDeps
   ```

5. **Parallelize independent operations**
   ```python
   async with asyncio.TaskGroup() as tg:
   ```

### ❌ DON'T

1. **Don't use raw dictionaries for structured data**
   ```python
   # Bad
   plan = {"summary": "...", "steps": [...]}

   # Good
   plan = ResearchPlan(executive_summary="...", search_steps=[...])
   ```

2. **Don't block async event loop**
   ```python
   # Bad
   result = requests.get(url)  # Synchronous

   # Good
   async with httpx.AsyncClient() as client:
       result = await client.get(url)
   ```

3. **Don't ignore error handling in tools**
   ```python
   # Bad
   async def search(query: str) -> str:
       response = await client.post(url)  # May raise
       return response.json()

   # Good
   async def search(query: str) -> str:
       try:
           response = await client.post(url, timeout=30)
           response.raise_for_status()
           return response.json()
       except Exception as e:
           return f"Search failed: {e}"
   ```

4. **Don't tightly couple agent logic to infrastructure**
   ```python
   # Bad: DBOS code mixed with agent logic
   async def plan_research(query: str):
       await DBOS.checkpoint()
       plan = create_plan(query)
       await DBOS.checkpoint()

   # Good: Separate concerns
   async def plan_research(query: str):
       return create_plan(query)  # Pure logic

   @DBOS.workflow()
   async def durable_plan(query: str):
       return await plan_research(query)  # Wrapper
   ```

5. **Don't execute dependent tasks in parallel**
   ```python
   # Bad: Synthesis depends on search results
   async with asyncio.TaskGroup() as tg:
       search_task = tg.create_task(search())
       synthesis_task = tg.create_task(synthesize())  # Won't work!

   # Good: Sequential when dependent
   results = await search()
   report = await synthesize(results)
   ```

## Next Steps

1. Review [AGENT_ARCHITECTURE.md](./AGENT_ARCHITECTURE.md) for design patterns
2. Set up dependencies: `just sync`
3. Start with simple agent example above
4. Implement planning agent following patterns
5. Add parallel search execution
6. Integrate event-driven state management
7. Add DBOS durability when needed
8. Deploy with Logfire observability

## Resources

- [Pydantic AI Docs](https://ai.pydantic.dev/)
- [DBOS Python Guide](https://docs.dbos.dev/python/quickstart)
- [Logfire Documentation](https://logfire.pydantic.dev/)
- [durable-exec Reference](https://github.com/pydantic/pydantic-stack-demo/tree/main/durable-exec)
