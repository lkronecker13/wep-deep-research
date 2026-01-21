# Deep Research Service

> AI-powered deep research using multi-agent workflows

An intelligent research system that conducts structured, comprehensive research using specialized AI agents. Built with [PydanticAI](https://ai.pydantic.dev/) and inspired by [Pydantic's durable-exec demo](https://github.com/pydantic/pydantic-stack-demo/tree/main/durable-exec).

**Current Status:** Phase 1 POC ✅ (Functional prototype)

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

### Run Your First Research Query

```bash
python -m research.run_research "What are the latest developments in quantum computing?"
```

**Output:** Results are saved to `research/outputs/research_YYYY-MM-DD_HH-MM-SS.json`

### View Results

```bash
# Pretty-print the latest result
cat research/outputs/research_*.json | jq '.report.key_findings'
```

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
├── research/                    # Phase 1 POC (current)
│   ├── models.py                # Pydantic models (5 models)
│   ├── agents.py                # PydanticAI agents (4 agents)
│   ├── run_research.py          # CLI + workflow orchestration
│   └── outputs/                 # JSON results (gitignored)
│
├── src/                         # Core application (future phases)
│   ├── logging.py               # Production logging system
│   └── ...
│
├── tests/                       # Test suite
│   └── test_logging.py          # Example tests
│
├── docs/                        # Technical documentation
│   ├── ARCHITECTURE_DECISIONS.md
│   ├── IMPLEMENTATION_PLAN.md
│   └── PHASE1_IMPLEMENTATION.md
│
├── pyproject.toml               # Dependencies and config
├── justfile                     # Development automation
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

### 🚧 Phase 2: Local Service (Planned - 1-2 weeks)

**Goal:** FastAPI REST service with durable execution

**Key additions:**
- FastAPI endpoints for research workflows
- DBOS-backed durability (PostgreSQL)
- Workflow resumption on failure
- Repository pattern for persistence
- Domain events for state tracking
- Comprehensive test suite (80%+ coverage)

### 📋 Phase 3: Production Deployment (Future - 2-3 weeks)

**Goal:** Production-ready service on GCP

**Key additions:**
- Cloud Run deployment
- Logfire observability and cost tracking
- API authentication and rate limiting
- Monitoring dashboards and alerts
- Load testing and performance optimization
- Production runbook

---

## Technical Details

### Dependencies

Core dependencies:
- `pydantic-ai[anthropic,google]>=0.2.0` - AI agent framework with model providers
- `pydantic>=2.11.0` - Data validation
- `annotated-types>=0.7.0` - Type constraints (MaxLen)
- `anthropic>=0.76.0` - Claude API client
- `google-genai>=1.59.0` - Gemini API client

Development dependencies:
- `pytest>=9.0.0` - Testing framework
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

### Documentation

- [Architecture Decisions](docs/ARCHITECTURE_DECISIONS.md) - Detailed technical rationale and trade-offs
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md) - Three-phase development roadmap
- [Phase 1 Implementation](docs/PHASE1_IMPLEMENTATION.md) - POC implementation details

### External Resources

- [PydanticAI Documentation](https://ai.pydantic.dev/) - Agent framework
- [Pydantic Stack Demo](https://github.com/pydantic/pydantic-stack-demo/tree/main/durable-exec) - Reference implementation
- [Claude API Documentation](https://docs.anthropic.com/) - Anthropic API
- [Gemini API Documentation](https://ai.google.dev/) - Google AI

### Key Concepts

**Multi-agent workflows:** Breaking complex tasks into specialized agent roles improves quality and maintainability

**Durable execution:** Long-running workflows that can resume on failure (Phase 2 feature with DBOS)

**Type-safe AI:** Using Pydantic for structured LLM outputs catches errors early and improves reliability

**Cost optimization:** Strategic model selection balances quality and cost for production viability

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

**Current Phase:** 1 (POC) ✅
**Next Phase:** 2 (Local Service) 🚧
**Production Ready:** Phase 3 📋

*Last updated: 2026-01-20*
