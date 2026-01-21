#!/bin/bash

# gcloud Deployment Management Script
# Manages Cloud Run service and Cloud SQL instance start/stop operations

set -euo pipefail

# Configuration - Update these if needed
PROJECT_ID="${PROJECT_ID:-claimly-484803}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-claimledger-backend}"
DB_INSTANCE="${DB_INSTANCE:-claimledger-db}"

# Deployment configuration
BACKEND_DIR="${BACKEND_DIR:-backend}"
REGISTRY="${REGISTRY:-gcr.io}"
IMAGE_NAME="${IMAGE_NAME:-${SERVICE_NAME}}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
PLATFORM="${PLATFORM:-linux/amd64}"
ENV_VARS_FILE="${ENV_VARS_FILE:-backend/.env.production.yaml}"

# Cloud Run deploy defaults (override via env vars if needed)
CLOUD_RUN_PORT="${CLOUD_RUN_PORT:-8080}"
CLOUD_RUN_MEMORY="${CLOUD_RUN_MEMORY:-1Gi}"
CLOUD_RUN_CPU="${CLOUD_RUN_CPU:-1}"
CLOUD_RUN_TIMEOUT="${CLOUD_RUN_TIMEOUT:-300}"
CLOUD_RUN_MAX_INSTANCES="${CLOUD_RUN_MAX_INSTANCES:-1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

run_cmd() {
    # Usage: run_cmd <command...>
    if [ "${DRY_RUN:-0}" -eq 1 ]; then
        echo "[DRY-RUN] $*"
        return 0
    fi
    "$@"
}

run_cmd_capture() {
    # Usage: run_cmd_capture <command...>
    # Prints command output to stdout, still respects DRY_RUN.
    if [ "${DRY_RUN:-0}" -eq 1 ]; then
        echo ""
        return 0
    fi
    "$@"
}

# Check if gcloud is installed
check_gcloud() {
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed. Please install it first:"
        echo "  brew install --cask google-cloud-sdk"
        exit 1
    fi
}

# Check if user is authenticated
check_auth() {
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log_error "Not authenticated with gcloud. Please run:"
        echo "  gcloud auth login"
        exit 1
    fi
}

check_docker() {
    if [ "${DRY_RUN:-0}" -eq 1 ]; then
        # In dry-run, avoid requiring a running daemon.
        if ! command -v docker &> /dev/null; then
            log_error "Docker is not installed. Please install Docker Desktop first."
            exit 1
        fi
        return 0
    fi
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker Desktop first."
        exit 1
    fi
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker daemon is not running. Please start Docker Desktop."
        exit 1
    fi
}

validate_env_vars_file() {
    if [ ! -f "${ENV_VARS_FILE}" ]; then
        log_error "Env vars file not found: ${ENV_VARS_FILE}"
        echo "  Expected a YAML file with entries like: KEY: \"value\""
        exit 1
    fi

    # Minimal format sanity check for YAML: look for at least one non-comment line containing ':'
    case "${ENV_VARS_FILE}" in
        *.yml|*.yaml)
            if ! grep -E '^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*[[:space:]]*:' "${ENV_VARS_FILE}" > /dev/null 2>&1; then
                log_error "Env vars YAML doesn't look valid: ${ENV_VARS_FILE}"
                echo "  Expected lines like: KEY: \"value\""
                exit 1
            fi
            ;;
        *)
            log_warning "Env vars file is not .yml/.yaml; continuing anyway: ${ENV_VARS_FILE}"
            ;;
    esac
}

# Set the project
set_project() {
    log_info "Setting project to ${PROJECT_ID}..."
    gcloud config set project "${PROJECT_ID}" > /dev/null 2>&1 || {
        log_error "Failed to set project. Please check your permissions."
        exit 1
    }
}

# Image helpers
local_image_ref() {
    echo "${IMAGE_NAME}:${IMAGE_TAG}"
}

remote_image_ref() {
    echo "${REGISTRY}/${PROJECT_ID}/${IMAGE_NAME}:${IMAGE_TAG}"
}

docker_build_image() {
    log_info "Building Docker image (${PLATFORM}) from ${BACKEND_DIR}..."
    if [ ! -d "${BACKEND_DIR}" ]; then
        log_error "Backend directory not found: ${BACKEND_DIR}"
        exit 1
    fi
    if [ ! -f "${BACKEND_DIR}/Dockerfile" ]; then
        log_error "Dockerfile not found: ${BACKEND_DIR}/Dockerfile"
        exit 1
    fi

    run_cmd docker build \
        --platform "${PLATFORM}" \
        -t "$(local_image_ref)" \
        "${BACKEND_DIR}"
    log_success "Built $(local_image_ref)"
}

docker_tag_image() {
    log_info "Tagging image for registry..."
    run_cmd docker tag "$(local_image_ref)" "$(remote_image_ref)"
    log_success "Tagged $(remote_image_ref)"
}

docker_configure_registry_auth() {
    log_info "Configuring Docker auth for ${REGISTRY}..."
    # Prefer scoping to a single registry to avoid long credHelpers lists.
    run_cmd gcloud auth configure-docker "${REGISTRY}"
}

docker_push_image() {
    log_info "Pushing image to registry..."
    run_cmd docker push "$(remote_image_ref)"
    log_success "Pushed $(remote_image_ref)"
}

resolve_cloudsql_connection_name() {
    if [ "${DRY_RUN:-0}" -eq 1 ]; then
        # In dry-run, avoid calling gcloud at all.
        echo "PROJECT:REGION:${DB_INSTANCE}"
        return 0
    fi
    log_info "Resolving Cloud SQL connection name for ${DB_INSTANCE}..."
    if ! gcloud sql instances describe "${DB_INSTANCE}" > /dev/null 2>&1; then
        log_error "Cloud SQL instance not found: ${DB_INSTANCE}"
        exit 1
    fi

    local connection_name
    connection_name="$(run_cmd_capture gcloud sql instances describe "${DB_INSTANCE}" --format="value(connectionName)" | tr -d '\r')"
    if [ -z "${connection_name}" ] && [ "${DRY_RUN:-0}" -ne 1 ]; then
        log_error "Failed to resolve Cloud SQL connection name for ${DB_INSTANCE}"
        exit 1
    fi
    echo "${connection_name}"
}

cloud_run_deploy() {
    validate_env_vars_file

    local connection_name
    connection_name="$(resolve_cloudsql_connection_name)"

    log_info "Deploying ${SERVICE_NAME} to Cloud Run (${REGION})..."
    run_cmd gcloud run deploy "${SERVICE_NAME}" \
        --image "$(remote_image_ref)" \
        --platform managed \
        --region "${REGION}" \
        --allow-unauthenticated \
        --port "${CLOUD_RUN_PORT}" \
        --memory "${CLOUD_RUN_MEMORY}" \
        --cpu "${CLOUD_RUN_CPU}" \
        --timeout "${CLOUD_RUN_TIMEOUT}" \
        --max-instances "${CLOUD_RUN_MAX_INSTANCES}" \
        --add-cloudsql-instances "${connection_name}" \
        --env-vars-file "${ENV_VARS_FILE}"

    log_success "Deployed ${SERVICE_NAME}"
}

# Cloud Run Functions
cloud_run_status() {
    log_info "Checking Cloud Run service status..."
    if gcloud run services describe "${SERVICE_NAME}" \
        --platform managed \
        --region "${REGION}" \
        --format="value(status.conditions[0].status)" 2>/dev/null | grep -q "True"; then
        local url=$(gcloud run services describe "${SERVICE_NAME}" \
            --platform managed \
            --region "${REGION}" \
            --format="value(status.url)" 2>/dev/null)
        local instances=$(gcloud run services describe "${SERVICE_NAME}" \
            --platform managed \
            --region "${REGION}" \
            --format="value(spec.template.spec.containerConcurrency)" 2>/dev/null || echo "N/A")
        log_success "Cloud Run service is RUNNING"
        echo "  URL: ${url}"
        echo "  Region: ${REGION}"
        return 0
    else
        log_warning "Cloud Run service status unknown or not found"
        return 1
    fi
}

cloud_run_start() {
    log_info "Starting Cloud Run service..."
    
    # Check if service exists
    if ! gcloud run services describe "${SERVICE_NAME}" \
        --platform managed \
        --region "${REGION}" > /dev/null 2>&1; then
        log_error "Service ${SERVICE_NAME} not found. Please deploy it first."
        echo "  Run: gcloud run deploy ${SERVICE_NAME} ..."
        exit 1
    fi
    
    # Scale to minimum 1 instance (ensures service is available)
    log_info "Scaling service to minimum 1 instance..."
    gcloud run services update "${SERVICE_NAME}" \
        --platform managed \
        --region "${REGION}" \
        --min-instances 1 \
        --max-instances 1 > /dev/null 2>&1 || {
        log_error "Failed to start Cloud Run service"
        exit 1
    }
    
    log_success "Cloud Run service started"
    cloud_run_status
}

cloud_run_stop() {
    log_info "Stopping Cloud Run service (scaling to zero)..."
    
    # Check if service exists
    if ! gcloud run services describe "${SERVICE_NAME}" \
        --platform managed \
        --region "${REGION}" > /dev/null 2>&1; then
        log_warning "Service ${SERVICE_NAME} not found"
        return 0
    fi
    
    # Scale to zero instances (service will scale to zero when idle)
    gcloud run services update "${SERVICE_NAME}" \
        --platform managed \
        --region "${REGION}" \
        --min-instances 0 \
        --max-instances 0 > /dev/null 2>&1 || {
        log_error "Failed to stop Cloud Run service"
        exit 1
    }
    
    log_success "Cloud Run service stopped (scaled to zero)"
    log_info "Note: Cloud Run will automatically scale to zero when idle, saving costs"
}

# Cloud SQL Functions
cloud_sql_status() {
    log_info "Checking Cloud SQL instance status..."
    local state=$(gcloud sql instances describe "${DB_INSTANCE}" \
        --format="value(state)" 2>/dev/null || echo "NOT_FOUND")
    
    case "${state}" in
        "RUNNABLE")
            log_success "Cloud SQL instance is RUNNING"
            local connection=$(gcloud sql instances describe "${DB_INSTANCE}" \
                --format="value(connectionName)" 2>/dev/null)
            echo "  Connection: ${connection}"
            return 0
            ;;
        "SUSPENDED")
            log_warning "Cloud SQL instance is SUSPENDED"
            return 1
            ;;
        "NOT_FOUND")
            log_warning "Cloud SQL instance not found"
            return 1
            ;;
        *)
            log_warning "Cloud SQL instance state: ${state}"
            return 1
            ;;
    esac
}

cloud_sql_start() {
    log_info "Starting Cloud SQL instance..."
    
    # Check if instance exists
    if ! gcloud sql instances describe "${DB_INSTANCE}" > /dev/null 2>&1; then
        log_error "Cloud SQL instance ${DB_INSTANCE} not found. Please create it first."
        echo "  See: docs/VERCEL_CLOUD_RUN_DEPLOYMENT.md"
        exit 1
    fi
    
    # Activate the instance
    gcloud sql instances patch "${DB_INSTANCE}" \
        --activation-policy ALWAYS > /dev/null 2>&1 || {
        log_error "Failed to start Cloud SQL instance"
        exit 1
    }
    
    log_success "Cloud SQL instance started"
    log_info "Waiting for instance to be ready (this may take a minute)..."
    
    # Wait for instance to be ready
    local max_attempts=30
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        local state=$(gcloud sql instances describe "${DB_INSTANCE}" \
            --format="value(state)" 2>/dev/null)
        if [ "${state}" = "RUNNABLE" ]; then
            log_success "Cloud SQL instance is ready"
            cloud_sql_status
            return 0
        fi
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    echo ""
    log_warning "Instance may still be starting. Check status with: $0 status"
}

cloud_sql_stop() {
    log_info "Stopping Cloud SQL instance..."
    
    # Check if instance exists
    if ! gcloud sql instances describe "${DB_INSTANCE}" > /dev/null 2>&1; then
        log_warning "Cloud SQL instance not found"
        return 0
    fi
    
    # Suspend the instance (saves costs)
    gcloud sql instances patch "${DB_INSTANCE}" \
        --activation-policy NEVER > /dev/null 2>&1 || {
        log_error "Failed to stop Cloud SQL instance"
        exit 1
    }
    
    log_success "Cloud SQL instance stopped (suspended)"
    log_info "Note: Suspended instances are not charged for compute, only storage"
}

# Main functions
start_all() {
    log_info "Starting all services..."
    echo ""
    cloud_sql_start
    echo ""
    cloud_run_start
    echo ""
    log_success "All services started"
}

stop_all() {
    log_info "Stopping all services..."
    echo ""
    cloud_run_stop
    echo ""
    cloud_sql_stop
    echo ""
    log_success "All services stopped"
}

status_all() {
    log_info "Checking status of all services..."
    echo ""
    echo "=== Cloud SQL Instance ==="
    cloud_sql_status || true
    echo ""
    echo "=== Cloud Run Service ==="
    cloud_run_status || true
    echo ""
}

build_only() {
    check_docker
    docker_build_image
}

push_only() {
    check_docker
    docker_tag_image
    docker_configure_registry_auth
    docker_push_image
}

deploy_only() {
    cloud_run_deploy
}

deploy_all() {
    check_docker
    docker_build_image
    docker_tag_image
    docker_configure_registry_auth
    docker_push_image
    cloud_run_deploy
}

# Show usage
usage() {
    cat << EOF
Usage: $0 [--dry-run] [COMMAND] [SERVICE]

Manage Google Cloud Run and Cloud SQL deployments.

COMMANDS:
    start [service]    Start service(s)
    stop [service]     Stop service(s)
    status [service]   Check status of service(s)
    build              Build backend Docker image (local)
    push               Tag + authenticate + push image to registry
    deploy-only        Deploy Cloud Run using already-pushed image
    deploy             Build + push + deploy Cloud Run
    help               Show this help message

SERVICES:
    all                All services (default)
    cloudrun           Cloud Run service only
    cloudsql           Cloud SQL instance only

EXAMPLES:
    $0 start              # Start all services
    $0 stop               # Stop all services
    $0 status             # Check status of all services
    $0 start cloudrun     # Start only Cloud Run service
    $0 stop cloudsql      # Stop only Cloud SQL instance
    $0 status cloudrun    # Check Cloud Run status only
    $0 deploy             # Build + push + deploy backend to Cloud Run
    $0 --dry-run deploy   # Print commands without executing

CONFIGURATION:
    Project ID: ${PROJECT_ID}
    Region: ${REGION}
    Service: ${SERVICE_NAME}
    DB Instance: ${DB_INSTANCE}
    Backend Dir: ${BACKEND_DIR}
    Registry: ${REGISTRY}
    Image: $(remote_image_ref)
    Platform: ${PLATFORM}
    Env Vars File: ${ENV_VARS_FILE}

    To change these, edit the script variables at the top or override via env vars:
      PROJECT_ID=... REGION=... SERVICE_NAME=... DB_INSTANCE=...
      IMAGE_TAG=... ENV_VARS_FILE=... PLATFORM=...

EOF
}

# Main script logic
main() {
    DRY_RUN=0
    if [ "${1:-}" = "--dry-run" ]; then
        DRY_RUN=1
        shift
    fi

    local command="${1:-help}"
    local service="${2:-all}"

    # Help should be usable without any cloud setup.
    if [ "${command}" = "help" ] || [ "${command}" = "--help" ] || [ "${command}" = "-h" ]; then
        usage
        return 0
    fi

    check_gcloud
    # In dry-run we avoid touching user gcloud config/credentials.
    if [ "${DRY_RUN:-0}" -ne 1 ]; then
        check_auth
        set_project
    fi
    
    case "${command}" in
        start)
            case "${service}" in
                all)
                    start_all
                    ;;
                cloudrun)
                    cloud_run_start
                    ;;
                cloudsql)
                    cloud_sql_start
                    ;;
                *)
                    log_error "Unknown service: ${service}"
                    usage
                    exit 1
                    ;;
            esac
            ;;
        stop)
            case "${service}" in
                all)
                    stop_all
                    ;;
                cloudrun)
                    cloud_run_stop
                    ;;
                cloudsql)
                    cloud_sql_stop
                    ;;
                *)
                    log_error "Unknown service: ${service}"
                    usage
                    exit 1
                    ;;
            esac
            ;;
        status)
            case "${service}" in
                all)
                    status_all
                    ;;
                cloudrun)
                    cloud_run_status || true
                    ;;
                cloudsql)
                    cloud_sql_status || true
                    ;;
                *)
                    log_error "Unknown service: ${service}"
                    usage
                    exit 1
                    ;;
            esac
            ;;
        build)
            build_only
            ;;
        push)
            push_only
            ;;
        deploy-only)
            deploy_only
            ;;
        deploy)
            deploy_all
            ;;
        *)
            log_error "Unknown command: ${command}"
            usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
