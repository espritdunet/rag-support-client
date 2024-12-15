#!/bin/bash
"""
RAG Support Client - One-click Deployment Script
Installs and configures the complete RAG Support Client with security best practices.

Usage: sudo ./deploy.sh
Requirements: Debian/Ubuntu based system
Author: Oliver Marshall
Date: December 15, 2024
"""

set -e

# ------------------------------
# Interactive Configuration
# ------------------------------
echo "RAG Support Client - Installation"
echo "--------------------------------"

# Essential information gathering
read -p "Domain name (e.g., rag.example.com): " DOMAIN
read -p "Install Ollama locally? (y/n): " OLLAMA_LOCAL
if [ "$OLLAMA_LOCAL" != "y" ]; then
    read -p "Remote Ollama URL: " OLLAMA_URL
fi
read -p "Enable HTTPS/SSL? (y/n): " SSL_ENABLE

# ------------------------------
# Installation
# ------------------------------
echo "Starting installation..."

# Root check
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Dependencies installation
echo "Installing system dependencies..."
apt-get update
apt-get install -y python3.11 python3.11-venv nginx certbot python3-certbot-nginx git

# Create service user
echo "Creating service user..."
useradd -r -s /bin/false -d /opt/rag-support rag 2>/dev/null || true

# Ollama installation if local
if [ "$OLLAMA_LOCAL" = "y" ]; then
    echo "Installing Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh
    systemctl enable --now ollama
    ollama pull nomic-embed-text
    OLLAMA_URL="http://localhost:11434"
fi

# Base directory setup
echo "Setting up directories..."
mkdir -p /opt/rag-support/{data,logs,config}
chown -R rag:rag /opt/rag-support

# Application installation
echo "Installing RAG Support Client..."
echo "Copying application files..."
cp -r $(dirname "$(dirname "$(readlink -f "$0")")") /opt/rag-support/current
cd /opt/rag-support/current
python3.11 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install .

# Set correct permissions
echo "Setting correct permissions..."
chown -R rag:rag /opt/rag-support
chmod -R 755 /opt/rag-support/current

# Environment configuration
echo "Configuring environment..."
cat > /opt/rag-support/config/.env << EOL
OLLAMA_BASE_URL=${OLLAMA_URL}
API_HOST=127.0.0.1
API_PORT=8000
STREAMLIT_HOST=127.0.0.1
STREAMLIT_PORT=8501
DATA_PATH=/opt/rag-support/data
EOL

## Systemd services setup
echo "Setting up systemd services..."
cat > /etc/systemd/system/rag-api.service << EOL
[Unit]
Description=RAG Support Client API
After=network.target
[Service]
User=rag
Group=rag
WorkingDirectory=/opt/rag-support/current
Environment="PATH=/opt/rag-support/current/.venv/bin"
Environment="PYTHONPATH=/opt/rag-support/current"
EnvironmentFile=/opt/rag-support/config/.env
ExecStart=/opt/rag-support/current/.venv/bin/uvicorn src.rag_support_client.api.main:app --host \${API_HOST} --port \${API_PORT}
Restart=always
# Security
PrivateTmp=true
ProtectSystem=full
NoNewPrivileges=true
# Resource limits
LimitNOFILE=65535
MemoryLimit=2G
[Install]
WantedBy=multi-user.target
EOL

cat > /etc/systemd/system/rag-ui.service << EOL
[Unit]
Description=RAG Support Client UI
After=network.target rag-api.service
[Service]
User=rag
Group=rag
WorkingDirectory=/opt/rag-support/current
Environment="PATH=/opt/rag-support/current/.venv/bin"
Environment="PYTHONPATH=/opt/rag-support/current"
EnvironmentFile=/opt/rag-support/config/.env
ExecStart=/opt/rag-support/current/.venv/bin/streamlit run src/rag_support_client/streamlit/pages/1_🏠_Home.py --server.port \${STREAMLIT_PORT} --server.address \${STREAMLIT_HOST}
Restart=always
# Security
PrivateTmp=true
ProtectSystem=full
NoNewPrivileges=true
# Resource limits
LimitNOFILE=65535
MemoryLimit=2G
[Install]
WantedBy=multi-user.target
EOL

# Nginx configuration
echo "Configuring nginx..."

# Backup original nginx.conf
cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup

# Create a new nginx.conf with rate limiting in http context
cat > /etc/nginx/nginx.conf << EOL
user www-data;
worker_processes auto;
pid /run/nginx.pid;
include /etc/nginx/modules-enabled/*.conf;

events {
    worker_connections 768;
}

http {
    # Rate limiting configuration
    limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/s;

    # Basic settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # SSL Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    # Logging Settings
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    # Virtual Host Configs
    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
EOL

# Site configuration
cat > /etc/nginx/sites-available/rag-support << EOL
server {
    listen 80;
    server_name ${DOMAIN};

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self' 'unsafe-inline' 'unsafe-eval'; img-src 'self' data: blob:;" always;

    # API configuration
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Rate limiting (using pre-defined zone)
        limit_req zone=api burst=10 nodelay;
    }

    # Streamlit UI configuration
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # WebSocket support
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOL

# Remove default site and create symlink
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/rag-support /etc/nginx/sites-enabled/


# SSL setup if requested
if [ "$SSL_ENABLE" = "y" ]; then
    echo "Setting up SSL..."
    certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "admin@${DOMAIN}" --redirect
fi

# Start services
echo "Starting services..."
systemctl daemon-reload
systemctl enable --now rag-api rag-ui
systemctl restart nginx

# Final report
echo "
Installation Complete!
---------------------

Access URLs:
- UI: http${SSL_ENABLE:+s}://${DOMAIN}
- API: http${SSL_ENABLE:+s}://${DOMAIN}/api
- API Docs: http${SSL_ENABLE:+s}://${DOMAIN}/api/docs

Useful Commands:
- View API logs: journalctl -u rag-api -f
- View UI logs: journalctl -u rag-ui -f
- Check status: systemctl status rag-api rag-ui
- Restart services: systemctl restart rag-api rag-ui

Installation Details:
- Install path: /opt/rag-support
- Config path: /opt/rag-support/config
- Data path: /opt/rag-support/data
- Logs path: /opt/rag-support/logs

For more information:
https://github.com/netspirit/rag-support-client
"
