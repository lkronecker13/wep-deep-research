# Skill Update: FastAPI OpenAPI Static Export Pattern

**Date:** 2026-01-29
**Repository:** wep-deep-research
**Branch:** feat/workflow-fastapi-layer
**Session Focus:** OpenAPI YAML export implementation, dependency management, production tooling patterns
**Context:** Implemented static OpenAPI spec export for client SDK generation and API contract validation

---

## Learnings

### Patterns Discovered

#### 1. **FastAPI OpenAPI Static Export Pattern** (Production-Grade)

**Problem:** Need static OpenAPI YAML files for client SDK generation, API contract validation in CI/CD, and sharing specs with external teams without running the server.

**Solution:** Extract schema from FastAPI app using `app.openapi()` and write to YAML with production-quality configuration.

```python
# src/export_openapi.py
from pathlib import Path
from typing import Any
import structlog
import yaml
from src.server import get_app

log = structlog.get_logger("src.export_openapi")

def export_openapi_yaml(output_path: Path = Path("docs/openapi.yaml")) -> int:
    """
    Generate OpenAPI YAML specification from FastAPI app definition.
    
    Returns:
        0 on success, 1 on failure (for CI/CD integration)
    """
    log.info("export.started", output_path=str(output_path))
    
    try:
        # Create FastAPI app instance (no server startup needed)
        app = get_app()
        
        # Generate OpenAPI schema (returns dict)
        openapi_schema: dict[str, Any] = app.openapi()
        
        if not openapi_schema:
            raise ValueError("FastAPI app returned empty OpenAPI schema")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write YAML file with readable configuration
        with output_path.open("w") as f:
            yaml.dump(
                openapi_schema,
                f,
                default_flow_style=False,  # Use block style (readable)
                sort_keys=False,  # Preserve order
                allow_unicode=True,  # Support special characters
            )
        
        file_size_kb = output_path.stat().st_size / 1024
        log.info("export.completed", output_path=str(output_path), size_kb=round(file_size_kb, 1))
        print(f"✅ OpenAPI specification exported to {output_path}")
        print(f"📄 File size: {file_size_kb:.1f} KB")
        return 0
        
    except ImportError as e:
        log.error("export.failed.import", error=str(e), output_path=str(output_path))
        print(f"❌ Failed to import dependencies: {e}", file=sys.stderr)
        return 1
    except (PermissionError, OSError) as e:
        log.error("export.failed.io", error=str(e), output_path=str(output_path))
        print(f"❌ File system error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        log.error("export.failed.unexpected", error=str(e), output_path=str(output_path))
        print(f"❌ Unexpected error during OpenAPI export: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(export_openapi_yaml())
```

**Key aspects:**
- **No server startup required:** `app.openapi()` extracts schema without running uvicorn
- **Exit codes for CI/CD:** Return 0 on success, 1 on failure (automation-friendly)
- **Readable YAML output:** Block style, preserve key order, unicode support
- **Comprehensive error handling:** Import errors, file I/O errors, unexpected errors
- **Structured logging:** Observability for debugging CI/CD failures

---

#### 2. **CRITICAL: Transitive Dependencies Are Fragile**

**Finding:** PyYAML worked initially via FastAPI's transitive dependency chain, but both specialist reviewers flagged this as CRITICAL.

**Problem:**
```python
# Initial implementation relied on transitive dependency:
# wep-deep-research -> FastAPI -> starlette -> PyYAML (maybe?)
import yaml  # Works... for now

# pyproject.toml
dependencies = [
    "fastapi>=0.100.0",
    # No PyYAML listed
]
```

**Why this is dangerous:**
- **Breaks silently:** Upstream can remove PyYAML anytime
- **Version conflicts:** No control over which PyYAML version is used
- **Deployment failures:** Works locally, breaks in prod (different dependency resolution)
- **Type checking fails:** Missing `types-PyYAML` means mypy can't validate

**Fix:**
```toml
# pyproject.toml
dependencies = [
    "fastapi>=0.100.0",
    "pyyaml>=6.0.0",        # ALWAYS explicit for direct imports
]

[project.optional-dependencies]
dev = [
    "types-pyyaml>=6.0.0",  # Type stubs for mypy
]
```

**Rule:** If you import it, declare it. Never rely on transitive dependencies for direct imports.

**Source:** Both bb-backend-engineer and Python expert reviews independently flagged this

---

#### 3. **Multi-Specialist Code Review Pattern**

**Pattern:** Request reviews from multiple specialists with different expertise areas

**Workflow:**
1. Implement initial version (basic functionality working)
2. Request review from domain specialist (`bb-backend-engineer`)
3. Request review from language specialist (Python expert)
4. Both reviewers provide independent feedback
5. Consolidate findings and apply fixes

**Example from this session:**
```
User: "have @bb-backend-engineer and both python specialists review"
→ Backend reviewer identified: Missing PyYAML dependency, lack of error handling
→ Python expert identified: Same PyYAML issue, type hint improvements
```

**Validation:** Both reviewers independently identified the CRITICAL dependency issue

**Benefits:**
- **Cross-validation:** Independent reviews catch the same critical issues (high confidence)
- **Diverse perspectives:** Backend specialist focuses on deployment, language expert on idioms
- **Knowledge gaps exposed:** When both flag the same issue, it's definitely important
- **Quality assurance:** Two layers of review before user approval

**When to use:**
- Production tooling (scripts used in CI/CD)
- Critical path code (core business logic)
- Complex implementations (async patterns, resource management)

---

### Anti-patterns Identified

#### 1. **Relying on Transitive Dependencies for Direct Imports**

**Don't:**
```python
# src/export_openapi.py
import yaml  # Works because FastAPI transitively includes it... maybe?

# pyproject.toml
dependencies = [
    "fastapi>=0.100.0",
    # No PyYAML declared
]
```

**Problem:**
- **Silent breakage:** FastAPI upgrades and removes PyYAML, your script breaks
- **Version conflicts:** Can't control PyYAML version, may get incompatible version
- **Type checking fails:** Missing `types-PyYAML` means mypy can't validate
- **Deployment variance:** Works locally (cached transitive), breaks in fresh environment

**Fix:**
```toml
dependencies = [
    "fastapi>=0.100.0",
    "pyyaml>=6.0.0",       # Explicit dependency
]

[project.optional-dependencies]
dev = [
    "types-pyyaml>=6.0.0",  # Type stubs
]
```

**Rule:** If your code imports it, your dependencies must declare it.

---

### Key Decisions

#### 1. **Why PyYAML (Not JSON) for OpenAPI Export**

**Decision:** Export OpenAPI spec as YAML, not JSON

**Alternatives considered:**
- **JSON:** FastAPI's default openapi.json endpoint format
- **Both:** Export both YAML and JSON

**Rationale:**
- **Human-readable:** YAML easier to review in pull requests
- **Comments supported:** Can add inline documentation (JSON can't)
- **Industry standard:** openapi-generator expects YAML by default
- **Git-friendly:** Diffs show clear structural changes

**Tradeoff:** Requires explicit PyYAML dependency (JSON is stdlib)

**Implementation:** Use `default_flow_style=False` for block format

---

#### 2. **Why Declare PyYAML in Main Dependencies (Not dev)**

**Decision:** Add PyYAML to `dependencies`, not `optional-dependencies.dev`

**Alternative:** Put in dev-only dependencies since it's a tooling script

**Rationale:**
- **Production tooling:** Export script runs in CI/CD (production context)
- **Deployment artifact:** OpenAPI YAML is part of release process
- **Availability guarantee:** Should work in all environments, not just dev

**Source:** bb-backend-engineer review flagged transitive dependency as CRITICAL

---

### Tools & Commands

#### 1. **FastAPI app.openapi()** — Extract OpenAPI schema

**Usage:**
```python
from fastapi import FastAPI

app = FastAPI(title="My API", version="1.0.0")

# Extract OpenAPI 3.1.0 schema (no server startup needed)
openapi_schema: dict[str, Any] = app.openapi()
```

**When to use:**
- Static documentation generation
- Client SDK generation (openapi-generator)
- API contract validation in CI/CD
- Sharing specs with external teams

---

#### 2. **PyYAML** — YAML serialization

**Install:**
```toml
dependencies = [
    "pyyaml>=6.0.0",
]

[project.optional-dependencies]
dev = [
    "types-pyyaml>=6.0.0",  # Type stubs for mypy
]
```

**Usage:**
```python
import yaml

# Readable block-style YAML
with open("output.yaml", "w") as f:
    yaml.dump(
        data,
        f,
        default_flow_style=False,  # Block style
        sort_keys=False,  # Preserve order
        allow_unicode=True,  # Unicode support
    )
```

---

## Recommended Skill Updates

### 1. Create New Skill: `fastapi-openapi-export`
- **Section:** Complete new skill
- **Content:** Static export pattern, error handling, CI/CD integration
- **Rationale:** Fills gap in FastAPI tooling knowledge

### 2. Update: `python-dependencies`
- **Section:** Anti-patterns
- **Content:** Transitive dependency anti-pattern
- **Rationale:** CRITICAL issue caught by both reviewers

### 3. Update: `code-review-patterns`
- **Section:** Multi-specialist review
- **Content:** When and how to use multiple reviewers
- **Rationale:** Pattern successfully caught critical issue

## Tags
`fastapi-openapi`, `python-tooling`, `dependency-management`, `exit-codes`, `error-handling`, `ci-cd-integration`, `production-patterns`
