#!/bin/bash
# Docker entrypoint script for ClaimLedger Backend
# Handles PORT environment variable from Cloud Run

set -e

# Get PORT from environment (Cloud Run sets this, default to 8080)
PORT=${PORT:-8080}

# Initialize database if needed
echo "🔍 Checking database connection..."
python -c "
from src.database import check_db_accessible, init_db
try:
    check_db_accessible()
    print('✅ Database connection successful')
    init_db()
except Exception as e:
    print(f'⚠️  Database initialization warning: {e}')
    # Continue anyway - app might work without DB for health checks
" || echo "⚠️  Database check skipped"

# Start the application
echo "🚀 Starting ClaimLedger Backend on port ${PORT}..."
exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT}"
