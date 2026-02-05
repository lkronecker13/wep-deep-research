# Deep Research Service

> AI-powered deep research using multi-agent workflows

An intelligent research system that conducts structured, comprehensive research using specialized AI agents. Built with [PydanticAI](https://ai.pydantic.dev/) for [Wepoint](https://www.wepoint.com/) as an internal research tool.

**Current Status:** Phase 2.5 Complete ✅ (Production API with SSE streaming + Demo mode)

## What It Does

Conducts deep research by orchestrating four specialized AI agents through a structured workflow:

```
┌─────────────┐      ┌──────────────┐      ┌───────────┐      ┌──────────────┐
│  Planning   │ ───> │  Gathering   │ ───> │ Synthesis │ ───> │ Verification │
│   Agent     │      │  (Parallel)  │      │   Agent   │      │    Agent     │
│             │      │              │      │           │      │              │
│   Claude    │      │    Gemini    │      │  Claude   │      │   Claude     │
└─────────────┘      └──────────────┘      └───────────┘      └──────────────┘
      │                     │                     │                    │
      v                     v                     v                    v
  Research Plan       Web Searches        Research Report      Quality Check
  (1-5 steps)         (Parallel)          (Synthesized)        (Validated)
```

**Example:** Ask "What are the latest developments in quantum computing?" and receive a comprehensive research report with citations, key findings, and quality validation—all in under 2 minutes.

---

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- API keys:
  - [Anthropic API key](https://console.anthropic.com/) (Claude)
  - [Google AI API key](https://aistudio.google.com/apikey) (Gemini)

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd wep-deep-research

# Set up environment
just init

# Configure API keys
export ANTHROPIC_API_KEY="sk-ant-..."
export GEMINI_API_KEY="..."
```

### Option 1: REST API (Production)

```bash
# Start FastAPI server
just serve

# In another terminal, execute research via API
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the latest developments in quantum computing?"}'
```

**Response:** Full `ResearchResult` JSON with plan, search results, report, validation, and timings (30-180s)

### Option 2: SSE Streaming (Real-time Progress)

```bash
# Stream real-time progress updates
curl -N -X POST http://localhost:8000/research/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "What is quantum computing?"}'

# Output: Server-Sent Events with phase_start, phase_complete, complete events
```

**Response:** SSE stream with real-time updates (planning → gathering → synthesis → verification → complete)

### Option 3: Demo Mode (Frontend Testing)

```bash
# Test with instant hardcoded responses (no API costs)
curl -X POST "http://localhost:8000/research?demo=true" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'

# Or with streaming
curl -N -X POST "http://localhost:8000/research/stream?demo=true" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'
```

**Response:** Instant quantum computing research example (no API keys required)

### Option 4: CLI (POC Reference)

```bash
# Run research via CLI
python -m research.run_research "What are the latest developments in quantum computing?"

# Output saved to research/outputs/research_YYYY-MM-DD_HH-MM-SS.json
cat research/outputs/research_*.json | jq '.report.key_findings'
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/research` | POST | Execute research workflow (30-180s), supports `?demo=true` |
| `/research/stream` | POST | SSE streaming with real-time progress updates, supports `?demo=true` |
| `/health` | GET | Service health check |
| `/health/liveness` | GET | Kubernetes liveness probe |
| `/health/readiness` | GET | Kubernetes readiness probe |

**Request body:**
```json
{"query": "Your research question here"}
```

**Response:** `ResearchResult` with plan, search_results, report, validation, timings

**Demo Mode:** Add `?demo=true` to either endpoint for instant hardcoded responses (frontend testing without API costs)

---

## How It Works

### 4-Phase Workflow

#### 1. Planning Agent (Claude Sonnet 4.5)
**Input:** Research query
**Output:** Structured research plan with 1-5 targeted search steps

Creates a strategic research plan by:
- Breaking down the query into logical search components
- Identifying different angles to explore
- Prioritizing depth over breadth
- Providing clear purpose for each search step

#### 2. Gathering Agent (Gemini 2.5 Flash)
**Input:** Search steps from planning phase
**Output:** Search results with citations and key findings

Executes web searches in parallel using PydanticAI's built-in `WebSearchTool`:
- Searches 1-5 queries simultaneously (5x faster than sequential)
- Extracts facts, statistics, and insights
- Collects source URLs for citation
- Cost-optimized: Gemini Flash is 10x cheaper than Claude

#### 3. Synthesis Agent (Claude Sonnet 4.5)
**Input:** All search results + original query
**Output:** Coherent research report

Combines findings into a structured report:
- Identifies patterns and themes across sources
- Presents clear key findings
- Maintains complete source attribution
- Acknowledges limitations and gaps

#### 4. Verification Agent (Claude Sonnet 4.5)
**Input:** Synthesized research report
**Output:** Quality validation with confidence score

Validates research integrity:
- Checks internal consistency (no contradictions)
- Assesses source quality and diversity
- Verifies all claims are backed by sources
- Provides confidence score (0.0-1.0)
- Recommends improvements if needed

### Multi-Model Strategy

We use different LLM models optimized for different tasks:

| Phase | Model | Why? |
|-------|-------|------|
| Planning | Claude Sonnet 4.5 | Complex reasoning, strategic thinking |
| Gathering | Gemini 2.5 Flash | Fast parallel execution, 10x cheaper |
| Synthesis | Claude Sonnet 4.5 | Deep analysis, coherent writing |
| Verification | Claude Sonnet 4.5 | Critical evaluation, fact-checking |

**Cost optimization:** A typical research workflow costs ~$0.30-$0.50 by using Gemini for parallel searches while reserving Claude for reasoning-heavy tasks.

### Example Output Structure

```json
{
  "query": "What are the latest developments in quantum computing?",
  "plan": {
    "executive_summary": "Research quantum computing breakthroughs...",
    "web_search_steps": [
      {
        "search_terms": "quantum computing breakthroughs 2025",
        "purpose": "Identify recent major advances"
      }
    ]
  },
  "search_results": [
    {
      "query": "quantum computing breakthroughs 2025",
      "findings": ["IBM announces 1000+ qubit processor...", "..."],
      "sources": ["https://...", "..."]
    }
  ],
  "report": {
    "title": "Latest Developments in Quantum Computing",
    "summary": "Quantum computing has seen significant advances...",
    "key_findings": [
      "IBM released a 1000+ qubit quantum processor",
      "Google achieved quantum error correction milestone"
    ],
    "sources": ["https://...", "..."],
    "limitations": "Most advances are still in research phase..."
  },
  "validation": {
    "is_valid": true,
    "confidence_score": 0.85,
    "issues_found": [],
    "recommendations": ["Consider adding more diverse sources"]
  }
}
```

---

## Architecture

### Technology Stack

- **Framework:** [PydanticAI](https://ai.pydantic.dev/) - Type-safe AI agent framework
- **Models:** Anthropic Claude Sonnet 4.5 + Google Gemini 2.5 Flash
- **Web Search:** PydanticAI built-in `WebSearchTool` (uses model provider's native search)
- **Validation:** Pydantic v2 for type-safe data models
- **Execution:** Async/await with parallel task execution (`asyncio.TaskGroup`)

### Project Structure

```
wep-deep-research/
├── research/                    # Phase 1 POC (reference implementation)
│   ├── models.py                # Pydantic models (5 models)
│   ├── agents.py                # PydanticAI agents (4 agents)
│   ├── run_research.py          # CLI + workflow orchestration
│   └── outputs/                 # JSON results (gitignored)
│
├── src/                         # Production application (Phase 2 ✅)
│   ├── agents.py                # 4 PydanticAI agents (plan, gather, synthesize, verify)
│   ├── models.py                # Pydantic models + PhaseTimings, ResearchResult
│   ├── workflow.py              # Production 4-phase async pipeline (156 lines)
│   ├── server.py                # FastAPI app with /research endpoint (106 lines)
│   ├── exceptions.py            # Custom exceptions (PlanningError, GatheringError, etc.)
│   └── logging.py               # Production logging (structlog)
│
├── tests/                       # Test suite (95% coverage)
│   ├── test_agents.py           # Agent creation tests
│   ├── test_logging.py          # Logging tests
│   ├── test_models.py           # Model validation tests
│   ├── test_workflow.py         # Workflow pipeline tests (232 lines)
│   └── test_server.py           # API endpoint tests (189 lines)
│
├── docs/                        # Technical documentation
│   ├── AGENT_ARCHITECTURE.md    # Agent design patterns
│   ├── ARCHITECTURE_DECISIONS.md # ADRs for key decisions
│   ├── IMPLEMENTATION_GUIDE.md  # Practical implementation guide
│   └── research/                # Research documents
│       └── gcp-cloud-run-sse-limits.md  # GCP SSE deployment guide
│
├── pyproject.toml               # Dependencies and config
├── justfile                     # Development automation
├── SSE_STREAMING_PLAN.md        # Phase 2.5 implementation plan
└── README.md                    # This file
```

### Key Design Decisions

1. **Multi-agent workflow:** Separates concerns (planning, gathering, synthesis, verification) for better quality and maintainability

2. **Parallel execution:** Independent searches run concurrently using `asyncio.TaskGroup`, reducing total time by 5-10x

3. **Type safety:** All data validated with Pydantic models—catches errors at runtime before they propagate

4. **Lazy initialization:** Agents created on-demand to avoid requiring API keys for code quality tools

5. **Cost optimization:** Strategic model selection balances quality and cost (Gemini for volume, Claude for reasoning)

---

## Development

### Environment Setup

```bash
# Set up Python 3.12+ environment
just init

# Sync dependencies
just sync
```

### Code Quality

```bash
# Format code
just format

# Lint and auto-fix issues
just lint

# Type check with mypy
just type-check

# Run tests (80% coverage required)
just test

# Run all quality checks
just validate-branch
```

### Development Workflow

The project follows production-first development practices:

- **Type safety:** Strict mypy type checking on all code
- **Test coverage:** 80% minimum coverage enforced
- **Code quality:** Automated formatting (ruff) and linting
- **Git workflow:** Feature branches with PR reviews (no direct commits to main)

### Testing

```bash
# Run standard test suite (excludes integration tests)
just test

# Run only unit tests
just test-unit

# Run all tests including integration
just test-all
```

**Test naming convention:** All tests follow `test__<what>__<expected>` pattern

Example: `test__plan_agent__creates_valid_research_plan`

---

## Roadmap

### ✅ Phase 1: POC (Complete)

**Status:** Working prototype
**Location:** `research/` folder
**Features:**
- 4 specialized AI agents (planning, gathering, synthesis, verification)
- Async parallel execution for searches
- Type-safe Pydantic models
- CLI interface with JSON output
- Multi-model cost optimization

**Typical performance:** Research query completes in < 2 minutes, costs $0.30-$0.50

### ✅ Phase 2: Production Service (Complete)

**Status:** Production-ready FastAPI service
**Location:** `src/` folder
**Completed:**
- ✅ FastAPI REST API with `/research` endpoint
- ✅ Production 4-phase workflow (`src/workflow.py`)
- ✅ Structured error handling with sanitized client messages
- ✅ Health check endpoints (`/health`, `/health/liveness`, `/health/readiness`)
- ✅ Comprehensive test suite (161 tests, 86% coverage)
- ✅ Type-safe models (PhaseTimings, ResearchResult)
- ✅ Production logging with correlation IDs
- ✅ OpenAPI specification with complete API documentation

**Deferred to Phase 3:**
- DBOS durability (add if needed for long workflows)
- Repository pattern (stateless API doesn't require)
- Domain events (simpler without for now)

**API Usage:**
```bash
# Start server
just serve

# Execute research workflow
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What is quantum computing?"}'

# Returns ResearchResult JSON (30-180s)
```

### ✅ Phase 2.5: SSE Streaming + Demo Mode (Complete)

**Status:** Production-ready with real-time progress updates
**Completed:**
- ✅ `POST /research/stream` - SSE streaming with real-time progress events
- ✅ 7 event types (phase_start, phase_complete, gathering_progress, heartbeat, complete, error, phase_warning)
- ✅ Pattern C cleanup (guarantees background task cancellation on disconnect)
- ✅ GCP Cloud Run optimized (600s timeout, 30s heartbeats, proxy buffering prevention)
- ✅ Comprehensive SSE testing (13 streaming tests, client disconnect scenarios, memory leak prevention)
- ✅ Demo mode with `?demo=true` parameter on both endpoints
- ✅ Environment-gated demo mode (development/staging only, blocked in production)
- ✅ LRU caching for instant demo responses
- ✅ Comprehensive test coverage (161 tests, 86% coverage)
- ✅ Docker containerization with production-ready configuration

**Demo Mode:**
- Returns hardcoded quantum computing research example instantly
- Supports both `/research` and `/research/stream` endpoints
- Zero API costs for frontend integration testing
- Production safety: 403 response if attempted in production environment

**API Usage:**
```bash
# Real-time streaming
curl -N -X POST http://localhost:8000/research/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "What is quantum computing?"}'

# Demo mode (instant, no API costs)
curl -X POST "http://localhost:8000/research?demo=true" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'
```

**Benefits:**
- Users see real-time progress during 30-180s workflows
- Frontend teams can iterate without burning API keys ($0.30-0.50 per query)
- Docker deployment ready for GCP Cloud Run

**Documentation:**
- `docs/openapi.yaml` - Complete API specification with streaming and demo mode
- `docs/research/gcp-cloud-run-sse-limits.md` - GCP deployment guide

### 📋 Phase 3: Production Deployment (Future - 2-3 weeks)

**Goal:** Production-ready service on GCP

**Key additions:**
- Cloud Run deployment with streaming support
- Logfire observability and cost tracking
- API authentication and rate limiting
- Monitoring dashboards and alerts
- Load testing and performance optimization
- Production runbook
- Optional: DBOS durability for workflow resumption

---

## Technical Details

### Dependencies

Core dependencies:
- `pydantic-ai[anthropic,google]>=0.2.0` - AI agent framework with model providers
- `pydantic>=2.11.0` - Data validation
- `fastapi>=0.115.0` - REST API framework
- `uvicorn[standard]>=0.30.0` - ASGI server
- `structlog>=25.1.0` - Production logging
- `anthropic>=0.76.0` - Claude API client
- `google-genai>=1.59.0` - Gemini API client

Development dependencies:
- `pytest>=9.0.0` - Testing framework
- `httpx>=0.27.0` - Async HTTP client for testing
- `mypy>=1.19.0` - Type checking
- `ruff>=0.14.0` - Linting and formatting

See `pyproject.toml` for complete dependency list.

### Environment Variables

Required API keys:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."  # Get from https://console.anthropic.com/
export GEMINI_API_KEY="..."            # Get from https://aistudio.google.com/apikey
```

---

## Learn More

### Project Documentation

- **Architecture & Design:**
  - `docs/AGENT_ARCHITECTURE.md` - Agent design patterns and orchestration
  - `docs/ARCHITECTURE_DECISIONS.md` - ADRs for key technical decisions
  - `docs/IMPLEMENTATION_GUIDE.md` - Practical implementation guide

- **SSE Streaming (Phase 2.5):**
  - `SSE_STREAMING_PLAN.md` - Complete implementation plan for streaming endpoint
  - `docs/research/gcp-cloud-run-sse-limits.md` - GCP Cloud Run deployment guide
  - `SKILL_UPDATE_2026-01-28_sse-streaming.md` - SSE best practices and patterns

- **Development:**
  - `CLAUDE.md` - Development standards and guidelines
  - `pyproject.toml` - Dependencies and configuration

### External Resources

- [PydanticAI Documentation](https://ai.pydantic.dev/) - Agent framework
- [Pydantic Stack Demo](https://github.com/pydantic/pydantic-stack-demo/tree/main/durable-exec) - Reference implementation
- [FastAPI Documentation](https://fastapi.tiangolo.com/) - REST API framework
- [Claude API Documentation](https://docs.anthropic.com/) - Anthropic API
- [Gemini API Documentation](https://ai.google.dev/) - Google AI

### Key Concepts

**Multi-agent workflows:** Breaking complex tasks into specialized agent roles improves quality and maintainability

**Phase-level streaming:** Real-time progress updates via SSE keep users informed during long workflows (30-180s)

**Type-safe AI:** Using Pydantic for structured LLM outputs catches errors early and improves reliability

**Cost optimization:** Strategic model selection balances quality and cost for production viability (Gemini for parallel searches, Claude for reasoning)

---

## Contributing

When contributing, follow these principles:

1. **Reliability over features** - Production systems must work consistently
2. **Simplicity over cleverness** - Code should be easy to understand and maintain
3. **Type safety** - All functions have type hints, validated with mypy strict mode
4. **Test coverage** - 80% minimum coverage required
5. **Code quality** - Run `just validate-branch` before all commits

### Development Standards

- Python 3.12+
- Type hints on all functions
- Pydantic for data validation
- structlog for logging
- Test naming: `test__<what>__<expected>`

See [CLAUDE.md](CLAUDE.md) for complete development standards.

---

## License

Apache License 2.0 - See [LICENSE](LICENSE) file.

---

## Status

**Current Phase:** Phase 2.5 Complete ✅
**Production Ready:** Docker containerization complete, GCP deployment pending

### What's Deployed
- ✅ **Phase 1:** POC CLI (`research/`) - Functional prototype
- ✅ **Phase 2:** Production API (`src/`) - FastAPI service with comprehensive testing
- ✅ **Phase 2.5:** SSE Streaming + Demo Mode - Real-time progress updates with frontend testing support
  - 161 tests passing (86% coverage)
  - `/research` and `/research/stream` endpoints with `?demo=true` support
  - Docker containerization with production-ready configuration
  - Environment-gated security controls
- 📋 **Phase 3:** GCP Cloud Run Deployment - Ready for deployment

*Last updated: 2026-02-05*
