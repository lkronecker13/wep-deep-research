"""Generate OpenAPI specification as YAML file."""

import sys
from pathlib import Path
from typing import Any

import structlog
import yaml

from src.server import get_app

log = structlog.get_logger("src.export_openapi")


def export_openapi_yaml(output_path: Path = Path("docs/openapi.yaml")) -> int:
    """
    Generate OpenAPI YAML specification from FastAPI app definition.

    Extracts the OpenAPI 3.1.0 schema from the FastAPI application and writes it
    to a YAML file. The schema includes all endpoint definitions, request/response
    models, and API documentation.

    This is useful for:
    - Generating static API documentation
    - Client SDK generation (via openapi-generator)
    - API contract validation in CI/CD
    - Sharing API specs with external teams

    Args:
        output_path: Path to write the YAML file (default: docs/openapi.yaml)

    Returns:
        0 on success, 1 on failure (for CI/CD integration)

    Raises:
        ImportError: If FastAPI app dependencies are missing
        PermissionError: If output path is not writable
        OSError: If disk write fails
        ValueError: If generated schema is empty

    Example:
        >>> from pathlib import Path
        >>> export_openapi_yaml(Path("api-spec.yaml"))
        ✅ OpenAPI specification exported to api-spec.yaml
        📄 File size: 18.3 KB
    """
    log.info("export.started", output_path=str(output_path))

    try:
        # Create FastAPI app instance
        app = get_app()

        # Generate OpenAPI schema (returns dict)
        openapi_schema: dict[str, Any] = app.openapi()

        if not openapi_schema:
            raise ValueError("FastAPI app returned empty OpenAPI schema")

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write YAML file
        with output_path.open("w") as f:
            yaml.dump(
                openapi_schema,
                f,
                default_flow_style=False,  # Use block style (readable)
                sort_keys=False,  # Preserve order
                allow_unicode=True,  # Support special characters
            )

        file_size_kb = output_path.stat().st_size / 1024
        log.info(
            "export.completed",
            output_path=str(output_path),
            size_kb=round(file_size_kb, 1),
        )
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
