#!/bin/bash
# Script to run the FastAPI backend
cd /raid/team/dev/member_1/WeatherRise-2026
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi
uvicorn backend.main:app --host 0.0.0.0 --port 8008 --reload
