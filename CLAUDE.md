# Project Instructions

Development standards and guidelines for Claude Code when working on the Deep Research Service.

## Project Overview

This is an AI-powered deep research service using multi-agent workflows built with PydanticAI. The project uses a phased approach:

- **Phase 1 (Current)**: POC in `research/` folder - 4-agent workflow (planning, gathering, synthesis, verification)
- **Phase 2 (Planned)**: FastAPI service with DBOS durability
- **Phase 3 (Future)**: Production GCP deployment

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

# Running research queries (requires API keys)
python -m research.run_research "Your research question here"

# View results
ls research/outputs/
cat research/outputs/research_*.json | jq '.report.key_findings'
```

## Project Structure

```
wep-deep-research/
├── research/              # Phase 1 POC (current implementation)
│   ├── models.py          # Pydantic models for research data
│   ├── agents.py          # 4 PydanticAI agents
│   ├── run_research.py    # CLI + workflow orchestration
│   └── outputs/           # JSON results (gitignored)
│
├── src/                   # Core application (future phases)
│   └── logging.py         # Production logging system
│
├── tests/                 # Test suite
│   └── test_logging.py    # Example logging tests
│
├── docs/                  # Technical documentation
│   ├── ARCHITECTURE_DECISIONS.md
│   ├── IMPLEMENTATION_PLAN.md
│   └── PHASE1_IMPLEMENTATION.md
│
├── pyproject.toml         # Project configuration
├── justfile               # Development automation
└── CLAUDE.md              # This file
```

## Important Notes

### Research Folder Exclusions

The `research/` folder is **intentionally excluded** from:
- `just type-check` (only checks `src/`)
- `just test` (only checks `tests/`)

This is by design for Phase 1 POC work. Research code will be restructured into `src/` during Phase 2.

### Lazy Agent Initialization

Agents in `research/agents.py` use lazy initialization (getter functions) so imports work without API keys. This allows `just` commands to run without requiring API credentials.
