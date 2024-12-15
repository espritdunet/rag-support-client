#!/bin/bash
"""
Installation script for RAG Support Client with local Ollama.
This script handles the complete installation process including local Ollama setup.

Author: Oliver Marshall
Date: April 2024
"""

set -e  # Exit on error

# Import configuration
source "$(dirname "$0")/../config/install_config.sh"

# ------------------------------
# Installation Steps
# ------------------------------

echo "Starting RAG Support Client installation (Local Ollama Configuration)..."

# Validate configuration
validate_config

# Step 1: Create system user
echo "Creating system user..."
if ! id -u "$RAG_USER" >/dev/null 2>&1; then
    useradd -r -s /bin/false -d "$INSTALL_BASE" "$RAG_USER"
    usermod -G www-data "$RAG_USER"
fi

# Step 2: Install system dependencies
echo "Installing system dependencies..."
apt-get update
apt-get install -y "${SYSTEM_PACKAGES[@]}" "${OLLAMA_SYSTEM_PACKAGES[@]}"

# Step 3: Install Ollama
echo "Installing Ollama..."
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.ai/install.sh | sh
    # Wait for Ollama service to be available
    echo "Waiting for Ollama service to start..."
    sleep 10
fi

# Step 4: Configure Ollama system resources
echo "Configuring Ollama system resources..."
mkdir -p /etc/systemd/system/ollama.service.d/
cat > /etc/systemd/system/ollama.service.d/override.conf << EOL
[Service]
Environment="OLLAMA_HOST=127.0.0.1"
Environment="OLLAMA_MODELS_PATH=${DATA_BASE}/ollama/models"
LimitNOFILE=65535
LimitNPROC=65535
TasksMax=infinity
MemoryMax=12G
CPUQuota=800%
EOL

# Create Ollama data directory
mkdir -p "${DATA_BASE}/ollama/models"
chown -R $RAG_USER:$RAG_GROUP "${DATA_BASE}/ollama"

# Step 5: Start Ollama service
echo "Starting Ollama service..."
systemctl daemon-reload
systemctl enable ollama
systemctl restart ollama

# Step 6: Pull required models
echo "Pulling required Ollama models..."
ollama pull nomic-embed-text
echo "Waiting for model download to complete..."
sleep 30

# Step 7: Create application directories
create_directories

# Step 8: Clone application
if [ ! -d "${INSTALL_BASE}/current" ]; then
    echo "Cloning application..."
    git clone "$(pwd)" "${INSTALL_BASE}/current"
fi

# Step 9: Create and activate virtual environment
echo "Setting up Python virtual environment..."
cd "${INSTALL_BASE}/current"
python${PYTHON_VERSION} -m venv .venv
source .venv/bin/activate

# Step 10: Install application
echo "Installing application..."
pip install --upgrade pip
pip install -e '.[dev]'

# Step 11: Setup environment file
setup_environment

# Update .env with local Ollama settings
sed -i "s#OLLAMA_BASE_URL=.*#OLLAMA_BASE_URL=http://127.0.0.1:11434#g" "${CONFIG_BASE}/.env"

# Step 12: Setup systemd services
echo "Setting up systemd services..."

# FastAPI Service
cat > /etc/systemd/system/rag-api.service << EOL
[Unit]
Description=RAG Support Client API
After=ollama.service
Requires=ollama.service

[Service]
User=${RAG_USER}
Group=${RAG_GROUP}
WorkingDirectory=${INSTALL_BASE}/current
Environment="PATH=${INSTALL_BASE}/current/.venv/bin"
EnvironmentFile=${CONFIG_BASE}/.env
ExecStart=${INSTALL_BASE}/current/.venv/bin/uvicorn rag_support_client.api.main:app --host ${API_HOST} --port ${API_PORT}
Restart=always

[Install]
WantedBy=multi-user.target
EOL

# Streamlit Service
cat > /etc/systemd/system/rag-ui.service << EOL
[Unit]
Description=RAG Support Client UI
After=ollama.service
Requires=ollama.service

[Service]
User=${RAG_USER}
Group=${RAG_GROUP}
WorkingDirectory=${INSTALL_BASE}/current
Environment="PATH=${INSTALL_BASE}/current/.venv/bin"
EnvironmentFile=${CONFIG_BASE}/.env
ExecStart=${INSTALL_BASE}/current/.venv/bin/streamlit run rag_support_client/streamlit/app.py --server.port ${STREAMLIT_PORT} --server.address ${STREAMLIT_HOST}
Restart=always

[Install]
WantedBy=multi-user.target
EOL

# Step 13: Setup Nginx configuration
echo "Setting up Nginx configuration..."
cat > /etc/nginx/sites-available/rag-support << EOL
server {
    listen 80;
    server_name ${NGINX_SERVER_NAME};

    # API
    location /api {
        proxy_pass http://localhost:${API_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    # Streamlit UI
    location / {
        proxy_pass http://localhost:${STREAMLIT_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOL

# Enable site
ln -sf /etc/nginx/sites-available/rag-support /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Step 14: Start services
echo "Starting services..."
systemctl daemon-reload
systemctl enable rag-api rag-ui
systemctl start rag-api rag-ui
systemctl restart nginx

# Step 15: Verify installation
echo "Verifying installation..."
sleep 5  # Wait for services to start

# Check if services are running
echo "Checking Ollama service..."
if ! systemctl is-active --quiet ollama; then
    echo "ERROR: Ollama service failed to start"
    journalctl -u ollama -n 50
    exit 1
fi

echo "Checking API service..."
if ! systemctl is-active --quiet rag-api; then
    echo "ERROR: API service failed to start"
    journalctl -u rag-api -n 50
    exit 1
fi

echo "Checking UI service..."
if ! systemctl is-active --quiet rag-ui; then
    echo "ERROR: UI service failed to start"
    journalctl -u rag-ui -n 50
    exit 1
fi

echo "
Installation completed successfully!

Services:
- Ollama: http://localhost:11434
- API: http://localhost:${API_PORT}
- UI: http://localhost:${STREAMLIT_PORT}
- Nginx: http://${NGINX_SERVER_NAME}

Configuration files:
- Environment: ${CONFIG_BASE}/.env
- Logs: ${LOG_BASE}/
- Data: ${DATA_BASE}/
- Ollama Models: ${DATA_BASE}/ollama/models

To check service status:
systemctl status ollama
systemctl status rag-api
systemctl status rag-ui

To view logs:
journalctl -u ollama
journalctl -u rag-api
journalctl -u rag-ui
"
