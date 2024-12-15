#!/bin/bash
"""
RAG Support Client - Cleanup Script
Removes all installed components and configurations
"""

set -e

echo "RAG Support Client - Cleanup"
echo "---------------------------"

# Stop and remove services
echo "Stopping and removing services..."
systemctl stop rag-api rag-ui 2>/dev/null || true
systemctl disable rag-api rag-ui 2>/dev/null || true
rm -f /etc/systemd/system/rag-api.service
rm -f /etc/systemd/system/rag-ui.service
systemctl daemon-reload

# Remove nginx configuration
echo "Removing nginx configuration..."
rm -f /etc/nginx/sites-enabled/rag-support
rm -f /etc/nginx/sites-available/rag-support
systemctl restart nginx || true

# Remove installation directory
echo "Removing installation directory..."
rm -rf /opt/rag-support

# Remove service user
echo "Removing service user..."
userdel rag 2>/dev/null || true

echo "Cleanup complete!"
echo "You can now run deploy.sh again for a fresh installation."
