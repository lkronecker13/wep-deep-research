"""Gunicorn configuration for production deployment.

Environment-aware configuration that supports both local development
and Cloud Run deployment. Cloud Run provides a PORT environment variable.
"""

import multiprocessing
import os

# Bind configuration
# Cloud Run sets PORT environment variable; default to 8080
port = os.environ.get("PORT", "8080")
bind = f"0.0.0.0:{port}"

# Worker configuration
# Cloud Run recommends 1-2 workers per vCPU
# For AI workloads with async I/O, fewer workers are often better
# Default: 2 workers (suitable for Cloud Run with 1-2 vCPUs)
workers = int(os.environ.get("GUNICORN_WORKERS", min(2, multiprocessing.cpu_count())))
worker_class = "uvicorn.workers.UvicornWorker"

# Timeout configuration
# Research workflows can take 30-180 seconds per request
# Set timeout high enough to allow completion
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "300"))
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", "5"))

# Logging configuration
# Cloud Run captures stdout/stderr automatically
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
accesslog = "-"  # Log to stdout
errorlog = "-"  # Log to stderr

# Performance tuning
# Preload app for faster worker startup
preload_app = True

# Maximum pending connections
backlog = 2048

# Maximum requests per worker before restart (prevents memory leaks)
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", "50"))
