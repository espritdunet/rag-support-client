#!/bin/bash

# Script to manage Docker operations for RAG Support Client
# Usage: ./docker-manage.sh [command] [config]
# config: local (with Ollama) or remote (external Ollama)

set -e

# Change to project root directory (since script is in /scripts)
cd "$(dirname "$0")/.."

# Configuration variables
APP_NAME="rag-support"
BACKUP_DIR="./data/backups"
COMPOSE_FILE="docker-compose.yml"
COMPOSE_FILE_REMOTE="docker-compose.external-ollama.yml"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running or you don't have permissions"
        exit 1
    fi
}

# Select compose file based on configuration
get_compose_file() {
    local config=$1
    if [ "$config" == "remote" ]; then
        echo $COMPOSE_FILE_REMOTE
    else
        echo $COMPOSE_FILE
    fi
}

# Create backup of data
backup() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="${BACKUP_DIR}/backup_${timestamp}.tar.gz"

    log_info "Creating backup in ${backup_file}..."
    mkdir -p "${BACKUP_DIR}"
    tar -czf "${backup_file}" ./data/vector_store ./data/processed ./data/cache
    log_info "Backup completed successfully"
}

# Main command handler
case "$1" in
    start)
        check_docker
        compose_file=$(get_compose_file $2)
        log_info "Starting services using ${compose_file}..."
        docker compose -f ${compose_file} up -d
        log_info "Services started successfully"
        ;;

    stop)
        check_docker
        compose_file=$(get_compose_file $2)
        log_info "Stopping services..."
        docker compose -f ${compose_file} down
        log_info "Services stopped successfully"
        ;;

    restart)
        check_docker
        compose_file=$(get_compose_file $2)
        log_info "Restarting services..."
        docker compose -f ${compose_file} restart
        log_info "Services restarted successfully"
        ;;

    update)
        check_docker
        compose_file=$(get_compose_file $2)
        log_info "Creating backup before update..."
        backup
        log_info "Updating services..."
        docker compose -f ${compose_file} down
        docker compose -f ${compose_file} pull
        docker compose -f ${compose_file} build --no-cache
        docker compose -f ${compose_file} up -d
        log_info "Update completed successfully"
        ;;

    logs)
        check_docker
        compose_file=$(get_compose_file $2)
        log_info "Showing logs..."
        docker compose -f ${compose_file} logs -f
        ;;

    backup)
        log_info "Starting backup..."
        backup
        ;;

    status)
        check_docker
        compose_file=$(get_compose_file $2)
        log_info "Checking service status..."
        docker compose -f ${compose_file} ps
        ;;

    *)
        echo "Usage: $0 {start|stop|restart|update|logs|backup|status} [local|remote]"
        echo "Examples:"
        echo "  $0 start local    # Start services with local Ollama"
        echo "  $0 start remote   # Start services with remote Ollama"
        echo "  $0 update local   # Update services with local Ollama"
        echo "  $0 logs remote    # Show logs for remote configuration"
        exit 1
        ;;
esac

exit 0
