# Architecture Decision Record: Deep Research Agent System

Decision rationale and trade-offs for agent architecture based on durable-exec analysis.

## Status

**PROPOSED** - Architecture recommendations based on durable-exec patterns

## Context

We are building a deep research system capable of conducting multi-step, long-running research workflows. The system must handle:

1. Complex multi-phase research tasks (planning → gathering → synthesis → verification)
2. Parallel execution of independent research steps
3. Durability and resumption of long-running workflows
4. Integration with existing event-driven architecture
5. Type-safe state management across workflow phases
6. Production observability and cost tracking

The [Pydantic Stack Demo](https://github.com/pydantic/pydantic-stack-demo) provides proven patterns through their `durable-exec` implementation, which demonstrates three approaches: base Python, DBOS-backed, and Temporal-based execution.

## Decision

We will implement a **four-phase deep research workflow** using **Pydantic AI agents** with **DBOS-backed durability** and **event-driven state management**.

### Core Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Agent Framework** | Pydantic AI | Type-safe, FastAPI integration, minimal dependencies |
| **Durability Layer** | DBOS (Phase 2) | PostgreSQL-backed, simpler deployment than Temporal |
| **Observability** | Logfire | Native Pydantic AI integration, excellent debugging |
| **State Management** | Pydantic Models + Domain Events | Type safety + audit trail + integration |
| **Web Search** | Tavily API | Production-grade search with citations |
| **LLM Providers** | Anthropic Claude + Google Gemini | Claude for reasoning, Gemini for parallel tasks |

### Architectural Patterns

#### 1. Four-Phase Workflow (Extension of durable-exec's three-phase)

```
┌─────────────┐      ┌──────────────┐      ┌───────────┐      ┌──────────────┐
│  Planning   │ ───> │  Gathering   │ ───> │ Synthesis │ ───> │ Verification │
│   Agent     │      │  (Parallel)  │      │   Agent   │      │    Agent     │
└─────────────┘      └──────────────┘      └───────────┘      └──────────────┘
      │                     │                     │                    │
      v                     v                     v                    v
 PlanCreated          SearchCompleted       ReportGenerated    ResearchCompleted
```

**Why add verification phase?**
- Research integrity requires fact-checking
- Citation verification prevents hallucinated sources
- Source reliability assessment critical for quality
- Separates synthesis logic from validation logic

#### 2. Event-Driven State Management (Integration with arch-events)

Combine Pydantic AI agents with domain events pattern:

```python
class ResearchWorkflow:
    """Aggregate root collecting domain events."""
    events: list[DomainEvent] = []

    async def execute(self, query: str) -> DeepResearchReport:
        # Emit events at each phase transition
        self.events.append(ResearchInitiated(...))
        plan = await plan_agent.run(query)
        self.events.append(PlanCreated(plan=plan))
        # ... continue workflow
```

**Benefits**:
- Progress tracking for UI updates
- Complete audit trail for reproducibility
- Event sourcing enables workflow replay
- Integration points for other services
- Aligns with existing `arch-events` skill patterns

#### 3. Layered Durability Approach

**Phase 1: Base Implementation** (Weeks 1-3)
- Pure Pydantic AI agents without durability
- Event emission for state tracking
- In-memory workflow execution
- Focus on agent logic correctness

**Phase 2: Add DBOS** (Week 4)
- Wrap existing agents with `DBOSAgent`
- PostgreSQL state persistence
- Workflow resumption capability
- No changes to agent logic required

**Why phased approach?**
- Validate agent logic before adding complexity
- DBOS wrapper requires zero agent code changes
- Easier testing without durability layer
- Incremental risk reduction

#### 4. Multi-Model Strategy (From durable-exec)

Different LLM models for different task characteristics:

| Phase | Model | Rationale |
|-------|-------|-----------|
| Planning | Claude Sonnet 4.5 | Complex reasoning, strategic thinking |
| Gathering | Gemini 2.5 Flash | Fast, parallel, cost-effective |
| Synthesis | Claude Sonnet 4.5 | Deep analysis, coherent writing |
| Verification | Claude Sonnet 4.5 | Critical evaluation, fact-checking |

**Cost Optimization**:
- Gemini Flash: $0.10/1M input tokens (10x cheaper than Claude)
- 5 parallel searches with Gemini saves ~$0.50 per workflow
- Claude reserved for phases requiring deep reasoning

#### 5. Dependency Injection Pattern (From durable-exec)

Enable agent composition and testing:

```python
class ResearchDeps(BaseModel):
    search_agent: Agent
    db_session: Session
    user_id: str

synthesis_agent = Agent(
    deps_type=ResearchDeps,
    result_type=ResearchReport
)

@synthesis_agent.tool
async def extra_search(ctx: RunContext[ResearchDeps], query: str) -> str:
    return await ctx.deps.search_agent.run(query)
```

**Benefits**:
- Agents can invoke other agents
- Easy mocking for unit tests
- Flexible composition at runtime
- Testable without API calls

## Alternatives Considered

### Alternative 1: Temporal Instead of DBOS

**Pros**:
- More mature ecosystem
- Better multi-service orchestration
- Stronger guarantees for distributed systems
- Rich UI for workflow visualization

**Cons**:
- Requires separate Temporal server deployment
- More complex infrastructure (server + workers + database)
- Overkill for single-service architecture
- Steeper learning curve

**Decision**: Use DBOS initially. Temporal is better for microservices but adds unnecessary complexity for our monolithic research service.

### Alternative 2: LangChain Instead of Pydantic AI

**Pros**:
- More mature framework
- Larger tool ecosystem
- LangGraph for complex agent flows
- LangSmith observability

**Cons**:
- Heavier dependency footprint
- Less type-safe than Pydantic AI
- More complex abstractions (LCEL)
- Slower updates than Pydantic AI

**Decision**: Pydantic AI aligns better with our type-safe philosophy and FastAPI-first architecture. LangChain's benefits don't outweigh the complexity cost.

### Alternative 3: No Durability Layer

**Pros**:
- Simplest implementation
- Fastest development
- No infrastructure overhead

**Cons**:
- Long workflows lost on failure
- No resume capability
- Poor user experience for expensive research
- Wasted API costs on retry

**Decision**: Start without durability but plan for DBOS in Phase 2. Research workflows are too expensive to re-run from scratch on transient failures.

### Alternative 4: Synchronous Execution

**Pros**:
- Simpler code (no async/await)
- Easier debugging
- Familiar patterns

**Cons**:
- 5x slower (sequential vs parallel searches)
- Blocks on I/O (web searches, API calls)
- Poor user experience (longer wait times)

**Decision**: Async/await is mandatory. Parallel execution provides 5-10x speedup for independent research tasks.

## Implementation Strategy

### Phase 1: Foundation (Week 1)

**Goal**: Type-safe models and event infrastructure

```
src/models/
├── research_plan.py       # ResearchPlan, SearchStep
├── search_result.py       # SearchResult, Citation
└── research_report.py     # DeepResearchReport, Finding

src/events/
└── research_events.py     # Domain events
```

**Deliverables**:
- Pydantic models with validation
- Domain event definitions
- Test coverage for models

### Phase 2: Agent Development (Week 2)

**Goal**: Individual agents with tools

```
src/agents/
├── planning_agent.py      # ResearchPlanAgent
├── gathering_agent.py     # InformationGatheringAgent
├── synthesis_agent.py     # SynthesisAgent
└── verification_agent.py  # VerificationAgent

src/tools/
├── web_search.py          # Tavily integration
└── citation_check.py      # Citation verification
```

**Deliverables**:
- 4 specialized agents
- Web search tool implementation
- Unit tests using `TestModel`

### Phase 3: Workflow Orchestration (Week 3)

**Goal**: End-to-end workflow without durability

```
src/workflows/
└── deep_research.py       # Base workflow
```

**Deliverables**:
- Complete research workflow
- Event emission at each phase
- Parallel search execution
- Integration tests

### Phase 4: Durability Layer (Week 4)

**Goal**: DBOS-backed resumable workflows

```
src/workflows/
└── deep_research_dbos.py  # DBOS wrapper
```

**Deliverables**:
- DBOS integration
- Resume functionality
- Failure recovery tests

### Phase 5: Production Hardening (Week 5)

**Goal**: Observability and monitoring

**Deliverables**:
- Logfire instrumentation
- Cost tracking per phase
- Performance optimization
- Production deployment

## Integration with Existing Architecture

### Event-Driven Architecture (arch-events skill)

Research workflows emit domain events compatible with existing event bus:

```python
# Existing pattern from arch-events
class MessageBus:
    def handle(self, event: DomainEvent) -> None:
        for handler in self.handlers[type(event)]:
            handler(event)

# Research events integrate seamlessly
bus = MessageBus()
bus.subscribe(PlanCreated, update_progress_ui)
bus.subscribe(SearchCompleted, log_search_metrics)
bus.subscribe(ResearchCompleted, notify_user)
```

### Repository Pattern (arch-ddd skill)

Persist research artifacts using existing repository layer:

```python
class ResearchRepository(Protocol):
    def add(self, workflow: ResearchWorkflow) -> None: ...
    def get(self, workflow_id: str) -> ResearchWorkflow: ...

# Use in workflow
async def execute_research(query: str, repo: ResearchRepository):
    workflow = ResearchWorkflow(workflow_id=uuid4())
    report = await workflow.execute(query)

    # Save aggregate with events
    repo.add(workflow)
```

### Service Layer Pattern (arch-ddd skill)

Expose research capabilities through service layer:

```python
class ResearchService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def conduct_research(
        self,
        query: str,
        user_id: str
    ) -> ResearchReport:
        async with self.uow:
            workflow = ResearchWorkflow(workflow_id=str(uuid4()))
            report = await workflow.execute(query)

            # Persist with events
            self.uow.research_repo.add(workflow)
            await self.uow.commit()

            # Publish events
            for event in workflow.events:
                await self.message_bus.handle(event)

        return report
```

### Testing Standards (dev-standards skill)

Follow project test naming convention:

```python
# Correct naming: test__<what>__<expected>
def test__plan_agent__creates_valid_research_plan():
    """Planning agent generates valid ResearchPlan with search steps."""
    ...

def test__parallel_search__executes_faster_than_sequential():
    """Parallel search execution reduces total time significantly."""
    ...

def test__workflow_resume__skips_completed_phases():
    """DBOS workflow resume continues from last checkpoint."""
    ...
```

## Validation and Quality Gates

### Before Any Commit

Run full validation (per dev-standards):

```bash
just validate-branch
```

This executes:
1. `just format` - Code formatting
2. `just lint` - Linting with auto-fix
3. `just type-check` - Type validation (mypy strict)
4. `just test` - 80% coverage minimum

### Agent-Specific Quality Gates

**Planning Agent**:
- [ ] Generates 1-5 search steps
- [ ] Includes executive summary
- [ ] Estimates duration
- [ ] Type-checks with mypy

**Gathering Agent**:
- [ ] Returns structured SearchResult
- [ ] Includes citations
- [ ] Handles API failures gracefully
- [ ] Executes in < 5s per search

**Synthesis Agent**:
- [ ] Produces coherent report
- [ ] Cites all sources
- [ ] Handles missing data
- [ ] Dynamic search tool works

**Verification Agent**:
- [ ] Validates citations
- [ ] Checks source reliability
- [ ] Identifies inconsistencies
- [ ] Returns structured validation

### Workflow Quality Gates

- [ ] Emits all expected events
- [ ] Completes in reasonable time
- [ ] Handles agent failures
- [ ] Resumes from checkpoints (DBOS)
- [ ] Tracks costs accurately

## Monitoring and Observability

### Logfire Metrics

Track key metrics per workflow:

```python
with logfire.span('research.workflow') as span:
    # Execution metrics
    span.set_attribute('num_searches', len(plan.search_steps))
    span.set_attribute('total_duration_seconds', duration)

    # Cost metrics
    span.set_attribute('total_input_tokens', total_input)
    span.set_attribute('total_output_tokens', total_output)
    span.set_attribute('total_cost_usd', total_cost)

    # Quality metrics
    span.set_attribute('num_findings', len(report.findings))
    span.set_attribute('num_sources', len(report.sources))
    span.set_attribute('validation_passed', validation.is_valid)
```

### Alerts

**Cost Alerts**:
- Workflow exceeds $10 USD
- Daily spend exceeds $100 USD

**Performance Alerts**:
- Workflow exceeds 10 minutes
- Search phase exceeds 30 seconds

**Quality Alerts**:
- Verification failure rate > 10%
- Less than 5 sources found

## Success Criteria

### Week 1 (Foundation)
- [ ] All Pydantic models defined with validation
- [ ] Domain events implemented
- [ ] 100% type coverage (mypy strict)
- [ ] Model tests passing

### Week 2 (Agents)
- [ ] 4 agents implemented
- [ ] Web search tool integrated
- [ ] Unit tests with TestModel
- [ ] 80%+ test coverage

### Week 3 (Workflow)
- [ ] End-to-end workflow functional
- [ ] Events emitted correctly
- [ ] Parallel execution working
- [ ] Integration tests passing

### Week 4 (Durability)
- [ ] DBOS integration complete
- [ ] Resume functionality tested
- [ ] Failure recovery validated
- [ ] Performance acceptable

### Week 5 (Production)
- [ ] Logfire instrumentation live
- [ ] Cost tracking operational
- [ ] Deployed to production
- [ ] Monitoring alerts configured

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| API rate limits | High | Medium | Implement exponential backoff, rate limiting |
| High LLM costs | High | Medium | Multi-model strategy, cost tracking, circuit breakers |
| Long workflow times | Medium | High | Parallel execution, progress updates via events |
| Citation hallucination | High | Medium | Verification agent, citation checking tool |
| DBOS learning curve | Medium | Low | Start without durability, add in Phase 2 |
| State management bugs | High | Medium | Comprehensive event tests, type safety |

## Future Enhancements

### Phase 6: Advanced Features (Future)

- **Multi-hop reasoning**: Iterative deepening based on findings
- **Document ingestion**: PDF/HTML parsing with LlamaParse
- **Knowledge graph**: Build entity relationships across research
- **Collaborative agents**: Multiple researchers on same topic
- **Human-in-the-loop**: Approval gates for sensitive research

### Scalability Path

**Current**: Single-service monolith
- DBOS-backed PostgreSQL
- Single deployment unit
- Handles 10-100 concurrent workflows

**Future**: Distributed microservices (if needed)
- Migrate to Temporal
- Agent services scale independently
- Handles 1000+ concurrent workflows

## References

- [durable-exec Source](https://github.com/pydantic/pydantic-stack-demo/tree/main/durable-exec)
- [Pydantic AI Documentation](https://ai.pydantic.dev/)
- [DBOS Documentation](https://docs.dbos.dev/)
- [Architecture Cosmos: Event-Driven Architecture](https://architecture-cosmos.com/event-driven-architecture)
- Project Skills: `llm-agentic-frameworks`, `arch-events`, `arch-ddd`, `dev-standards`

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-20 | Use Pydantic AI over LangChain | Type safety, FastAPI integration |
| 2026-01-20 | DBOS over Temporal initially | Simpler deployment for monolith |
| 2026-01-20 | Add verification phase | Research integrity requirement |
| 2026-01-20 | Multi-model strategy | Cost optimization (Gemini for parallel tasks) |
| 2026-01-20 | Event-driven state | Integration with existing arch-events pattern |
