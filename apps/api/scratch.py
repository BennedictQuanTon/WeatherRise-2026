import asyncio
import os
import sys

# add parent directory to path so agents can be imported
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from agents.intelligence_layer.weather_path_b.path_b_service import PathBWeatherService
from pydantic import BaseModel

class DummyGeo(BaseModel):
    coordinates: dict = {"latitude": 16.0544, "longitude": 108.2022}

class DummyProcessed(BaseModel):
    intent: str = "concrete_pouring"
    domain: str = "construction"
    location: str = "Da Nang"
    geographical_location: DummyGeo = DummyGeo()

async def main():
    service = PathBWeatherService()
    res = await service.run(DummyProcessed())
    print("Decision:", res.decision)
    print("Warnings:", res.warnings)
    for w in res.warnings:
        print(w)
    
    for r in res.quality_reports:
        if not r.valid:
            print("Invalid source:", r.source_code, "Invalid Fields:", r.invalid_fields, "Missing Fields:", r.missing_fields, "Warnings:", r.warnings)
        else:
            print("Valid source:", r.source_code)

if __name__ == "__main__":
    asyncio.run(main())
