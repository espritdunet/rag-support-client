#!/bin/bash
"""
SSL setup script for RAG Support Client
Handles Let's Encrypt certificate generation and nginx SSL configuration.

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

# ------------------------------
# Pre-flight Checks
# ------------------------------
if [ "$EUID" -ne 0 ]; then
    error "Please run as root"
fi

if [ -z "$NGINX_SERVER_NAME" ]; then
    error "NGINX_SERVER_NAME is not set in configuration"
fi

if [ "$SSL_ENABLED" != "true" ]; then
    error "SSL is not enabled in configuration"
fi

# ------------------------------
# Main Installation
# ------------------------------
log "Starting SSL setup for $NGINX_SERVER_NAME..."

# 1. Install certbot and nginx plugin
log "Installing certbot..."
apt-get update
apt-get install -y certbot python3-certbot-nginx

# 2. Create webroot directory for ACME challenges
log "Creating ACME challenge directory..."
mkdir -p /var/www/certbot
chown www-data:www-data /var/www/certbot
chmod 755 /var/www/certbot

# 3. Generate strong DH parameters (this may take a while)
log "Generating DH parameters..."
if [ ! -f /etc/nginx/dhparam.pem ]; then
    openssl dhparam -out /etc/nginx/dhparam.pem 2048
fi

# 4. Backup existing nginx configuration
log "Backing up nginx configuration..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
if [ -f /etc/nginx/sites-available/rag-support ]; then
    cp /etc/nginx/sites-available/rag-support "/etc/nginx/sites-available/rag-support.backup.$TIMESTAMP"
fi

# 5. Configure nginx for initial certificate request
log "Configuring nginx for certificate request..."
cat > /etc/nginx/sites-available/rag-support << EOL
server {
    listen 80;
    listen [::]:80;
    server_name ${NGINX_SERVER_NAME};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}
EOL

# Enable the site and test nginx configuration
ln -sf /etc/nginx/sites-available/rag-support /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# 6. Request Let's Encrypt certificate
log "Requesting Let's Encrypt certificate..."
certbot certonly --webroot \
    --webroot-path /var/www/certbot \
    --email "${ADMIN_EMAIL:-admin@$NGINX_SERVER_NAME}" \
    --agree-tos \
    --no-eff-email \
    --staging \
    -d "$NGINX_SERVER_NAME"

# If staging was successful, get real certificate
if [ $? -eq 0 ]; then
    log "Staging successful, requesting production certificate..."
    certbot certonly --webroot \
        --webroot-path /var/www/certbot \
        --email "${ADMIN_EMAIL:-admin@$NGINX_SERVER_NAME}" \
        --agree-tos \
        --no-eff-email \
        -d "$NGINX_SERVER_NAME"
else
    error "Staging certificate request failed"
fi

# 7. Configure SSL-enabled nginx
log "Configuring nginx with SSL..."

# Include security configuration
if [ ! -f /etc/nginx/conf.d/security.conf ]; then
    cp "$(dirname "$0")/../config/nginx/security.conf" /etc/nginx/conf.d/
fi

# Configure SSL-enabled site
cat > /etc/nginx/sites-available/rag-support << EOL
# HTTP redirect
server {
    listen 80;
    listen [::]:80;
    server_name ${NGINX_SERVER_NAME};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${NGINX_SERVER_NAME};

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/${NGINX_SERVER_NAME}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${NGINX_SERVER_NAME}/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/${NGINX_SERVER_NAME}/chain.pem;

    # Include security configuration
    include /etc/nginx/conf.d/security.conf;

    # API Configuration
    location /api {
        proxy_pass http://localhost:${API_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Rate limiting
        limit_req zone=api_limit burst=20 nodelay;
    }

    # Streamlit UI Configuration
    location / {
        proxy_pass http://localhost:${STREAMLIT_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Rate limiting
        limit_req zone=ui_limit burst=50 nodelay;
    }
}
EOL

# 8. Test and reload nginx
log "Testing nginx configuration..."
nginx -t && systemctl reload nginx

# 9. Setup automatic renewal
log "Configuring automatic certificate renewal..."
cat > /etc/cron.d/certbot << EOL
0 */12 * * * root test -x /usr/bin/certbot -a \! -d /run/systemd/system && perl -e 'sleep int(rand(43200))' && certbot renew --quiet --deploy-hook "systemctl reload nginx"
EOL

# 10. Test SSL configuration
log "Testing SSL configuration..."
curl -sI "https://${NGINX_SERVER_NAME}" > /dev/null
if [ $? -eq 0 ]; then
    log "SSL configuration test successful"
else
    log "WARNING: SSL configuration test failed"
fi

# Final status report
log "
SSL Setup Complete!
------------------
Domain: ${NGINX_SERVER_NAME}
Certificate location: /etc/letsencrypt/live/${NGINX_SERVER_NAME}/
Next renewal: $(certbot certificates | grep "Expiry Date" | awk '{print $3, $4, $5, $6}')

To test SSL configuration:
- SSL Labs: https://www.ssllabs.com/ssltest/analyze.html?d=${NGINX_SERVER_NAME}
- Certificate info: certbot certificates
- Nginx status: systemctl status nginx

Certificate will auto-renew via cron job.
"

# Test SSL grade using SSL Labs API (if available)
if command -v curl &> /dev/null; then
    log "Initiating SSL Labs test (this may take a few minutes)..."
    curl -s "https://api.ssllabs.com/api/v3/analyze?host=${NGINX_SERVER_NAME}"
fi
