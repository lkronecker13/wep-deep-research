# Three-Phase Deep Research Implementation Plan

## Overview

Implement a deep research service using Pydantic AI and durable execution, following a three-phase incremental approach:
- **Phase 1 (1-2 days)**: POC in `research/` folder - prove value with simple scripts
- **Phase 2 (1-2 weeks)**: Local service with FastAPI + DBOS + local PostgreSQL
- **Phase 3 (2-3 weeks)**: Production deployment with full observability and monitoring

**Key Principle**: Write production-quality agent code once in Phase 1, then promote it through phases by adding infrastructure, not rewriting.

---

## Phase 1: POC (Research Mode) - 1-2 Days

### Goal
Prove deep research agent value with 4-phase workflow (Planning → Gathering → Synthesis → Verification) in simplest possible execution context.

### Scope

**What Gets Built**:
- 4 Pydantic AI agents (all phases from start)
  - Planning Agent (Claude Sonnet 4.5, `output_type=ResearchPlan`)
  - Gathering Agent (Gemini 2.5 Flash, `builtin_tools=[WebSearchTool()]`, parallel execution)
  - Synthesis Agent (Claude Sonnet 4.5, `output_type=ResearchReport`)
  - Verification Agent (Claude Sonnet 4.5, `output_type=ValidationResult`)
- Core Pydantic models (ResearchPlan, SearchResult, ResearchReport, ValidationResult)
- Web search via PydanticAI's builtin `WebSearchTool()` (no custom tool code needed)
- Simple CLI script: `python research/run_research.py "query"`
- JSON output for results

**What Gets Skipped**:
- No database, no PostgreSQL, no DBOS
- No FastAPI, no REST endpoints
- No event system, no message bus
- No Logfire observability
- No error recovery or durability
- Minimal testing (manual validation only)

### File Structure

```
research/
├── run_research.py              # CLI entry point + workflow (~120 lines)
├── agents.py                    # All 4 agents defined (~80 lines)
├── models.py                    # 5 Pydantic models (~60 lines)
└── outputs/                     # JSON results directory
    └── research_YYYY-MM-DD_HH-MM-SS.json
```

**Total LOC**: ~260 lines of production-quality Python

**Note**: No custom `tools.py` needed - PydanticAI provides `WebSearchTool()` as a builtin tool that integrates directly with model providers (Anthropic, Google, OpenAI).

### Dependencies to Add

```toml
# Add to pyproject.toml [project.dependencies]
"pydantic-ai[anthropic,google]>=0.2.0",  # PydanticAI with provider support
```

**Note**: `WebSearchTool()` is a builtin that uses the model provider's native web search capability - no separate Tavily dependency needed for Phase 1. If you prefer Tavily, use `pydantic-ai-slim[tavily]` and the `tavily_search_tool()` common tool instead.

### Implementation Tasks

1. **Install dependencies** (15 min)
   ```bash
   # Edit pyproject.toml to add pydantic-ai[anthropic,google]
   uv sync
   ```

2. **Create `research/models.py`** (1 hour)
   - `SearchStep` - Individual search task (with `search_terms: str`)
   - `ResearchPlan` - Output from planning agent (with `web_search_steps: list[SearchStep]`)
   - `SearchResult` - Output from gathering agent
   - `ResearchReport` - Output from synthesis agent
   - `ValidationResult` - Output from verification agent

3. **Create `research/agents.py`** (2 hours)
   Following the PydanticAI pattern from [pydantic-stack-demo](https://github.com/pydantic/pydantic-stack-demo/tree/main/durable-exec):
   ```python
   from pydantic_ai import Agent
   from pydantic_ai.builtin_tools import WebSearchTool

   plan_agent = Agent(
       'anthropic:claude-sonnet-4-5',
       instructions="Create a research plan...",
       output_type=ResearchPlan,
       name='plan_agent',
   )

   gathering_agent = Agent(
       'google-gla:gemini-2.5-flash',
       instructions="Search for information...",
       builtin_tools=[WebSearchTool()],  # No custom tool needed!
       output_type=SearchResult,
       name='gathering_agent',
   )

   synthesis_agent = Agent(
       'anthropic:claude-sonnet-4-5',
       instructions="Synthesize research findings...",
       output_type=ResearchReport,
       name='synthesis_agent',
   )

   verification_agent = Agent(
       'anthropic:claude-sonnet-4-5',
       instructions="Verify and validate...",
       output_type=ValidationResult,
       name='verification_agent',
   )
   ```

4. **Create `research/run_research.py`** (1.5 hours)
   - CLI argument parsing
   - 4-phase workflow orchestration
   - Parallel execution of searches using `asyncio.TaskGroup`
   - JSON output to `outputs/` directory
   - Progress printing to console

5. **Manual testing and iteration** (1-2 hours)
   - Test with example queries
   - Refine agent prompts based on output quality
   - Validate parallel execution works
   - Test edge cases (empty results, API failures)

### Environment Setup

```bash
# Set API keys in .env or export
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_AI_API_KEY="..."
export TAVILY_API_KEY="tvly-..."

# Run research
python research/run_research.py "What are the latest developments in quantum computing?"
```

### Success Criteria

- [ ] CLI completes end-to-end 4-phase workflow
- [ ] JSON output contains plan, search results, report, validation
- [ ] Parallel execution reduces total time vs sequential
- [ ] Typical query completes in <2 minutes
- [ ] Output quality demonstrates research value to stakeholders
- [ ] Validation phase catches source quality issues

**Decision Point**: If POC demonstrates value, proceed to Phase 2. If output quality is poor, iterate on prompts/models before adding infrastructure.

---

## Phase 2: Local Service - 1-2 Weeks

### Goal
Evolve research scripts into locally running service with FastAPI, DBOS durability, and local PostgreSQL - without cloud deployment complexity.

### Migration Strategy

**What Moves from Phase 1 (unchanged)**:
- All 4 agent definitions → `src/agents/*.py` (split into 4 files, same code)
- All 5 Pydantic models → `src/models/*.py` (split into 3 files, same code)
- 4-phase workflow logic (same sequence, wrapped with DBOS)

**What Gets Added**:
- `DBOSAgent` wrappers around PydanticAI agents (from `pydantic_ai.ext.dbos`)
- FastAPI service with `/research` endpoints
- Local PostgreSQL database (Docker Compose)
- DBOS-wrapped workflow for durability using `@DBOS.workflow()`
- `DBOS.start_workflow_async()` for durable parallel execution
- Domain events emitted at each phase
- Repository layer for persistence
- Comprehensive test suite (80%+ coverage)

**Key Pattern - DBOSAgent Wrapper** (from [pydantic-stack-demo](https://github.com/pydantic/pydantic-stack-demo/tree/main/durable-exec)):
```python
from pydantic_ai.ext.dbos import DBOSAgent
from dbos import DBOS

# Wrap PydanticAI agents with DBOSAgent for durability
plan_agent = Agent(...)  # PydanticAI agent (unchanged from Phase 1)
dbos_plan_agent = DBOSAgent(plan_agent)  # DBOS wrapper

@DBOS.workflow()
async def deep_research(query: str):
    # Use wrapped agents - they checkpoint automatically
    plan = await dbos_plan_agent.run(query)

    # Durable parallel execution (not asyncio.TaskGroup)
    search_handles = [
        await DBOS.start_workflow_async(search_workflow, step.search_terms)
        for step in plan.data.web_search_steps
    ]
    results = [await handle.get_result() for handle in search_handles]

    report = await dbos_synthesis_agent.run(results)
    validation = await dbos_verification_agent.run(report)
    return validation
```

### File Structure

```
src/
├── agents/
│   ├── __init__.py
│   ├── planning_agent.py        # Copied from research/agents.py
│   ├── gathering_agent.py       # Copied from research/agents.py (with WebSearchTool builtin)
│   ├── synthesis_agent.py       # Copied from research/agents.py
│   ├── verification_agent.py    # Copied from research/agents.py
│   └── dbos_agents.py           # DBOSAgent wrappers for all 4 agents
│
├── models/
│   ├── __init__.py
│   ├── research_plan.py         # ResearchPlan, SearchStep
│   ├── search_result.py         # SearchResult
│   └── research_report.py       # ResearchReport, ValidationResult
│
├── workflows/
│   ├── __init__.py
│   ├── deep_research.py         # Base workflow (same logic as run_research.py)
│   ├── deep_research_dbos.py    # DBOS-wrapped version with @DBOS.workflow()
│   └── search_workflow.py       # Individual search workflow for parallel execution
│
├── events/
│   ├── __init__.py
│   └── research_events.py       # ResearchInitiated, PlanCreated, etc.
│
├── api/
│   ├── __init__.py
│   ├── routes.py                # FastAPI endpoints
│   └── schemas.py               # Request/response models
│
├── repositories/
│   ├── __init__.py
│   └── research_repository.py   # Database persistence
│
├── database/
│   ├── __init__.py
│   ├── connection.py            # SQLAlchemy setup
│   └── models.py                # ORM models
│
├── logging.py                   # Already exists - reuse!
└── main.py                      # FastAPI app entry point

tests/
├── test_agents/                 # New: 4 agent test files
├── test_workflows/              # New: workflow tests
├── test_api/                    # New: API endpoint tests
└── test_logging.py              # Already exists - keep!

docker-compose.yml               # Local PostgreSQL
alembic/                         # Database migrations
research/                        # Keep Phase 1 POC for reference
```

### Dependencies to Add

```toml
# Add to pyproject.toml [project.dependencies]
"pydantic-ai[anthropic,google,dbos]>=0.2.0",  # Adds DBOSAgent support
"fastapi>=0.115.0",
"uvicorn>=0.32.0",
"sqlalchemy>=2.0.0",
"asyncpg>=0.30.0",
"dbos>=1.0.0",
"alembic>=1.13.0",
```

### Implementation Tasks

**Week 1: Core Migration**

1. **Restructure files** (Day 1, 4 hours)
   - Create src/ folder structure
   - Copy and split `research/agents.py` → 4 files in `src/agents/`
   - Copy and split `research/models.py` → 3 files in `src/models/`
   - Create `src/agents/dbos_agents.py` with DBOSAgent wrappers
   - Update imports (only change: import paths)

2. **Add domain events** (Day 1, 2 hours)
   - Create `src/events/research_events.py`
   - Define: ResearchInitiated, PlanCreated, SearchCompleted, ReportGenerated, ResearchCompleted
   - Use dataclasses with timestamps

3. **Add local database** (Day 2, 4 hours)
   - Create `docker-compose.yml` for PostgreSQL 16
   - Create `src/database/models.py` (SQLAlchemy ORM)
   - Create `src/database/connection.py` (session factory)
   - Initialize Alembic: `alembic init alembic`
   - Create first migration: research_requests and research_results tables

4. **Add FastAPI layer** (Day 2-3, 6 hours)
   - Create `src/api/routes.py`:
     - POST /research - Start workflow
     - GET /research/{id} - Get status
     - GET /research/{id}/result - Get final result
   - Create `src/api/schemas.py` (request/response models)
   - Create `src/main.py` (FastAPI app with middleware)

5. **Add DBOS workflow wrapper** (Day 3-4, 6 hours)
   - Create `src/workflows/deep_research.py` (base workflow)
   - Create `src/workflows/search_workflow.py` (individual search for parallel execution)
   - Create `src/workflows/deep_research_dbos.py` (DBOS-wrapped):
     - Use `DBOSAgent` wrappers from `pydantic_ai.ext.dbos`
     - Decorate with `@DBOS.workflow()`
     - Use `DBOS.start_workflow_async()` for durable parallel searches
   - Test workflow resumption after simulated failure

6. **Add repository layer** (Day 4, 4 hours)
   - Create `src/repositories/research_repository.py`
   - Implement CRUD operations
   - Follow DomainSession protocol pattern

**Week 2: Testing and Validation**

7. **Write agent tests** (Day 5-6, 8 hours)
   - Use `pydantic_ai.models.test.TestModel` for fast testing
   - Test naming: `test__<what>__<expected>`
   - Target: 80%+ coverage on agents
   - Tests in `tests/test_agents/`

8. **Write workflow tests** (Day 7, 4 hours)
   - Test base workflow in `tests/test_workflows/`
   - Test DBOS resumption capability
   - Test event emission

9. **Write API tests** (Day 7-8, 4 hours)
   - Test all endpoints in `tests/test_api/`
   - Mock DBOS workflows for fast tests
   - Test error handling

10. **Integration testing** (Day 9, 4 hours)
    - End-to-end workflow execution
    - Database persistence validation
    - Event emission verification

11. **Run validation** (Day 10, 2 hours)
    ```bash
    just validate-branch  # Must pass: format, lint, type-check, test (80%+)
    ```

### Local Development Workflow

```bash
# Start PostgreSQL
docker-compose up -d

# Run migrations
alembic upgrade head

# Start FastAPI service
uvicorn src.main:app --reload

# Test endpoint
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the latest developments in quantum computing?"}'

# View logs (using existing src/logging.py)
# Logs appear in structured JSON format via stdout
```

### Success Criteria

- [ ] All endpoints functional and tested
- [ ] Research results persisted to PostgreSQL
- [ ] DBOS workflow resumes after simulated failure
- [ ] Test coverage ≥80% on new code
- [ ] `just validate-branch` passes cleanly
- [ ] Domain events emitted at each phase transition
- [ ] Original POC agent code works unchanged in new structure

**Decision Point**: If local service runs reliably and meets performance targets, proceed to Phase 3.

---

## Phase 3: Production - 2-3 Weeks

### Goal
Deploy robust production service to GCP with full observability, cost tracking, monitoring, and production-grade error handling.

### What Changes

**Additions Only (agent code still unchanged from Phase 1!)**:
- Logfire instrumentation for observability
- Cost tracking middleware (token usage per workflow)
- GCP Cloud Run deployment configuration
- Cloud SQL PostgreSQL (production database)
- Monitoring dashboards and alerts
- API authentication (API keys)
- Rate limiting middleware
- Production error handling and circuit breakers
- Comprehensive integration and load tests

### File Structure Changes

```
src/
├── (all Phase 2 files remain)
│
├── observability/               # NEW
│   ├── __init__.py
│   ├── logfire_config.py       # Logfire setup
│   └── cost_tracking.py        # Token usage tracking
│
├── middleware/                  # NEW
│   ├── __init__.py
│   ├── authentication.py       # API key validation
│   └── rate_limiting.py        # Rate limit enforcement
│
├── config/                      # NEW
│   ├── __init__.py
│   └── settings.py             # Pydantic settings (env vars)
│
└── main.py                      # Enhanced with middleware

infra/                           # NEW
├── terraform/
│   ├── cloud_run.tf
│   ├── cloud_sql.tf
│   └── variables.tf
└── Dockerfile

.github/workflows/
├── ci.yml                       # Already exists
└── deploy-cloud-run.yml         # NEW: CD pipeline

tests/
├── (all Phase 2 tests remain)
├── test_observability/
│   └── test_cost_tracking.py
└── test_integration/
    └── test_load.py
```

### Dependencies to Add

```toml
# Add to pyproject.toml [project.dependencies]
"logfire>=0.59.0",
"slowapi>=0.1.9",                       # Rate limiting
"google-cloud-secret-manager>=2.20.0",
"sentry-sdk[fastapi]>=2.0.0",
```

### Implementation Tasks

**Week 1: Observability and Configuration**

1. **Logfire integration** (Day 1-2, 6 hours)
   - Create `src/observability/logfire_config.py`
   - Add `logfire.configure()` and `logfire.instrument_pydantic_ai()`
   - Update `src/workflows/deep_research_dbos.py` with `logfire.span()` wrappers
   - Agents automatically traced (no code changes needed)

2. **Cost tracking** (Day 2, 4 hours)
   - Create `src/observability/cost_tracking.py`
   - Track token usage per agent execution
   - Log costs to Logfire metrics
   - Add cost limits per workflow

3. **Production settings** (Day 3, 4 hours)
   - Create `src/config/settings.py` (Pydantic Settings)
   - Load API keys from environment variables
   - Configure log levels, rate limits, cost thresholds

4. **Authentication middleware** (Day 3-4, 4 hours)
   - Create `src/middleware/authentication.py`
   - API key validation
   - Integrate with FastAPI dependencies

5. **Rate limiting** (Day 4, 4 hours)
   - Create `src/middleware/rate_limiting.py`
   - Use SlowAPI for per-key rate limits
   - Configure limits: 10 requests/minute

**Week 2: Infrastructure and Deployment**

6. **Terraform infrastructure** (Day 5-7, 12 hours)
   - Create `infra/terraform/cloud_run.tf` (service definition)
   - Create `infra/terraform/cloud_sql.tf` (PostgreSQL instance)
   - Configure secrets in Secret Manager
   - Set up VPC networking

7. **Dockerfile** (Day 7, 4 hours)
   - Multi-stage build
   - Install dependencies with uv
   - Configure health check endpoint
   - Optimize image size

8. **CI/CD pipeline** (Day 8, 4 hours)
   - Create `.github/workflows/deploy-cloud-run.yml`
   - Build and push Docker image to GCR
   - Deploy to Cloud Run on merge to main
   - Run database migrations

**Week 3: Production Hardening**

9. **Monitoring setup** (Day 9-10, 8 hours)
   - Configure Logfire dashboards (workflow duration, costs, errors)
   - Set up GCP Monitoring alerts (cost threshold, error rate, latency)
   - Integrate Sentry for exception tracking

10. **Load testing** (Day 11, 4 hours)
    - Create `tests/test_integration/test_load.py`
    - Test 50 concurrent workflows
    - Validate P95 latency < 60s
    - Test error rates under load

11. **Production deployment** (Day 12-13, 8 hours)
    - Deploy to staging environment
    - Run end-to-end integration tests
    - Deploy to production with canary rollout
    - Monitor for 24 hours

12. **Documentation** (Day 14, 4 hours)
    - Production runbook (troubleshooting, rollback procedures)
    - API documentation (OpenAPI/Swagger)
    - Update README with production usage

### Production Deployment

```bash
# Build and push image
docker build -t gcr.io/PROJECT_ID/deep-research:latest .
docker push gcr.io/PROJECT_ID/deep-research:latest

# Apply infrastructure
cd infra/terraform
terraform init
terraform apply

# Deploy via GitHub Actions (automatic on merge to main)
git push origin main
```

### Success Criteria

- [ ] Service deployed on Cloud Run with Cloud SQL
- [ ] Logfire dashboards showing all metrics (duration, costs, errors)
- [ ] Per-workflow costs logged accurately
- [ ] P95 latency < 60s for typical workflows
- [ ] 99.5% uptime over 1 week
- [ ] API authentication and rate limiting enforced
- [ ] Cost and performance alerts configured and tested
- [ ] Load tested: handles 50 concurrent workflows
- [ ] Production runbook and troubleshooting guide complete

---

## Code Reuse Summary

### Components Unchanged Across All Phases

**Agent Definitions** (Phase 1 → Phase 2 → Phase 3):
- Planning Agent: model, instructions, output_type
- Gathering Agent: model, builtin_tools=[WebSearchTool()], output_type
- Synthesis Agent: model, instructions, output_type
- Verification Agent: model, instructions, output_type

**Pydantic Models** (Phase 1 → Phase 2 → Phase 3):
- ResearchPlan, SearchStep, SearchResult, ResearchReport, ValidationResult

**Tools** (Phase 1 → Phase 2 → Phase 3):
- `WebSearchTool()` builtin - no custom code to maintain!

**Core Workflow Logic**:

Phase 1 (asyncio):
```python
plan = await plan_agent.run(query)
async with asyncio.TaskGroup() as tg:
    tasks = [tg.create_task(gathering_agent.run(step.search_terms)) for step in plan.data.web_search_steps]
results = [task.result().data for task in tasks]
report = await synthesis_agent.run(synthesis_prompt)
validation = await verification_agent.run(validation_prompt)
```

Phase 2+ (DBOS - same logic, durable execution):
```python
@DBOS.workflow()
async def deep_research(query: str):
    plan = await dbos_plan_agent.run(query)
    search_handles = [
        await DBOS.start_workflow_async(search_workflow, step.search_terms)
        for step in plan.data.web_search_steps
    ]
    results = [await handle.get_result() for handle in search_handles]
    report = await dbos_synthesis_agent.run(results)
    validation = await dbos_verification_agent.run(report)
    return validation
```

**Reuse Percentage**: ~70% of Phase 1 agent code moves to production unchanged. Phase 2 adds DBOSAgent wrappers (thin layer), not logic rewrites.

---

## Decision Points

### Proceed to Phase 2 If:
- ✓ POC demonstrates accurate research results
- ✓ 4-phase workflow completes successfully
- ✓ Parallel execution works reliably
- ✓ Stakeholders see value in deep research capability
- ✓ API costs per workflow are acceptable (<$5)
- ✓ Performance is reasonable (<3 minutes for typical query)

### Proceed to Phase 3 If:
- ✓ Local service handles concurrent workflows
- ✓ DBOS durability tested and working
- ✓ Test coverage ≥80% and all tests pass
- ✓ API performance meets targets (P95 < 60s)
- ✓ Business case approved for production deployment
- ✓ Security review completed (if required)

### Abort/Iterate If:
- ✗ Agent output quality is poor → Iterate on prompts/models
- ✗ API costs exceed budget ($10+ per workflow) → Optimize model usage
- ✗ Performance unacceptable (>5 minutes) → Profile and optimize
- ✗ DBOS durability unreliable → Consider Temporal or debug further
- ✗ Test coverage fails to reach 80% → Write more tests

---

## Testing Strategy

### Test Naming Convention
All tests follow: `test__<what>__<expected>`

**Examples**:
```python
def test__plan_agent__creates_valid_plan()
def test__gathering_agent__returns_search_results()
def test__parallel_search__executes_faster_than_sequential()
def test__dbos_workflow__resumes_after_failure()
def test__api_endpoint__returns_workflow_id()
def test__cost_tracking__logs_all_agent_costs()
```

### Coverage Requirements
- Phase 1: No coverage requirements (manual validation)
- Phase 2: 80% minimum (`just test` enforces)
- Phase 3: 80% minimum + integration test suite

### Validation Before Commits
**Phase 1**: No git commits (research folder is exploratory)

**Phase 2 & 3**: Required before every commit
```bash
just validate-branch  # Runs: format, lint, type-check, test
```

---

## Git Workflow

**Phase 1**: No branching (work directly in research/ folder)

**Phase 2 & 3**: Feature branches for all work
```bash
git checkout -b feat/add-fastapi-endpoints
# Make changes
just validate-branch
git add .
git commit -m "feat: add research API endpoints"
gh pr create --title "feat: Add research API endpoints" --body "..."
# Wait for approval, then merge
```

**Critical**: No direct commits to main. All changes via pull requests.

---

## Critical Files Reference

The following files are essential for implementation:

**External References**:
- [pydantic-stack-demo/durable-exec](https://github.com/pydantic/pydantic-stack-demo/tree/main/durable-exec) - **Reference implementation** for PydanticAI + DBOS patterns
- [PydanticAI Built-in Tools](https://ai.pydantic.dev/builtin-tools/) - WebSearchTool documentation
- [PydanticAI DBOS Extension](https://ai.pydantic.dev/api/ext/dbos/) - DBOSAgent wrapper documentation

**Local Files**:
- `docs/AGENT_ARCHITECTURE.md` - Agent patterns and 4-phase workflow design
- `docs/IMPLEMENTATION_GUIDE.md` - Code examples for agents, tools, DBOS, testing
- `docs/ARCHITECTURE_DECISIONS.md` - Technology stack rationale and trade-offs
- `src/logging.py` - Production logging (reuse in Phase 2/3)
- `pyproject.toml` - Dependencies configuration
- `justfile` - Build automation (validate-branch command)

---

## Verification

### Phase 1 Verification
```bash
# Run POC
python research/run_research.py "What are the latest developments in quantum computing?"

# Check output
cat research/outputs/research_*.json | jq '.report.key_findings | length'
# Should show multiple findings

# Verify validation ran
cat research/outputs/research_*.json | jq '.validation.is_valid'
# Should show true/false with confidence score
```

### Phase 2 Verification
```bash
# Start local service
docker-compose up -d
uvicorn src.main:app --reload

# Test endpoint
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "Test query"}' | jq

# Check database
docker exec -it postgres psql -U postgres -d deep_research -c "SELECT * FROM research_requests;"

# Run full validation
just validate-branch
# Must show: ✓ format, ✓ lint, ✓ type-check, ✓ test (80%+)
```

### Phase 3 Verification
```bash
# Check deployment
gcloud run services list | grep deep-research

# Test production endpoint
curl -X POST https://deep-research-XXX.run.app/research \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "Test query"}'

# Check Logfire dashboard
open https://logfire.pydantic.dev

# Verify alerts configured
gcloud alpha monitoring policies list
```

---

## Timeline Summary

| Phase | Duration | Deliverable | Key Milestone |
|-------|----------|-------------|---------------|
| **Phase 1** | 1-2 days | POC scripts in research/ | Working 4-phase research demo |
| **Phase 2** | 1-2 weeks | Local FastAPI + DBOS service | API endpoints + durable workflows |
| **Phase 3** | 2-3 weeks | Production GCP deployment | Cloud Run service with monitoring |

**Total Estimated Time**: 4-6 weeks from start to production deployment

---

## Next Steps

1. Review this plan with stakeholders
2. Obtain approval for Phase 1 implementation
3. Set up API keys (Anthropic, Google AI, Tavily)
4. Begin Phase 1: Create research/ folder and implement 4 agents
5. Demo POC to validate approach before proceeding to Phase 2
