#!/bin/bash
# =============================================================
# Weatherise NIM Reallocation Script
# Re-launches the 120B model on 4 H200 GPUs (TP=4)
# =============================================================
set -e

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"

echo "🌦️  Re-allocating NIM LLM on GPUs 0, 1, 5, 6..."

# Load env to get NGC_API_KEY
export $(grep -v '^#' "$ENV_FILE" | xargs)

# Stop and remove existing container
echo "🛑 Stopping old nim-llm..."
docker stop nim-llm || true
docker rm nim-llm || true

echo "🚀 Starting new nim-llm with 4 GPUs..."
docker run -d --name nim-llm \
  --gpus '"device=0,1,5,6"' \
  --shm-size=16g \
  -e NGC_API_KEY=$NGC_API_KEY \
  -v /raid/team/weatherise/nim-cache:/opt/nim/.cache \
  -p 8001:8000 \
  nvcr.io/nim/nvidia/nemotron-3-super-120b-a12b:latest

echo "✅ NIM LLM started! Follow logs with: docker logs -f nim-llm"
