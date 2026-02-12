# Project task runner
# Run `just` or `just --list` to see available recipes

set dotenv-load := false
set shell := ["bash", "-cu"]

# Configuration
python_version := "3.12"
source_dir := "src/"
test_dir := "tests/"


# Display available recipes
default:
    @just --list

# ----------------------------
# Environment Management
# ----------------------------

# Set up Python version, venv, and install dependencies
init:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "🔧 Installing uv if missing..."
    if ! command -v uv >/dev/null 2>&1; then
        echo "📦 Installing uv..."
        python3 -m pip install --user --upgrade uv
    else
        echo "✅ uv is already installed"
    fi
    echo "🐍 Setting up Python {{ python_version }} environment..."
    uv python install {{ python_version }}
    uv venv --python {{ python_version }} .venv
    echo "📦 Installing project dependencies..."
    uv sync --extra dev
    . .venv/bin/activate && uv pip install -e .
    echo "🔗 Setting up pre-commit hooks..."
    if [ -f .pre-commit-config.yaml ]; then
        uv run pre-commit install
        echo "✅ Pre-commit hooks installed"
    else
        echo "⚠️  No .pre-commit-config.yaml found, skipping pre-commit setup"
    fi
    echo "🎉 Environment setup complete!"

# Sync project dependencies
sync:
    @echo "Syncing project dependencies..."
    uv sync --extra dev
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'

# Clean Python caches and tooling artifacts
clean-project:
    @echo "Cleaning project caches..."
    find . -type d \( -name '.pytest_cache' -o -name '.ruff_cache' -o -name '.mypy_cache' -o -name '__pycache__' \) -exec rm -rf {} +
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'

# Remove the virtual environment folder
clean-env:
    @echo "Deleting virtual environment..."
    rm -rf .venv
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'

# ----------------------------
# Code Quality
# ----------------------------

# Format codebase using ruff
format:
    @echo "Formatting code with ruff..."
    uv run ruff format
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'

# Lint code using ruff and autofix issues
lint:
    @echo "Running lint checks with ruff..."
    uv run ruff check . --fix
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'

# Perform static type checks using mypy
type-check:
    @echo "Running type checks with mypy..."
    uv run --extra dev mypy {{ source_dir }}
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'

# ----------------------------
# Tests
# ----------------------------

# Run unit tests with pytest
test-unit:
    @echo "Running UNIT tests with pytest..."
    uv run python -m pytest -vv --verbose -s {{ test_dir }}
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'

# Run functional tests with pytest
test-functional:
    @echo "Running FUNCTIONAL tests with pytest..."
    uv run python -m pytest -m functional -vv --verbose -s {{ test_dir }}
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'

# Run integration tests with pytest
test-integration:
    @echo "Running INTEGRATION tests with pytest..."
    uv run python -m pytest -m integration -vv --verbose -s {{ test_dir }}
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'

# Run standard tests with coverage report (excludes integration)
test:
    @echo "Running tests with pytest..."
    uv run python -m pytest -m "not integration" -vv -s {{ test_dir }} \
        --cov=src \
        --cov-config=pyproject.toml \
        --cov-fail-under=80 \
        --cov-report=term-missing
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'

# Run all tests including integration tests
test-all:
    @echo "Running ALL tests with pytest..."
    uv run python -m pytest -vv -s {{ test_dir }} \
        --cov=src \
        --cov-config=pyproject.toml \
        --cov-fail-under=80 \
        --cov-report=term-missing
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'

# ----------------------------
# Branch Validation
# ----------------------------

# Run formatting, linting, type checks, and tests
validate-branch: format lint type-check test
    @echo "🎉 Branch validation successful - ready for PR!"
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'

# ----------------------------
# Research POC (Phase 1)
# ----------------------------

# Run a research query using the Phase 1 POC
research query:
    @echo "🔍 Running deep research query..."
    @echo "Query: {{ query }}"
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'
    uv run python -m research.run_research "{{ query }}"
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'
    @echo "✅ Research complete! Check research/outputs/ for results"

# ----------------------------
# Evaluation Suite
# ----------------------------

# Run full evaluation suite (35 questions across 7 domains)
eval-full:
    @echo "Running FULL evaluation suite (35 questions)..."
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'
    uv run python -m research.evaluation.runner --export research/outputs/evaluations/
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'

# Run smoke test evaluations (P0 only - 7 questions)
eval-smoke:
    @echo "Running SMOKE test evaluations (7 P0 questions)..."
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'
    uv run python -m research.evaluation.runner --smoke-test --export research/outputs/evaluations/
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'

# Run critical evaluations (P0+P1 - 14 questions)
eval-critical:
    @echo "Running CRITICAL evaluations (14 P0+P1 questions)..."
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'
    uv run python -m research.evaluation.runner --critical --export research/outputs/evaluations/
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'

# Run evaluation for a specific domain
eval-domain domain:
    @echo "Running evaluation for {{ domain }} domain..."
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'
    uv run python -m research.evaluation.runner --domain {{ domain }} --export research/outputs/evaluations/
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'

# Run evaluation for a single custom query
eval-query query:
    @echo "Running evaluation for custom query..."
    @echo "Query: {{ query }}"
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'
    uv run python -m research.evaluation.runner --query "{{ query }}" --export research/outputs/evaluations/
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'

# ----------------------------
# Run Application
# ----------------------------

# Run the main application module
run:
    @echo "🚀 Running main application..."
    uv run python -m src.main
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'

# Start the FastAPI development server
serve:
    @echo "Starting development server..."
    uv run uvicorn src.server:app --reload --host 0.0.0.0 --port 8000

# Generate OpenAPI YAML specification
export-openapi:
    @echo "Generating OpenAPI YAML specification..."
    uv run python -m src.export_openapi
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'

# ----------------------------
# Docker
# ----------------------------

# Build Docker image for production
docker-build:
    @echo "🏗️  Building Deep Research Service Docker image..."
    DOCKER_BUILDKIT=1 docker build --target=runtime . -t wep-deep-research:latest
    @echo "✅ Docker image built successfully!"
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'

# Run service with docker-compose
docker-run:
    @echo "🚀 Starting Deep Research Service with Gunicorn..."
    @echo "🔗 Service will be available at: http://localhost:8080"
    @echo "📖 API docs at: http://localhost:8080/docs"
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'
    docker-compose up --remove-orphans

# Stop running containers
docker-stop:
    @echo "🛑 Stopping Deep Research Service containers..."
    docker-compose down --remove-orphans
    @echo "✅ Containers stopped!"
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'

# View container logs
docker-logs:
    @echo "📋 Viewing Deep Research Service logs..."
    docker-compose logs -f deep-research

# Remove Docker images and prune build cache
docker-clean:
    @echo "🧹 Cleaning Docker images and build cache..."
    docker-compose down --rmi all --volumes --remove-orphans 2>/dev/null || true
    docker image rm wep-deep-research:latest 2>/dev/null || true
    @echo "✅ Docker cleanup complete!"
    @printf '\033[0;32m--------------------------------------------------\033[0m\n'
