#!/bin/bash
"""
Installation script for RAG Support Client with remote Ollama.
This script handles the complete installation process when using a remote Ollama instance.
Author: Your Name
Date: December 15, 2024
"""

set -e  # Exit on error

# Import configuration
source "$(dirname "$0")/../config/install_config.sh"

# ------------------------------
# Installation Steps
# ------------------------------

echo "Starting RAG Support Client installation (Remote Ollama Configuration)..."

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
apt-get install -y "${SYSTEM_PACKAGES[@]}"

# Step 3: Create application directories
create_directories

# Step 4: Clone application (if not already present)
if [ ! -d "${INSTALL_BASE}/current" ]; then
    echo "Cloning application..."
    git clone "$(pwd)" "${INSTALL_BASE}/current"
fi

# Step 5: Create and activate virtual environment
echo "Setting up Python virtual environment..."
cd "${INSTALL_BASE}/current"
python${PYTHON_VERSION} -m venv .venv
source .venv/bin/activate

# Step 6: Install application
echo "Installing application..."
pip install --upgrade pip
pip install -e '.[dev]'

# Step 7: Setup environment file
setup_environment

# Step 8: Setup systemd services
echo "Setting up systemd services..."

# FastAPI Service
cat > /etc/systemd/system/rag-api.service << EOL
[Unit]
Description=RAG Support Client API
After=network.target

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
After=network.target

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

# Step 9: Setup Nginx configuration
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

# Step 10: Start services
echo "Starting services..."
systemctl daemon-reload
systemctl enable rag-api rag-ui
systemctl start rag-api rag-ui
systemctl restart nginx

# Step 11: Verify installation
echo "Verifying installation..."
sleep 5  # Wait for services to start

# Check if services are running
systemctl is-active --quiet rag-api && echo "API service is running" || echo "API service failed to start"
systemctl is-active --quiet rag-ui && echo "UI service is running" || echo "UI service failed to start"

echo "
Installation completed!

Services:
- API: http://localhost:${API_PORT}
- UI: http://localhost:${STREAMLIT_PORT}
- Nginx: http://${NGINX_SERVER_NAME}

Configuration files:
- Environment: ${CONFIG_BASE}/.env
- Logs: ${LOG_BASE}/
- Data: ${DATA_BASE}/

To check service status:
systemctl status rag-api
systemctl status rag-ui

To view logs:
journalctl -u rag-api
journalctl -u rag-ui
"