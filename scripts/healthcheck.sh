#!/bin/bash
# Script to check health of backend and redis
echo "=== Weatherise MVP Health Check ==="
echo "1. Checking Redis (Port 6379)..."
redis-cli -p 6379 ping || echo "WARNING: Redis might be down or redis-cli not installed"

echo -e "\n2. Checking Backend (Port 8008)..."
curl -s http://localhost:8008/health || echo "WARNING: Backend is down. Run scripts/run_backend.sh first."
echo ""