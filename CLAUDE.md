# Project Instructions

Development standards and guidelines for Claude Code when working on the Deep Research Service.

## Project Overview

This is an AI-powered deep research service using multi-agent workflows built with PydanticAI.

- **Phase 1** (Complete): POC in `research/` folder - 4-agent workflow (planning, gathering, synthesis, verification)
- **Phase 2** (Complete): FastAPI service with production workflow, structured error handling, health checks
- **Phase 2.5** (Complete): SSE streaming, demo mode, Docker containerization, LLM-as-a-Judge evaluation system
- **Phase 3** (Planned): Production GCP Cloud Run deployment

**Multi-model strategy**: Claude Sonnet 4.5 (reasoning) + Gemini 2.5 Flash (parallel searches)

## Git Workflow

**NEVER push directly to main.** All changes must go through pull requests.

### Rules

1. Always work on feature branches
2. Create pull requests using `gh pr create`
3. Wait for user approval before merging
4. No force pushes to main

### Workflow

```bash
# 1. Create feature branch
git checkout -b feat/my-feature

# 2. Make changes and validate
just validate-branch

# 3. Commit and push
git add <files>
git commit -m "feat: description"
git push origin feat/my-feature

# 4. Create PR
gh pr create --title "feat: Title" --body "Description"

# 5. WAIT for user approval before merging
```

## Development Standards

### Before Any Commit

Run full validation:

```bash
just validate-branch
```

This runs:
- `just format` - Code formatting (black, ruff)
- `just lint` - Linting with auto-fix
- `just type-check` - Type validation (mypy strict)
- `just test` - Tests with 80% coverage minimum

### Test Naming Convention

All tests must follow: `test__<what>__<expected>`

Examples:
- `test__parse_config__returns_valid_settings`
- `test__api_call__raises_on_timeout`
- `test__logger_init__creates_json_processor_in_production`

### Code Style

- Python 3.12+
- Type hints on all functions
- Pydantic for data validation
- structlog for logging
- 120 character line limit

## Environment Setup

### Required API Keys

```bash
# Create .env file or export these variables
export ANTHROPIC_API_KEY="sk-ant-..."  # Get from https://console.anthropic.com/
export GEMINI_API_KEY="..."            # Get from https://aistudio.google.com/apikey
```

**Important**: API keys are required to run research queries but NOT for code quality tools.

## Local Development

```bash
# Environment setup
just init              # Set up Python 3.12+ environment and dependencies
just sync              # Sync dependencies after pyproject.toml changes

# Code quality (works without API keys)
just format            # Auto-format code with ruff
just lint              # Lint and auto-fix issues
just type-check        # Type check with mypy (only checks src/)
just test              # Run tests (only checks tests/)
just validate-branch   # Full validation (format + lint + type-check + test)

# Running the API server (requires API keys)
just serve             # Start FastAPI dev server on http://localhost:8000

# Running research queries via CLI (requires API keys)
just research "Your research question here"

# Evaluation suite (requires API keys + optional PHOENIX_API_KEY)
just eval-smoke        # 7 P0 questions
just eval-critical     # 14 P0+P1 questions
just eval-full         # 35 questions across 7 domains

# Docker
just docker-build      # Build production image
just docker-run        # Run with docker-compose (http://localhost:8080)
just docker-stop       # Stop containers
```

## Project Structure

```
wep-deep-research/
├── src/                          # Production application (Phase 2+)
│   ├── server.py                 # FastAPI app (/research, /research/stream, /health)
│   ├── workflow.py               # 4-phase async research pipeline
│   ├── agents.py                 # 4 PydanticAI agents (plan, gather, synthesize, verify)
│   ├── models.py                 # Pydantic models (PhaseTimings, ResearchResult, etc.)
│   ├── events.py                 # SSE event types and streaming infrastructure
│   ├── demo.py                   # Demo mode (hardcoded responses for frontend testing)
│   ├── exceptions.py             # Custom exceptions (PlanningError, GatheringError, etc.)
│   ├── logging.py                # Production logging (structlog + correlation IDs)
│   └── export_openapi.py         # OpenAPI YAML generation
│
├── research/                     # Phase 1 POC (reference + evaluation)
│   ├── models.py                 # Pydantic models for research data
│   ├── agents.py                 # 4 PydanticAI agents (CLI version)
│   ├── run_research.py           # CLI + workflow orchestration
│   ├── evaluation/               # LLM-as-a-Judge evaluation system
│   │   ├── runner.py             # Evaluation orchestrator
│   │   ├── evaluators.py         # 4 evaluators (one per agent phase)
│   │   ├── prompts.py            # Judge prompt templates
│   │   ├── datasets.py           # Dataset loading
│   │   ├── schemas.py            # Evaluation data models
│   │   ├── export.py             # Results export
│   │   ├── tracing.py            # Arize Phoenix integration
│   │   └── EVALUATION_REPORT.md  # Production run results
│   ├── data/
│   │   └── production_questions.json  # 35 questions across 7 domains
│   └── outputs/                  # JSON results (gitignored)
│
├── tests/                        # Test suite (182 tests, 86% coverage)
│
├── docs/                         # Technical documentation
│   └── EXECUTIVE_BRIEF.md        # Executive summary of current state
│
├── Dockerfile                    # Production Docker image
├── docker-compose.yml            # Container orchestration
├── gunicorn_conf.py              # Production WSGI config
├── ADR.md                        # Architecture Decision Record
├── pyproject.toml                # Project configuration
├── justfile                      # Development automation
└── CLAUDE.md                     # This file
```

## Important Notes

### Research Folder Exclusions

The `research/` folder (including the evaluation system) is **intentionally excluded** from:
- `just type-check` (only checks `src/`)
- `just test` (only checks `tests/`)

This is by design. The `research/` folder contains the Phase 1 POC and the evaluation harness, which are separate from the production `src/` code.

### Lazy Agent Initialization

Agents in both `research/agents.py` and `src/agents.py` use lazy initialization (getter functions with `@lru_cache`) so imports work without API keys. `src/agents.py` also provides `create_*()` factory functions for test injection with `TestModel`.

### Two Parallel Pipelines

The project has two implementations of the same 4-agent workflow:
- **`research/`**: CLI-based POC, used by `just research` and the evaluation system
- **`src/`**: FastAPI production service, used by `just serve`

Both share the same agent architecture but differ in infrastructure (tracing, error handling, streaming).
