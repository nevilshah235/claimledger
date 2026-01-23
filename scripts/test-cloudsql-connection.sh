#!/bin/bash
# Test Cloud SQL connection from local Docker container

set -euo pipefail

PROJECT_ID="claimly-484803"
REGION="us-central1"
DB_INSTANCE="claimledger-db"
DB_USER="claimledger-user"
DB_NAME="claimledger"
DB_PASSWORD="tY8mK!x2zW3@pB7q"

echo "🔍 Getting Cloud SQL connection details..."

# Get public IP (if available)
PUBLIC_IP=$(gcloud sql instances describe "${DB_INSTANCE}" \
  --format="value(ipAddresses[0].ipAddress)" 2>/dev/null || echo "")

# Get connection name
CONNECTION_NAME=$(gcloud sql instances describe "${DB_INSTANCE}" \
  --format="value(connectionName)" 2>/dev/null || echo "${PROJECT_ID}:${REGION}:${DB_INSTANCE}")

echo "📋 Connection Details:"
echo "  Connection Name: ${CONNECTION_NAME}"
if [ -n "${PUBLIC_IP}" ]; then
  echo "  Public IP: ${PUBLIC_IP}"
else
  echo "  Public IP: Not available (private IP only)"
fi

# Get local IP
LOCAL_IP=$(curl -s ifconfig.me || echo "")
echo "  Local IP: ${LOCAL_IP}"

echo ""
echo "🔐 Authorizing local IP to access Cloud SQL..."
if [ -n "${LOCAL_IP}" ]; then
  # Get current authorized networks
  CURRENT_NETWORKS=$(gcloud sql instances describe "${DB_INSTANCE}" \
    --format="value(settings.ipConfiguration.authorizedNetworks[].value)" 2>/dev/null | tr '\n' ',' || echo "")
  
  if echo "${CURRENT_NETWORKS}" | grep -q "${LOCAL_IP}"; then
    echo "  ✅ IP ${LOCAL_IP} is already authorized"
  else
    echo "  ➕ Adding ${LOCAL_IP}/32 to authorized networks..."
    gcloud sql instances patch "${DB_INSTANCE}" \
      --authorized-networks="${LOCAL_IP}/32" \
      --quiet || {
      echo "  ⚠️  Failed to authorize IP. You may need to do this manually."
      echo "  Run: gcloud sql instances patch ${DB_INSTANCE} --authorized-networks=${LOCAL_IP}/32"
    }
  fi
else
  echo "  ⚠️  Could not determine local IP. Skipping authorization."
fi

echo ""
echo "🐳 Testing connection from Docker container..."

# Create a test connection string
if [ -n "${PUBLIC_IP}" ]; then
  TEST_DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${PUBLIC_IP}:5432/${DB_NAME}"
  echo "  Using Public IP connection: postgresql://${DB_USER}:***@${PUBLIC_IP}:5432/${DB_NAME}"
else
  echo "  ⚠️  No public IP available. Testing with Cloud SQL Proxy..."
  TEST_DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@127.0.0.1:5432/${DB_NAME}"
fi

# Test with psql in Docker
docker run --rm -it \
  -e PGPASSWORD="${DB_PASSWORD}" \
  postgres:15-alpine \
  psql -h "${PUBLIC_IP:-127.0.0.1}" -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT version();" || {
  echo ""
  echo "❌ Direct connection failed. This is expected if:"
  echo "   1. Public IP is not enabled"
  echo "   2. IP is not authorized"
  echo "   3. Cloud SQL Proxy is required"
  echo ""
  echo "💡 For Cloud Run deployment, use Unix socket connection:"
  echo "   DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@/claimledger?host=/cloudsql/${CONNECTION_NAME}"
}

echo ""
echo "✅ Test complete!"
