#!/bin/bash
# Test Cloud SQL connection using the backend Docker container

set -euo pipefail

cd "$(dirname "$0")/.."

PROJECT_ID="claimly-484803"
REGION="us-central1"
DB_INSTANCE="claimledger-db"
DB_USER="claimledger-user"
DB_NAME="claimledger"
DB_PASSWORD="tY8mK!x2zW3@pB7q"

echo "🔍 Getting Cloud SQL public IP..."

# Get public IP
PUBLIC_IP=$(gcloud sql instances describe "${DB_INSTANCE}" \
  --format="value(ipAddresses[0].ipAddress)" 2>/dev/null || echo "")

if [ -z "${PUBLIC_IP}" ]; then
  echo "❌ Could not get public IP. Checking instance status..."
  gcloud sql instances describe "${DB_INSTANCE}" --format="yaml(ipAddresses)"
  exit 1
fi

echo "✅ Public IP: ${PUBLIC_IP}"

# Get local IP
LOCAL_IP=$(curl -s ifconfig.me || echo "")
echo "📍 Local IP: ${LOCAL_IP}"

echo ""
echo "🔐 Checking authorized networks..."
AUTHORIZED=$(gcloud sql instances describe "${DB_INSTANCE}" \
  --format="value(settings.ipConfiguration.authorizedNetworks[].value)" 2>/dev/null | grep -q "${LOCAL_IP}" && echo "yes" || echo "no")

if [ "${AUTHORIZED}" = "no" ] && [ -n "${LOCAL_IP}" ]; then
  echo "➕ Authorizing ${LOCAL_IP}/32..."
  gcloud sql instances patch "${DB_INSTANCE}" \
    --authorized-networks="${LOCAL_IP}/32" \
    --quiet
  echo "✅ IP authorized"
else
  echo "✅ IP already authorized"
fi

echo ""
echo "🐳 Building backend Docker image..."
cd backend
docker build --platform linux/amd64 -t claimledger-backend-test:latest . || {
  echo "❌ Docker build failed"
  exit 1
}

echo ""
echo "🧪 Testing database connection from Docker container..."

# Test connection using Python
docker run --rm \
  -e DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${PUBLIC_IP}:5432/${DB_NAME}" \
  claimledger-backend-test:latest \
  python -c "
import os
from src.database import engine, check_db_accessible
try:
    check_db_accessible()
    print('✅ Database connection successful!')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
" || {
  echo ""
  echo "❌ Connection test failed"
  echo ""
  echo "🔍 Debugging steps:"
  echo "1. Verify Cloud SQL instance is running:"
  echo "   bash scripts/gcloud-deployment.sh status cloudsql"
  echo ""
  echo "2. Check if public IP is enabled:"
  echo "   gcloud sql instances describe ${DB_INSTANCE} --format='yaml(ipAddresses)'"
  echo ""
  echo "3. Verify IP is authorized:"
  echo "   gcloud sql instances describe ${DB_INSTANCE} --format='value(settings.ipConfiguration.authorizedNetworks)'"
  echo ""
  echo "4. Test with psql directly:"
  echo "   psql -h ${PUBLIC_IP} -U ${DB_USER} -d ${DB_NAME}"
  exit 1
}

echo ""
echo "✅ All tests passed!"
