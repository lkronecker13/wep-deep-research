# ADR-001: Deep Research Service Architecture

## Status
Accepted

## Context
Building an AI-powered deep research system that conducts structured, comprehensive research using specialized AI agents. The system needs to handle complex multi-phase research tasks, parallel execution of searches, and provide quality validation of results.

## Decision
Implement a **four-phase multi-agent workflow** using **PydanticAI** with a **multi-model strategy** (Claude + Gemini) for cost-optimized, high-quality research.

## Technical Specification

### Architecture
Four specialized agents orchestrated in sequence:
1. **Planning Agent** - Creates research strategy (1-5 search steps)
2. **Gathering Agent** - Executes web searches in parallel
3. **Synthesis Agent** - Combines findings into coherent report
4. **Verification Agent** - Validates quality and consistency

### Technology Stack
- **Framework**: PydanticAI v0.2.0+ for type-safe agent framework
- **Models**:
  - Anthropic Claude Sonnet 4.5 (planning, synthesis, verification)
  - Google Gemini 2.5 Flash (parallel gathering - 10x cheaper)
- **Web Search**: PydanticAI built-in `WebSearchTool`
- **Validation**: Pydantic v2 for structured data models
- **Execution**: Async/await with `asyncio.TaskGroup` for parallel searches

### Data Flow
```
User Query → Planning Agent → Search Steps → Gathering Agent (parallel) →
Search Results → Synthesis Agent → Research Report → Verification Agent →
Validated Report + Confidence Score
```

### Multi-Model Strategy
- **Claude Sonnet 4.5**: Complex reasoning, strategic thinking, critical evaluation
- **Gemini 2.5 Flash**: Fast, cost-effective parallel searches ($0.10/1M tokens vs $3/1M)
- **Cost per workflow**: ~$0.30-$0.50
- **Performance**: < 2 minutes for typical queries

## Consequences

### Pros
- Type safety catches errors early (Pydantic validation)
- Cost-optimized via strategic model selection
- 5-10x faster via parallel execution
- Quality validation built into workflow
- Clean separation of concerns (specialized agents)
- Extensible architecture for future phases

### Cons
- Requires two API keys (Anthropic + Google)
- Multi-model complexity vs single-provider simplicity
- No durability/resumption (deferred; stateless API sufficient for current use)

## Alternatives Considered

### Single Model (Claude only)
- **Rejected**: Higher costs, no benefit from Gemini's cost-effectiveness for parallel tasks

### Synchronous Execution
- **Rejected**: 5-10x slower, poor user experience

### LangChain instead of PydanticAI
- **Rejected**: Less type-safe, heavier dependencies, more complex abstractions

## Implementation Phases

### Phase 1: POC ✅ (Complete)
- Pure async workflow in `research/` folder
- CLI interface with JSON output
- No persistence or durability

### Phase 2: Production Service ✅ (Complete)
- FastAPI REST API with `/research` endpoint
- Production 4-phase workflow in `src/workflow.py`
- Structured error handling with sanitized client messages
- Health check endpoints (`/health`, `/health/liveness`, `/health/readiness`)
- Comprehensive test suite (161 tests, 86% coverage)
- **Deferred**: DBOS durability, PostgreSQL persistence, repository pattern (stateless API sufficient)

### Phase 2.5: SSE Streaming + Demo Mode ✅ (Complete)
- `POST /research/stream` with real-time SSE progress events
- Demo mode (`?demo=true`) for frontend testing without API costs
- Docker containerization with production-ready Gunicorn config
- LLM-as-a-Judge evaluation system with Arize Phoenix tracing

### Phase 3: Production Deployment (Planned)
- GCP Cloud Run deployment
- Observability and cost tracking
- API authentication and rate limiting
- Monitoring dashboards and alerts

## Non-Functional Requirements
- **Performance**: < 2 minutes for typical research queries
- **Cost**: < $0.50 per workflow
- **Reliability**: Type safety via Pydantic, validation phase for quality
- **Scalability**: Async parallel execution, Phase 2 adds durable workflows

## Integration Points
- **Consumes**:
  - Environment variables (ANTHROPIC_API_KEY, GEMINI_API_KEY)
  - Research queries via CLI (Phase 1) or API (Phase 2+)
- **Provides**:
  - JSON research reports with citations
  - Quality validation scores
  - REST API endpoints (`/research`, `/research/stream`)
  - SSE event streams for real-time progress

## Security
- API keys via environment variables (no hardcoded secrets)
- No user data persistence in Phase 1
- Phase 2+ adds database security, API authentication

## References
- [PydanticAI Documentation](https://ai.pydantic.dev/)
- [Pydantic Stack Demo - durable-exec](https://github.com/pydantic/pydantic-stack-demo/tree/main/durable-exec)
- Project docs: `docs/EXECUTIVE_BRIEF.md`, `README.md`
