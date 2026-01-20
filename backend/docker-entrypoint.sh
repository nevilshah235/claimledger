#!/bin/bash
set -e

# Get port from environment variable (Cloud Run sets this)
PORT=${PORT:-8080}

# Log startup information
echo "🚀 Starting ClaimLedger API on port ${PORT}..."

# Run uvicorn with the correct port
exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT}"
