#!/bin/bash
# =============================================================
# Weatherise v2 — Deploy Script (NVIDIA H200 Server)
# Run from repo root: ./infra/scripts/deploy_nvidia.sh
# =============================================================
set -e

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/infra/docker-compose.yml"
ENV_FILE="$REPO_ROOT/.env"

echo "🌦️  Weatherise v2 Deploy Starting..."

# Check .env exists
if [ ! -f "$ENV_FILE" ]; then
  echo "❌ .env not found. Copy .env.example to .env and fill in values."
  exit 1
fi

# Load env
export $(grep -v '^#' "$ENV_FILE" | xargs)

echo "📦 Building and starting services..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

echo ""
echo "🔍 Service Status:"
docker compose -f "$COMPOSE_FILE" ps

echo ""
echo "🩺 Running health check..."
bash "$REPO_ROOT/infra/scripts/healthcheck.sh"

echo ""
echo "✅ Weatherise v2 is deployed!"
echo "🌐 Access: http://$(hostname -I | awk '{print $1}'):8080"
