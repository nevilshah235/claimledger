# Multi-stage Dockerfile for ClaimLedger Backend
# Optimized for Google Cloud Run deployment

# Stage 1: Builder stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./

# Install uv (modern Python package manager)
RUN pip install --no-cache-dir uv

# Install dependencies into virtual environment
RUN uv pip install --system --no-cache -e ".[dev]" || \
    pip install --no-cache-dir -e ".[dev]"

# Stage 2: Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder (or install dependencies directly)
# For simplicity, we'll install directly in runtime stage
COPY pyproject.toml ./
RUN pip install --no-cache-dir uv && \
    (uv pip install --system --no-cache -e "." || \
     pip install --no-cache-dir -e ".")

# Copy application code
COPY src/ ./src/

# Create uploads directory
RUN mkdir -p uploads

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port (Cloud Run sets PORT env var, default to 8080)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8080}/health')"

# Run the application
# Cloud Run provides PORT environment variable
CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8080}
