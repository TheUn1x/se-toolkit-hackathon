#!/bin/bash
# CashFlow — Deployment Script for Ubuntu 24.04
# Run as: sudo bash deploy.sh

set -e

echo "🚀 Deploying CashFlow..."

# 1. Update system
echo "📦 Updating system packages..."
apt update -y
apt install -y python3 python3-pip python3-venv curl

# 2. Install Docker (if not present)
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    apt install -y ca-certificates curl gnupg
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
    apt update -y
    apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi

# 3. Deploy with Docker Compose
echo "🐳 Building and starting containers..."
docker compose up -d --build

# 4. Wait for health
echo "⏳ Waiting for service to be ready..."
sleep 5

# 5. Check health
HEALTH=$(curl -s http://localhost:8000/api/health)
if echo "$HEALTH" | grep -q "ok"; then
    echo "✅ CashFlow is running at http://localhost:8000"
    echo "📊 Health: $HEALTH"
else
    echo "❌ Health check failed. Check logs: docker compose logs"
    exit 1
fi
