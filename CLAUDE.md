# Project Instructions

Development standards and guidelines for Claude Code when working on this project.

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

## Local Development

```bash
just init              # Set up environment
just run               # Run main application
just test              # Run test suite
just test-unit         # Fast unit tests only
just validate-branch   # Full validation (required before commits)
```

## Project Structure

```
src/                   # Python source code
tests/                 # Test suite (mirrors src/ structure)
.github/workflows/     # CI/CD pipelines
```
