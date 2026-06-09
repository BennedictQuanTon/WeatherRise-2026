from pydantic import BaseModel
from typing import List, Optional

class DestinationSchema(BaseModel):
    destination_id: str
    name: str
    city: str
    country: str
    lat: float
    lon: float
    activity_type: str
    tags: List[str]
    bad_conditions: List[str]
    safe_alternatives: List[str]
