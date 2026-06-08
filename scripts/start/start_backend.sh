#!/bin/bash
# ==============================================================================
# Script: run_backend.sh
# Objective: Activate isolated environment and run FastAPI web service layer
# Core Path: /raid/team/test/weatherise/scripts/run_backend.sh
# ==============================================================================

set -e

WORKSPACE_ROOT="/raid/team/test/weatherise/code"
BACKEND_DIR="${WORKSPACE_ROOT}/backend"
VENV_PATH="${BACKEND_DIR}/app/.venv"

echo "[INFO] Navigating to system backend destination..."
cd "$BACKEND_DIR"

if [ ! -d "$VENV_PATH" ]; then
    echo "[ERROR] Virtual environment missing at: ${VENV_PATH}"
    echo "Execute: 'python3 -m venv ${VENV_PATH}' before triggering this engine."
    exit 1
fi

echo "[INFO] Initializing virtual environment shell path context..."
source "${VENV_PATH}/bin/activate"

echo "[INFO] Deploying live Uvicorn loopback gateway on interface port 8008..."
# Running with reload flag enabled to permit dynamic hackathon sprint updates
exec uvicorn app.main:app --host 0.0.0.0 --port 8008 --reload