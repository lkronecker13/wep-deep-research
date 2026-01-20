# Autonomous Python Template

> Describe what you want to build. Let agents build it.

A self-building Python ML/Data Science template powered by Claude Code. Clone, describe your project, and watch it come to life.

## Quick Start

### 1. Clone this template

```bash
git clone https://github.com/ai-enhanced-engineer/aut-python-template.git my-project
cd my-project
```

### 2. Set up environment

```bash
just init
```

### 3. Start Claude Code

```bash
claude
```

### 4. Describe your project

```
> I want to build a RAG system for legal documents
```

That's it. Describe what you want; agents help you build it.

## Example Session

```
You: I want to build a fraud detection API

Claude: I'll help you build a fraud detection API. Let me understand your requirements:
        - What data sources will you use? (transactions, user behavior, etc.)
        - Any specific ML approach preference? (rule-based, XGBoost, neural network)
        - What's your target latency for predictions?

You: Transaction data from a PostgreSQL database. XGBoost for now, we can upgrade later.
     Need sub-100ms latency.

Claude: Great, let me set up the project structure:
        1. Creating data pipeline for PostgreSQL ingestion
        2. Setting up XGBoost model with feature engineering
        3. Building FastAPI endpoint with async handlers
        4. Adding monitoring and logging

        [Creates files, writes tests, validates...]

You: Add a batch prediction endpoint too

Claude: Adding batch prediction endpoint with:
        - CSV upload support
        - Background processing with status tracking
        - Results stored in PostgreSQL

        [Implements, tests, validates...]
```

## What's Included

This template comes with production-ready infrastructure:

### Production Logging

- Structured JSON logging with [structlog](https://www.structlog.org/)
- Correlation ID tracking across requests
- Dual-mode: human-readable (dev) / JSON (prod)

### Testing Infrastructure

- pytest with markers (unit, functional, integration)
- 80% coverage requirement
- Pre-commit hooks for quality gates

### CI/CD Pipeline

- GitHub Actions workflows
- Semantic versioning with auto-release
- Format → Lint → Type-check → Test pipeline

### Modern Python Tooling

- Python 3.12+
- Type hints throughout
- Pydantic for data validation
- uv for fast dependency management
- Ruff + Black for formatting/linting
- mypy (strict mode) for type checking

## Project Structure

```
my-project/
├── src/                       # Python source code
│   ├── __init__.py
│   └── logging.py             # Production logging system
├── tests/                     # Test suite
│   └── test_logging.py        # 21+ logging tests as examples
├── .claude/                   # Claude Code settings
├── .github/workflows/         # CI/CD pipelines
│   └── ci.yml
├── CLAUDE.md                  # Development standards
├── pyproject.toml             # Project configuration
├── justfile                   # Automation commands
├── ADR.md                     # Architecture decisions
└── .pre-commit-config.yaml    # Git hooks
```

## Development Commands

```bash
just                   # Show all available commands

# Environment
just init              # Complete development setup
just sync              # Update dependencies
just clean-env         # Reset environment

# Code Quality
just format            # Auto-format code
just lint              # Fix linting issues
just type-check        # Validate type hints
just validate-branch   # Run all checks (required before commits)

# Testing
just test              # Standard test suite
just test-unit         # Fast unit tests
just test-functional   # Feature tests
just test-integration  # Integration tests
just test-all          # Complete test suite
```

## The Production-First Philosophy

This template embodies the principle that **production AI requires engineering discipline**:

- **90% infrastructure, 10% model code**: Most production AI is validation, monitoring, error handling, and cost controls—not algorithms
- **Reliability over novelty**: Production systems must work consistently, not just impressively
- **Plan for failure**: Every external call needs error handling; every assumption needs validation

## Who Should Use This

### Teams Starting ML/Data Projects

Stop reinventing infrastructure. Describe your project and get a production-ready foundation.

### Senior Engineers New to ML

Get the safety rails you're accustomed to in production systems while learning ML concepts.

### Technical Leaders

Give your team a consistent, production-ready starting point that embodies engineering best practices.

## Learn More

### Production AI Engineering

- [A Production-First Approach to AI Engineering](https://aienhancedengineer.substack.com/p/a-production-first-approach-to-ai)
- [Google's Rules for ML](https://developers.google.com/machine-learning/guides/rules-of-ml)
- [Hidden Technical Debt in ML Systems](https://papers.nips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems.pdf)

### Technologies

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Pydantic](https://docs.pydantic.dev/) - Data validation
- [structlog](https://www.structlog.org/) - Structured logging
- [uv](https://docs.astral.sh/uv/) - Fast Python package management

## Contributing

When contributing, prioritize:

1. **Reliability over features**
2. **Simplicity over cleverness**
3. **Documentation over assumptions**
4. **Tests over trust**

## License

Apache License 2.0 - See [LICENSE](LICENSE) file.

---

*"Describe what you want. Let agents build it."*
