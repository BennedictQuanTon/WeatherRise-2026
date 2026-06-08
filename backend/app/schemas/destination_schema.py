from pydantic import BaseModel, Field
from typing import List

class DestinationRecord(BaseModel):
    destination_id: str = Field(..., description="Unique alphanumeric identifier string")
    name: str = Field(..., description="Public name of attraction")
    city: str
    country: str
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    activity_type: str
    tags: List[str] = Field(default_factory=list)
    bad_conditions: List[str] = Field(default_factory=list)
    safe_alternatives: List[str] = Field(default_factory=list)