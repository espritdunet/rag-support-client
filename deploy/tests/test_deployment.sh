#!/bin/bash
"""
Post-deployment test script for RAG Support Client
Validates installation and configuration of all components.

Author: Oliver Marshall
Date: December 15, 2024
"""

set -e  # Exit on error

# Import configuration
source "$(dirname "$0")/../config/install_config.sh"

# ------------------------------
# Helper Functions
# ------------------------------
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    log "ERROR: $1"
    exit 1
}

check_service() {
    local service=$1
    log "Checking service: $service"
    if ! systemctl is-active --quiet "$service"; then
        error "Service $service is not running"
    fi
    log "Service $service is running"

    # Check last 10 lines of service logs for errors
    log "Checking logs for $service"
    if journalctl -u "$service" -n 10 | grep -i "error"; then
        log "WARNING: Found errors in $service logs"
    fi
}

check_port() {
    local port=$1
    local service=$2
    log "Checking port $port for $service"
    if ! netstat -tuln | grep ":$port " > /dev/null; then
        error "Port $port is not open for $service"
    fi
    log "Port $port is open for $service"
}

check_http_endpoint() {
    local url=$1
    local name=$2
    log "Testing HTTP endpoint: $url ($name)"
    local response
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    if [ "$response" != "200" ]; then
        error "$name endpoint returned $response"
    fi
    log "$name endpoint is responding correctly"
}

check_permissions() {
    local path=$1
    local expected_user=$2
    local expected_group=$3
    log "Checking permissions for $path"

    if [ ! -e "$path" ]; then
        error "Path $path does not exist"
    fi

    local actual_user
    actual_user=$(stat -c '%U' "$path")
    if [ "$actual_user" != "$expected_user" ]; then
        error "Wrong user for $path: expected $expected_user, got $actual_user"
    fi

    local actual_group
    actual_group=$(stat -c '%G' "$path")
    if [ "$actual_group" != "$expected_group" ]; then
        error "Wrong group for $path: expected $expected_group, got $actual_group"
    }

    log "Permissions for $path are correct"
}

# ------------------------------
# Main Tests
# ------------------------------
log "Starting deployment tests..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    error "Please run as root"
fi

# 1. Check Services
log "Testing systemd services..."
check_service "nginx"
check_service "rag-api"
check_service "rag-ui"
if [ "$OLLAMA_DEPLOYMENT" = "local" ]; then
    check_service "ollama"
fi

# 2. Check Ports
log "Testing network ports..."
check_port "80" "nginx"
check_port "443" "nginx"
check_port "$API_PORT" "rag-api"
check_port "$STREAMLIT_PORT" "rag-ui"
if [ "$OLLAMA_DEPLOYMENT" = "local" ]; then
    check_port "11434" "ollama"
fi

# 3. Check File Permissions
log "Testing file permissions..."
check_permissions "$INSTALL_BASE" "$RAG_USER" "$RAG_GROUP"
check_permissions "$DATA_BASE" "$RAG_USER" "$RAG_GROUP"
check_permissions "$LOG_BASE" "$RAG_USER" "$RAG_GROUP"
check_permissions "$CONFIG_BASE" "$RAG_USER" "$RAG_GROUP"

# 4. Check Log Files
log "Testing log files..."
for log_file in "$LOG_BASE"/*.log; do
    if [ ! -f "$log_file" ]; then
        error "Log file $log_file does not exist"
    fi
    if [ ! -w "$log_file" ]; then
        error "Log file $log_file is not writable"
    fi
done

# 5. Check HTTP Endpoints
log "Testing HTTP endpoints..."
# Wait for services to be fully ready
sleep 5

# Test API health endpoint
check_http_endpoint "http://localhost:${API_PORT}/api/health" "API Health"

# Test Streamlit
check_http_endpoint "http://localhost:${STREAMLIT_PORT}/_stcore/health" "Streamlit Health"

# 6. Check Ollama Connection
log "Testing Ollama connection..."
if ! curl -s "${OLLAMA_BASE_URL}/api/version" > /dev/null; then
    error "Cannot connect to Ollama at ${OLLAMA_BASE_URL}"
fi

# 7. Check SSL Configuration (if enabled)
if [ "$SSL_ENABLED" = "true" ]; then
    log "Testing SSL configuration..."
    if ! openssl s_client -connect "${NGINX_SERVER_NAME}:443" < /dev/null 2>&1 | grep -q "Verify return code: 0"; then
        log "WARNING: SSL verification failed"
    fi
fi

# 8. Check Environment Configuration
log "Testing environment configuration..."
if [ ! -f "${CONFIG_BASE}/.env" ]; then
    error "Environment file not found"
fi

# 9. Check Python Environment
log "Testing Python environment..."
if ! "${INSTALL_BASE}/current/.venv/bin/python" -c "import langchain; import chromadb; import ollama" 2>/dev/null; then
    error "Required Python packages are not properly installed"
fi

# 10. Check Data Directories
log "Testing data directories..."
required_dirs=(
    "${DATA_BASE}/raw"
    "${DATA_BASE}/processed"
    "${DATA_BASE}/vector_store"
)

for dir in "${required_dirs[@]}"; do
    if [ ! -d "$dir" ]; then
        error "Required directory $dir does not exist"
    fi
done

# Final Status Report
log "
Deployment Test Results:
----------------------
✓ Systemd Services
✓ Network Ports
✓ File Permissions
✓ Log Files
✓ HTTP Endpoints
✓ Ollama Connection
✓ SSL Configuration
✓ Environment Configuration
✓ Python Environment
✓ Data Directories

All tests completed successfully!

Next steps:
1. Monitor the logs: tail -f ${LOG_BASE}/*.log
2. Check metrics: systemctl status rag-api rag-ui
3. Test the UI: https://${NGINX_SERVER_NAME}
4. Test the API: https://${NGINX_SERVER_NAME}/api/docs
"
