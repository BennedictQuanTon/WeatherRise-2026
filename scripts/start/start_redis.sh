#!/bin/bash
# ==============================================================================
# Script: start_redis.sh
# Objective: Provision/Start isolated Redis container tier inside NVMe mount
# Core Path: /raid/team/Weatherise/scripts/start_redis.sh
# ==============================================================================

set -e

CONTAINER_NAME="redis"
DATA_DIR="/raid/team/test/weatherise/data/redis"

echo "[INFO] Commencing container state inspection for: ${CONTAINER_NAME}..."

# Ensure persistent mount directory exists on host
mkdir -p "$DATA_DIR"

if [ "$(docker ps -q -f name=^/${CONTAINER_NAME}$)" ]; then
    echo "[SUCCESS] Container '${CONTAINER_NAME}' is already active and running."
elif [ "$(docker ps -a -q -f name=^/${CONTAINER_NAME}$)" ]; then
    echo "[WARN] Container '${CONTAINER_NAME}' exists but is stopped. Reviving process..."
    docker start "$CONTAINER_NAME"
    echo "[SUCCESS] Process revived successfully."
else
    echo "[INFO] No existing container located. Provisioning new image layers..."
    docker run -d --name "$CONTAINER_NAME" \
      -p 6379:6379 \
      -v "${DATA_DIR}:/data" \
      redis:7-alpine --appendonly yes
    echo "[SUCCESS] Container initialized and detached on port 6379."
fi