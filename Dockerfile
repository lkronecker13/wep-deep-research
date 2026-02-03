ARG PYTHON_VERSION=3.12
ARG UV_VERSION=latest

# Stage 1: Fetch the specified version of `uv` and `uvx` executables
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv_installer

# Stage 2: Builder - Prepare the application environment
FROM python:${PYTHON_VERSION}-slim AS builder

# Copy the `uv` and `uvx` executables from the installer stage to `/bin/`
COPY --from=uv_installer /uv /uvx /bin/

# Set the working directory inside the container to `/app`
WORKDIR /app

# Copy only dependency files first (for better layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies using `uv`, leveraging cache for efficiency
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-editable

# Copy the application source code
COPY src/ ./src/

# Stage 3: Runtime - Minimal production environment
FROM python:${PYTHON_VERSION}-slim AS runtime

# Container detection flag
ENV IS_CONTAINER=true

# Copy the `uv` executable from the builder stage (needed for gunicorn)
COPY --from=builder /bin/uv /bin/uv

# Copy the Python virtual environment with installed dependencies
COPY --from=builder /app/.venv /app/.venv

# Copy the application code
COPY --from=builder /app/src /app/src

# Copy gunicorn configuration
COPY gunicorn_conf.py /app/gunicorn_conf.py

# Set the working directory
WORKDIR /app

# Update the PATH environment variable to prioritize binaries from the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Add the /app directory to PYTHONPATH so src module can be imported
ENV PYTHONPATH="/app"

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose port 8080 (Cloud Run standard)
EXPOSE 8080

# Start the application using gunicorn with uvicorn workers
CMD ["gunicorn", "-c", "/app/gunicorn_conf.py", "src.server:app"]
