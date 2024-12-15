#!/bin/bash
"""
Main installation script for RAG Support Client
Orchestrates the complete installation process including configuration,
deployment type selection, SSL setup, and post-deployment tests.

Author: Oliver Marshall
Date: December 15, 2024
"""

set -e  # Exit on error

# ------------------------------
# Constants
# ------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config/install_config.sh"
INSTALL_LOG="/tmp/rag-install-$(date +%Y%m%d-%H%M%S).log"
REQUIRED_MEMORY=4096  # 4GB in MB
REQUIRED_DISK=10240   # 10GB in MB

# ------------------------------
# Helper Functions
# ------------------------------
log() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] $1" | tee -a "$INSTALL_LOG"
}

error() {
    log "ERROR: $1"
    exit 1
}

prompt_yes_no() {
    local prompt=$1
    local default=${2:-n}

    while true; do
        read -p "$prompt [y/n] ($default): " response
        response=${response:-$default}
        case $response in
            [Yy]* ) return 0;;
            [Nn]* ) return 1;;
            * ) echo "Please answer yes or no.";;
        esac
    done
}

check_system_requirements() {
    log "Checking system requirements..."

    # Check OS
    if [ ! -f /etc/debian_version ]; then
        error "This script requires Debian-based Linux"
    fi

    # Check memory
    local total_mem
    total_mem=$(free -m | awk '/^Mem:/{print $2}')
    if [ "$total_mem" -lt "$REQUIRED_MEMORY" ]; then
        error "Insufficient memory. Required: ${REQUIRED_MEMORY}MB, Available: ${total_mem}MB"
    fi

    # Check disk space
    local free_space
    free_space=$(df -m /opt | awk 'NR==2 {print $4}')
    if [ "$free_space" -lt "$REQUIRED_DISK" ]; then
        error "Insufficient disk space. Required: ${REQUIRED_DISK}MB, Available: ${free_space}MB"
    }

    # Check Python version
    if ! command -v python3.11 &> /dev/null; then
        error "Python 3.11 is required but not installed"
    }

    log "System requirements check passed"
}

configure_installation() {
    log "Configuring installation..."

    # Load or create configuration
    if [ ! -f "$CONFIG_FILE" ]; then
        error "Configuration file not found: $CONFIG_FILE"
    fi
    source "$CONFIG_FILE"

    # Prompt for missing configurations
    if [ -z "$NGINX_SERVER_NAME" ]; then
        read -p "Enter domain name for the application: " NGINX_SERVER_NAME
        export NGINX_SERVER_NAME
    fi

    if [ -z "$ADMIN_EMAIL" ]; then
        read -p "Enter admin email address: " ADMIN_EMAIL
        export ADMIN_EMAIL
    fi

    # Determine installation type if not set
    if [ -z "$OLLAMA_DEPLOYMENT" ]; then
        if prompt_yes_no "Do you want to install Ollama locally?" "n"; then
            export OLLAMA_DEPLOYMENT="local"
        else
            export OLLAMA_DEPLOYMENT="remote"
            read -p "Enter Ollama server address: " OLLAMA_HOST
            export OLLAMA_HOST
        fi
    fi

    # Configure SSL
    if [ "$SSL_ENABLED" = "true" ]; then
        if ! prompt_yes_no "SSL is enabled. Do you want to proceed with SSL setup?" "y"; then
            export SSL_ENABLED="false"
        fi
    fi
}

install_application() {
    log "Starting application installation..."

    # Select and run appropriate installation script
    local install_script
    if [ "$OLLAMA_DEPLOYMENT" = "local" ]; then
        install_script="${SCRIPT_DIR}/install_local.sh"
    else
        install_script="${SCRIPT_DIR}/install_remote.sh"
    fi

    if [ ! -f "$install_script" ]; then
        error "Installation script not found: $install_script"
    fi

    log "Running installation script: $install_script"
    if ! bash "$install_script"; then
        error "Installation failed"
    fi
}

setup_ssl() {
    if [ "$SSL_ENABLED" = "true" ]; then
        log "Setting up SSL..."
        if ! bash "${SCRIPT_DIR}/setup_ssl.sh"; then
            error "SSL setup failed"
        fi
    fi
}

run_tests() {
    log "Running post-deployment tests..."
    if ! bash "${SCRIPT_DIR}/../tests/test_deployment.sh"; then
        log "WARNING: Some tests failed. Check the logs for details."
    fi
}

generate_report() {
    local report_file="${INSTALL_LOG%.log}-report.txt"

    log "Generating installation report..."

    cat > "$report_file" << EOL
RAG Support Client Installation Report
====================================
Date: $(date)
Installation Type: ${OLLAMA_DEPLOYMENT}
SSL Enabled: ${SSL_ENABLED}

Installation Details:
-------------------
Domain: ${NGINX_SERVER_NAME}
Admin Email: ${ADMIN_EMAIL}
Install Path: ${INSTALL_BASE}
Data Path: ${DATA_BASE}
Log Path: ${LOG_BASE}

Services Status:
--------------
$(systemctl status nginx rag-api rag-ui 2>&1)

URLs:
----
API: https://${NGINX_SERVER_NAME}/api
UI: https://${NGINX_SERVER_NAME}

Next Steps:
----------
1. Monitor the logs: tail -f ${LOG_BASE}/*.log
2. Test the API: curl https://${NGINX_SERVER_NAME}/api/health
3. Access the UI: https://${NGINX_SERVER_NAME}
4. Review security settings in nginx configuration

For support:
Visit: https://github.com/espritdunet/rag-support-client
EOL

    log "Installation report generated: $report_file"
}

# ------------------------------
# Main Installation Process
# ------------------------------
log "Starting RAG Support Client installation..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    error "Please run as root"
fi

# Execute installation steps
check_system_requirements
configure_installation
install_application
setup_ssl
run_tests
generate_report

log "Installation completed successfully!"
log "Check the installation report for next steps: ${INSTALL_LOG%.log}-report.txt"
