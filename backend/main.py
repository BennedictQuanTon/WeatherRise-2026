from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api import health

app = FastAPI(
    title="Weatherise MVP", 
    description="Backend for Weatherise 4-Agent MVP System",
    version="1.0.0"
)

# Allow CORS for Gradio/Streamlit UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)

from backend.api import destinations
app.include_router(destinations.router)

from backend.api import weather, session, monitor, notify
app.include_router(weather.router)
app.include_router(session.router)
app.include_router(monitor.router)
app.include_router(notify.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8008, reload=True)
