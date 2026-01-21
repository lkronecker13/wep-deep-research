# Deep Research Agent Architecture

Analysis of durable-exec patterns and recommendations for implementing deep research capabilities.

## Executive Summary

The [pydantic-stack-demo/durable-exec](https://github.com/pydantic/pydantic-stack-demo/tree/main/durable-exec) implementation demonstrates production patterns for building durable, multi-agent research systems using Pydantic AI. This document analyzes these patterns and provides recommendations for implementing robust deep research capabilities in this project.

## Key Findings from durable-exec

### 1. Agent Orchestration Pattern

The implementation uses a **three-phase sequential pipeline** with parallel execution within phases:

```
Planning → Information Gathering → Synthesis
(1 agent)  (N parallel agents)    (1 agent)
```

**Pattern Details**:
- **Planning Agent**: Creates structured research blueprint (Claude Sonnet 4.5)
- **Search Agents**: Execute parallel web searches (Gemini 2.5 Flash)
- **Analysis Agent**: Synthesizes findings into report (Claude Sonnet 4.5)

**Key Insight**: Different models for different phases optimizes cost and performance. Fast models (Gemini Flash) for parallel execution, powerful models (Claude Sonnet) for reasoning.

### 2. State Management Approach

State flows through **typed Pydantic models** without explicit persistence in base implementation:

```python
# State flow via typed models
plan: DeepResearchPlan = await plan_agent.run(query)
search_results: list[SearchResult] = await gather_searches(plan)
report: DeepResearchReport = await analysis_agent.run(plan, search_results)
```

**Durability Layer Patterns**:
- **Base Python**: No persistence, ephemeral execution
- **DBOS**: PostgreSQL-backed state storage
- **Temporal**: External orchestration server with event sourcing

**Key Insight**: Agent logic remains identical across backends. Durability is infrastructure concern, not agent concern.

### 3. Tool Integration Patterns

Two distinct patterns for agent tools:

**Built-in Tools**:
```python
search_agent = Agent(
    model='google-gla:gemini-2.5-flash',
    tools=[WebSearchTool()]  # Tool in agent config
)
```

**Dynamic Tools with Dependency Injection**:
```python
@analysis_agent.tool
async def extra_search(ctx: RunContext[SearchAgent], query: str) -> str:
    """Dynamic search during analysis."""
    result = await ctx.deps.run(query)  # Invoke dependency agent
    return result.data
```

**Key Insight**: Tools can invoke other agents via dependency injection, enabling hierarchical agent coordination.

### 4. Parallel Execution Pattern

Concurrent task execution using `asyncio.TaskGroup`:

```python
async with asyncio.TaskGroup() as tg:
    search_tasks = [
        tg.create_task(search_agent.run(step.query))
        for step in plan.search_steps
    ]
```

**Key Insight**: Independent searches execute concurrently, dramatically reducing total execution time.

### 5. Error Handling and Retry

**Infrastructure-Provided Durability**:
- DBOS: Automatic retry via PostgreSQL transaction log
- Temporal: Configurable retry policies and timeouts

```python
# DBOS: Resume failed workflow
resume_id = sys.argv[1] if len(sys.argv) > 1 else None
if resume_id:
    wf_id = resume_id  # Continue from checkpoint
```

**Key Insight**: Explicit try/catch is minimized. Infrastructure handles transient failures and provides workflow resumption.

## Architectural Recommendations

### Recommended Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Agent Framework | Pydantic AI | Type-safe, FastAPI integration, minimal dependencies |
| Durability Layer | DBOS | PostgreSQL-backed, simpler deployment than Temporal |
| Observability | Logfire | Native Pydantic AI integration, excellent debugging |
| State Management | Pydantic Models + Events | Type safety + audit trail + integration |
| Web Search | Tavily API | Production-grade search with citations |

### Four-Phase Deep Research Workflow

Extend the three-phase pattern with verification:

```
Planning → Gathering → Synthesis → Verification
   ↓           ↓           ↓            ↓
Events    Events      Events       Events
```

**Phase 1: Research Planning**
- **Agent**: `ResearchPlanAgent`
- **Model**: Claude Sonnet 4.5
- **Input**: Research question + constraints (depth, sources, deadline)
- **Output**: `ResearchPlan` (Pydantic model)
- **Tools**: None (pure reasoning)
- **Event**: `PlanCreated`

**Phase 2: Information Gathering** (parallel)
- **Agent**: `InformationGatheringAgent`
- **Model**: Gemini 2.5 Flash (cost-effective for parallel execution)
- **Input**: Individual search steps from plan
- **Output**: `SearchResult[]` with metadata
- **Tools**: `WebSearchTool`, `DocumentRetrievalTool`, `APIQueryTool`
- **Events**: `SearchCompleted` (per task)

**Phase 3: Synthesis**
- **Agent**: `SynthesisAgent`
- **Model**: Claude Sonnet 4.5
- **Input**: Research plan + all search results
- **Output**: `DeepResearchReport`
- **Tools**: `extra_search` (dynamic follow-up)
- **Event**: `ReportGenerated`

**Phase 4: Verification** (NEW)
- **Agent**: `VerificationAgent`
- **Model**: Claude Sonnet 4.5
- **Input**: Report + original question
- **Output**: `ValidationResult`
- **Tools**: `citation_check`, `source_reliability`
- **Event**: `ResearchCompleted` / `ResearchFailed`

### Project Structure

```
src/
├── agents/
│   ├── __init__.py
│   ├── planning_agent.py           # ResearchPlanAgent
│   ├── gathering_agent.py          # InformationGatheringAgent
│   ├── synthesis_agent.py          # SynthesisAgent
│   └── verification_agent.py       # VerificationAgent
│
├── workflows/
│   ├── __init__.py
│   ├── deep_research.py            # Base workflow orchestration
│   └── deep_research_dbos.py       # DBOS-wrapped durable version
│
├── models/
│   ├── __init__.py
│   ├── research_plan.py            # ResearchPlan, SearchStep
│   ├── search_result.py            # SearchResult, Citation
│   └── research_report.py          # DeepResearchReport, Finding
│
├── tools/
│   ├── __init__.py
│   ├── web_search.py               # WebSearchTool (Tavily)
│   ├── document_retrieval.py       # DocumentRetrievalTool
│   └── citation_verification.py    # CitationVerificationTool
│
├── events/
│   ├── __init__.py
│   └── research_events.py          # Domain events
│
└── repositories/
    ├── __init__.py
    └── research_repository.py      # Persistence layer
```

### State Management with Event-Driven Architecture

Integrate Pydantic AI agents with event-driven patterns (from `arch-events` skill):

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

# Domain Events
@dataclass
class ResearchInitiated:
    query: str
    timestamp: datetime
    workflow_id: str

@dataclass
class PlanCreated:
    plan: ResearchPlan
    timestamp: datetime

@dataclass
class SearchCompleted:
    search_step: str
    result: SearchResult
    timestamp: datetime

@dataclass
class ReportGenerated:
    report: DeepResearchReport
    timestamp: datetime

@dataclass
class ResearchCompleted:
    workflow_id: str
    report: DeepResearchReport
    timestamp: datetime

# Workflow Aggregate
class ResearchWorkflow:
    """Aggregate root collecting domain events during research."""

    def __init__(self, workflow_id: str) -> None:
        self.workflow_id = workflow_id
        self.events: list[DomainEvent] = []

    async def execute(self, query: str) -> DeepResearchReport:
        """Execute complete research workflow with event tracking."""
        self.events.append(ResearchInitiated(
            query=query,
            timestamp=datetime.utcnow(),
            workflow_id=self.workflow_id
        ))

        # Phase 1: Planning
        plan = await plan_agent.run(query)
        self.events.append(PlanCreated(
            plan=plan,
            timestamp=datetime.utcnow()
        ))

        # Phase 2: Parallel information gathering
        async with asyncio.TaskGroup() as tg:
            search_tasks = [
                tg.create_task(self._search_and_emit(step))
                for step in plan.search_steps
            ]

        # Phase 3: Synthesis
        report = await synthesis_agent.run(plan, search_results)
        self.events.append(ReportGenerated(
            report=report,
            timestamp=datetime.utcnow()
        ))

        # Phase 4: Verification
        validation = await verification_agent.run(query, report)
        if validation.is_valid:
            self.events.append(ResearchCompleted(
                workflow_id=self.workflow_id,
                report=report,
                timestamp=datetime.utcnow()
            ))
        else:
            self.events.append(ResearchFailed(
                workflow_id=self.workflow_id,
                reason=validation.failure_reason,
                timestamp=datetime.utcnow()
            ))

        return report

    async def _search_and_emit(self, step: SearchStep) -> SearchResult:
        """Execute search and emit completion event."""
        result = await gathering_agent.run(step.query)
        self.events.append(SearchCompleted(
            search_step=step.query,
            result=result,
            timestamp=datetime.utcnow()
        ))
        return result
```

**Benefits of Event-Driven Approach**:
1. **Progress Tracking**: UI can subscribe to events for real-time updates
2. **Audit Trail**: Complete research history for reproducibility
3. **Retry/Resume**: Event sourcing enables workflow reconstruction
4. **Integration**: Other services react to research completion
5. **Testing**: Event assertions validate workflow behavior

### Dependency Injection Pattern

Following durable-exec's dependency pattern:

```python
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel

# Define agent dependencies
class ResearchDeps(BaseModel):
    gathering_agent: Agent
    db_session: Session
    config: ResearchConfig

# Planning agent with no dependencies
plan_agent = Agent(
    model='anthropic:claude-sonnet-4-5',
    system_prompt='You are a research planning specialist...',
    result_type=ResearchPlan
)

# Gathering agent with web search tool
gathering_agent = Agent(
    model='google-gla:gemini-2.5-flash',
    tools=[WebSearchTool(), DocumentRetrievalTool()]
)

# Synthesis agent with dynamic search capability
synthesis_agent = Agent(
    model='anthropic:claude-sonnet-4-5',
    deps_type=ResearchDeps,
    result_type=DeepResearchReport
)

@synthesis_agent.tool
async def extra_search(
    ctx: RunContext[ResearchDeps],
    query: str
) -> str:
    """Perform additional search during synthesis if needed."""
    result = await ctx.deps.gathering_agent.run(query)
    return result.data
```

**Key Pattern**: Use `deps_type` for context injection, enabling agents to invoke other agents or access shared resources.

### DBOS Integration Pattern

Wrap the base workflow for durability:

```python
from dbos import DBOS

# Configure DBOS
DBOS.config = {
    'system_database_url': 'postgresql://postgres@localhost:5432/dbos'
}

# Wrap agents as DBOS entities
from dbos import DBOSAgent

dbos_plan_agent = DBOSAgent(plan_agent)
dbos_gathering_agent = DBOSAgent(gathering_agent)
dbos_synthesis_agent = DBOSAgent(synthesis_agent)

@DBOS.workflow()
async def durable_deep_research(query: str) -> DeepResearchReport:
    """DBOS-wrapped workflow with automatic state persistence."""
    workflow_id = DBOS.workflow_id

    # Phase 1: Planning (automatically checkpointed)
    plan = await dbos_plan_agent.run(query)

    # Phase 2: Parallel gathering (each task checkpointed)
    search_workflows = [
        await DBOS.start_workflow_async(
            dbos_gathering_agent.run,
            step.query
        )
        for step in plan.search_steps
    ]
    search_results = [await wf for wf in search_workflows]

    # Phase 3: Synthesis (checkpointed)
    report = await dbos_synthesis_agent.run(plan, search_results)

    return report

# Resume capability
if __name__ == '__main__':
    resume_id = sys.argv[1] if len(sys.argv) > 1 else None

    if resume_id:
        print(f'Resuming workflow {resume_id}')
        result = DBOS.resume_workflow(resume_id)
    else:
        query = "What are the latest developments in quantum computing?"
        result = asyncio.run(durable_deep_research(query))
```

**DBOS Benefits**:
- Automatic state persistence to PostgreSQL
- Resume failed workflows without re-executing completed steps
- No external orchestration infrastructure needed
- Simpler deployment than Temporal for single-service architecture

### Tool Integration Best Practices

Following durable-exec patterns:

```python
from pydantic_ai.tools import Tool
from typing import Annotated
import httpx

class WebSearchTool(Tool):
    """Tavily-powered web search with citations."""

    name = "web_search"
    description = "Search the web for current information"

    async def __call__(
        self,
        query: Annotated[str, "Search query"],
        max_results: Annotated[int, "Maximum results"] = 5
    ) -> str:
        """Execute web search and return formatted results."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "query": query,
                    "max_results": max_results,
                    "include_citations": True
                },
                headers={"Authorization": f"Bearer {TAVILY_API_KEY}"}
            )
            results = response.json()

        # Format results with citations
        formatted = []
        for result in results['results']:
            formatted.append(
                f"Title: {result['title']}\n"
                f"Source: {result['url']}\n"
                f"Content: {result['content']}\n"
            )

        return "\n---\n".join(formatted)
```

**Tool Design Principles**:
1. **Type annotations**: Use `Annotated` for parameter descriptions
2. **Async by default**: All tools should be async for composability
3. **Error handling**: Return error messages as strings, don't raise
4. **Structured output**: Return formatted strings suitable for LLM consumption
5. **Citation tracking**: Always include source URLs for verification

### Testing Strategy

Testing approach for agent workflows:

```python
import pytest
from unittest.mock import AsyncMock
from pydantic_ai.models.test import TestModel

class TestDeepResearchWorkflow:
    """Tests for deep research workflow orchestration."""

    @pytest.mark.asyncio
    async def test__execute_workflow__completes_all_phases(self):
        """Workflow executes planning, gathering, synthesis, and verification."""
        # Arrange: Mock agents with TestModel
        mock_plan = ResearchPlan(
            executive_summary="Test research plan",
            search_steps=[
                SearchStep(query="Test query 1"),
                SearchStep(query="Test query 2")
            ]
        )

        plan_agent = Agent(
            model=TestModel(),
            result_type=ResearchPlan
        )

        # Act
        workflow = ResearchWorkflow(workflow_id="test-001")
        report = await workflow.execute("Test research question")

        # Assert
        assert len(workflow.events) >= 5  # Initiated, Plan, 2x Search, Report
        assert isinstance(workflow.events[0], ResearchInitiated)
        assert isinstance(workflow.events[-1], ResearchCompleted)
        assert report is not None

    @pytest.mark.asyncio
    async def test__parallel_gathering__executes_concurrently(self):
        """Search tasks execute in parallel, not sequentially."""
        # Arrange
        import time

        async def slow_search(query: str):
            await asyncio.sleep(0.1)
            return SearchResult(content=f"Result for {query}")

        plan = ResearchPlan(search_steps=[
            SearchStep(query=f"Query {i}")
            for i in range(5)
        ])

        # Act
        start = time.time()
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(slow_search(step.query)) for step in plan.search_steps]
        duration = time.time() - start

        # Assert: Parallel execution should take ~0.1s, not 0.5s
        assert duration < 0.2  # Allow some overhead

    @pytest.mark.asyncio
    async def test__workflow_resume__skips_completed_steps(self):
        """DBOS workflow resume skips already-completed phases."""
        # Integration test with actual DBOS
        # This would require DBOS test fixtures
        pass
```

**Testing Recommendations**:
1. Use `TestModel` for unit testing agent logic without API calls
2. Test workflow orchestration separately from agent behavior
3. Verify event emission at each phase
4. Test parallel execution performance characteristics
5. Integration tests for DBOS resume functionality

### Observability with Logfire

Instrument agents for production debugging:

```python
import logfire
from pydantic_ai import Agent

# Configure Logfire
logfire.configure(
    service_name='deep-research',
    environment='production'
)

# Instrument Pydantic AI
logfire.instrument_pydantic_ai()

# Agents automatically emit traces
plan_agent = Agent(
    model='anthropic:claude-sonnet-4-5',
    name='research-planner',  # Shows in traces
    result_type=ResearchPlan
)

# Manual instrumentation for workflow phases
async def execute_research(query: str) -> DeepResearchReport:
    with logfire.span('research.workflow', query=query):
        with logfire.span('research.planning'):
            plan = await plan_agent.run(query)

        with logfire.span('research.gathering', num_searches=len(plan.search_steps)):
            # Parallel searches
            ...

        with logfire.span('research.synthesis'):
            report = await synthesis_agent.run(plan, search_results)

    return report
```

**Observability Benefits**:
- Trace complete workflow execution across agent calls
- Debug tool invocations and dependency injection
- Monitor token usage and costs per phase
- Alert on workflow failures or timeouts

## Implementation Roadmap

### Phase 1: Foundation (Week 1)
- [ ] Add dependencies: `pydantic-ai`, `httpx`, `tavily-python`, `logfire`
- [ ] Implement Pydantic models: `ResearchPlan`, `SearchResult`, `DeepResearchReport`
- [ ] Create domain events: `ResearchInitiated`, `PlanCreated`, etc.
- [ ] Set up Logfire instrumentation

### Phase 2: Agent Development (Week 2)
- [ ] Implement `ResearchPlanAgent` with test coverage
- [ ] Implement `InformationGatheringAgent` with `WebSearchTool`
- [ ] Implement `SynthesisAgent` with `extra_search` tool
- [ ] Unit tests for each agent using `TestModel`

### Phase 3: Workflow Orchestration (Week 3)
- [ ] Implement base `deep_research.py` workflow
- [ ] Add event emission at each phase
- [ ] Implement parallel execution with `asyncio.TaskGroup`
- [ ] Integration tests for complete workflow

### Phase 4: Durability Layer (Week 4)
- [ ] Set up PostgreSQL for DBOS
- [ ] Implement `deep_research_dbos.py` wrapper
- [ ] Add workflow resume capability
- [ ] Test failure recovery scenarios

### Phase 5: Verification & Production (Week 5)
- [ ] Implement `VerificationAgent` for fact-checking
- [ ] Add citation verification tool
- [ ] Performance optimization (caching, batching)
- [ ] Production deployment and monitoring

## Key Takeaways

### What to Adopt from durable-exec

1. **Three-phase pattern**: Plan → Gather → Synthesize is proven for research
2. **Type-safe state flow**: Pydantic models ensure correctness
3. **Parallel execution**: `asyncio.TaskGroup` for independent tasks
4. **Infrastructure durability**: Separate agent logic from persistence concerns
5. **Dependency injection**: Enable agent composition and testing

### What to Extend

1. **Add verification phase**: Critical for research integrity
2. **Event-driven state**: Enable progress tracking and integration
3. **Richer tool ecosystem**: Beyond web search (documents, APIs, databases)
4. **Multi-model support**: Different models for different task types
5. **Cost tracking**: Monitor token usage per phase for optimization

### What to Avoid

1. **Explicit error handling in agents**: Let infrastructure handle retries
2. **Tight coupling**: Keep agent logic independent of durability layer
3. **Synchronous execution**: Use async everywhere for composability
4. **Premature optimization**: Start with base implementation, add DBOS when needed

## References

- [Pydantic AI Documentation](https://ai.pydantic.dev/)
- [DBOS Documentation](https://docs.dbos.dev/)
- [Temporal Documentation](https://docs.temporal.io/)
- [durable-exec Source](https://github.com/pydantic/pydantic-stack-demo/tree/main/durable-exec)
- [Logfire Documentation](https://logfire.pydantic.dev/)
