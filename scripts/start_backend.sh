#!/bin/bash

#Local path
#cd /d/Dev/Projects/Weatherise/code/WeatherRise-2026/backend

#Custer path
cd /raid/team/test/weatherise/backend
source .venv/Scripts/activate
uvicorn app.main:app --host 0.0.0.0 --port 8008 --reload