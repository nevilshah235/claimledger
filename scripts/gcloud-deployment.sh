#!/bin/bash

# gcloud Deployment Management Script
# Manages Cloud Run service and Cloud SQL instance start/stop operations

set -euo pipefail

# Configuration - Update these if needed
PROJECT_ID="claimly-484803"
REGION="us-central1"
SERVICE_NAME="claimledger-backend"
DB_INSTANCE="claimledger-db"

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

# Set the project
set_project() {
    log_info "Setting project to ${PROJECT_ID}..."
    gcloud config set project "${PROJECT_ID}" > /dev/null 2>&1 || {
        log_error "Failed to set project. Please check your permissions."
        exit 1
    }
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
    if ! gcloud run services update "${SERVICE_NAME}" \
        --platform managed \
        --region "${REGION}" \
        --min-instances 1 \
        --max-instances 1 2>&1; then
        log_error "Failed to start Cloud Run service"
        log_info "Trying to get more details..."
        gcloud run services describe "${SERVICE_NAME}" \
            --platform managed \
            --region "${REGION}" \
            --format="value(status.conditions[0].message)" 2>&1 || true
        exit 1
    fi
    
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

# Logs functions
cloud_run_logs() {
    local limit="${1:-50}"
    log_info "Fetching Cloud Run logs (last ${limit} lines)..."
    echo ""
    gcloud run services logs read "${SERVICE_NAME}" \
        --platform managed \
        --region "${REGION}" \
        --limit "${limit}" || {
        log_error "Failed to fetch logs"
        exit 1
    }
}

cloud_sql_logs() {
    log_info "Fetching Cloud SQL logs..."
    echo ""
    gcloud sql operations list \
        --instance="${DB_INSTANCE}" \
        --limit=10 || {
        log_warning "Could not fetch Cloud SQL operations"
    }
}

# Show usage
usage() {
    cat << EOF
Usage: $0 [COMMAND] [SERVICE]

Manage Google Cloud Run and Cloud SQL deployments.

COMMANDS:
    start [service]    Start service(s)
    stop [service]     Stop service(s)
    status [service]   Check status of service(s)
    logs [service]     View logs for service(s)
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

CONFIGURATION:
    Project ID: ${PROJECT_ID}
    Region: ${REGION}
    Service: ${SERVICE_NAME}
    DB Instance: ${DB_INSTANCE}

    To change these, edit the script variables at the top.

EOF
}

# Main script logic
main() {
    check_gcloud
    check_auth
    set_project
    
    local command="${1:-help}"
    local service="${2:-all}"
    
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
        logs)
            case "${service}" in
                all|cloudrun)
                    cloud_run_logs
                    ;;
                cloudsql)
                    cloud_sql_logs
                    ;;
                *)
                    log_error "Unknown service: ${service}"
                    usage
                    exit 1
                    ;;
            esac
            ;;
        help|--help|-h)
            usage
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
