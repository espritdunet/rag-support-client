#!/bin/bash
"""
Configuration script for RAG Support Client deployment.
This script defines all necessary variables and functions for installation.
Author: Oliver Marshall
Date: December 15, 2024
"""

# ------------------------------
# System Configuration
# ------------------------------
# Application user and group
RAG_USER="rag-service"
RAG_GROUP="rag-service"

# Installation paths
INSTALL_BASE="/opt/rag-support"
DATA_BASE="/var/lib/rag-support"
LOG_BASE="/var/log/rag-support"
CONFIG_BASE="/etc/rag-support"

# Python version
PYTHON_VERSION="3.11"

# ------------------------------
# Service Configuration
# ------------------------------
# FastAPI Service
API_PORT="8000"
API_HOST="0.0.0.0"

# Streamlit Service
STREAMLIT_PORT="8501"
STREAMLIT_HOST="0.0.0.0"

# ------------------------------
# Ollama Configuration
# ------------------------------
# Deployment type: "remote" or "local"
OLLAMA_DEPLOYMENT="remote"

# Remote Ollama settings (used when OLLAMA_DEPLOYMENT="remote")
OLLAMA_HOST="your-ollama-server.domain"
OLLAMA_PORT="11434"
OLLAMA_BASE_URL="http://${OLLAMA_HOST}:${OLLAMA_PORT}"

# ------------------------------
# Security Configuration
# ------------------------------
# Generate random API key if not provided
if [ -z "$API_KEY" ]; then
    API_KEY=$(openssl rand -hex 32)
fi

# ------------------------------
# Nginx Configuration
# ------------------------------
NGINX_SERVER_NAME="rag-support.yourdomain.com"
SSL_ENABLED="true"

# ------------------------------
# Dependencies
# ------------------------------
SYSTEM_PACKAGES=(
    "python${PYTHON_VERSION}"
    "python${PYTHON_VERSION}-venv"
    "python3-pip"
    "nginx"
    "git"
    "curl"
    "supervisor"
)

# Additional packages for local Ollama deployment
OLLAMA_SYSTEM_PACKAGES=(
    "cmake"
    "make"
    "gcc"
)

# ------------------------------
# Utility Functions
# ------------------------------

# Function to validate configuration
validate_config() {
    echo "Validating configuration..."

    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        echo "Error: Please run as root"
        exit 1
    fi

    # Check if essential directories can be created
    for dir in "$INSTALL_BASE" "$DATA_BASE" "$LOG_BASE" "$CONFIG_BASE"; do
        if [ ! -w "$(dirname "$dir")" ]; then
            echo "Error: Cannot create directory $dir (permission denied)"
            exit 1
        fi
    done

    # Validate Ollama configuration
    if [ "$OLLAMA_DEPLOYMENT" = "remote" ]; then
        echo "Testing connection to Ollama at $OLLAMA_BASE_URL..."
        if ! curl -s -f "$OLLAMA_BASE_URL/api/version" > /dev/null; then
            echo "Warning: Cannot connect to Ollama at $OLLAMA_BASE_URL"
            read -p "Continue anyway? (y/N) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    fi

    # Validate Python version
    if ! command -v "python${PYTHON_VERSION}" &> /dev/null; then
        echo "Error: Python ${PYTHON_VERSION} not available"
        exit 1
    fi

    echo "Configuration validation completed successfully"
}

# Function to create necessary directories
create_directories() {
    echo "Creating necessary directories..."

    for dir in "$INSTALL_BASE" "$DATA_BASE" "$LOG_BASE" "$CONFIG_BASE"; do
        mkdir -p "$dir"
        chown -R $RAG_USER:$RAG_GROUP "$dir"
        chmod 750 "$dir"
    done
}

# Function to setup environment file
setup_environment() {
    echo "Setting up environment file..."

    # Create environment file
    ENV_FILE="${CONFIG_BASE}/.env"
    cp .env-example "$ENV_FILE"

    # Update environment file with installation-specific values
    sed -i "s#LOG_FILE=.*#LOG_FILE=${LOG_BASE}/app.log#g" "$ENV_FILE"
    sed -i "s#CHROMA_PERSIST_DIRECTORY=.*#CHROMA_PERSIST_DIRECTORY=${DATA_BASE}/vector_store#g" "$ENV_FILE"
    sed -i "s#DATA_DIR=.*#DATA_DIR=${DATA_BASE}#g" "$ENV_FILE"
    sed -i "s#RAW_DIR=.*#RAW_DIR=${DATA_BASE}/raw#g" "$ENV_FILE"
    sed -i "s#PROCESSED_DIR=.*#PROCESSED_DIR=${DATA_BASE}/processed#g" "$ENV_FILE"
    sed -i "s#MARKDOWN_DIR=.*#MARKDOWN_DIR=${DATA_BASE}/raw#g" "$ENV_FILE"

    # Set correct permissions
    chown $RAG_USER:$RAG_GROUP "$ENV_FILE"
    chmod 640 "$ENV_FILE"
}

# Export all variables for child scripts
export RAG_USER RAG_GROUP
export INSTALL_BASE DATA_BASE LOG_BASE CONFIG_BASE
export PYTHON_VERSION
export API_PORT API_HOST
export STREAMLIT_PORT STREAMLIT_HOST
export OLLAMA_DEPLOYMENT OLLAMA_BASE_URL
export API_KEY
export NGINX_SERVER_NAME SSL_ENABLED