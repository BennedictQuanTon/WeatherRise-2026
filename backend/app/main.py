from fastapi import FastAPI
from .routers import health

app = FastAPI(title="WeatherRise Backend API", version="1.0.0")

app.include_router(health.router)