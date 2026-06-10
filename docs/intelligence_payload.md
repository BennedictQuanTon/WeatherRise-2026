# 🧠 Cấu Trúc Payload Nhận Bởi Intelligence Layer (FullyProcessedPayload)

Tài liệu này chi tiết hóa cấu trúc dữ liệu JSON được gửi từ tầng Context Agent sang **Intelligence Layer** để phục vụ việc lập luận và sinh lời khuyên cuối cùng cho người dùng.

---

## 1. Định Nghĩa Lớp (Python Pydantic Schema)
Cấu trúc này được định nghĩa tại file `apps/api/app/schemas/context_schema.py`:

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class GeographicalLocation(BaseModel):
    country: Optional[str] = None
    city: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None

class TimeRange(BaseModel):
    raw_text: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    timezone: str = "Asia/Ho_Chi_Minh"

class KnowledgeContext(BaseModel):
    found_context: Dict[str, Any] = Field(default_factory=dict)
    missing_context: List[str] = Field(default_factory=list)

class MCPContext(BaseModel):
    coordinates: Optional[Dict[str, float]] = None
    weather_forecast: Optional[Dict[str, Any]] = None
    realtime_weather: Optional[Dict[str, Any]] = None
    places: Optional[List[Dict[str, Any]]] = None
    opening_hours: Optional[Dict[str, Any]] = None
    time_range_resolved: Optional[Dict[str, str]] = None
    external_risk_data: Optional[Dict[str, Any]] = None

class IntelligenceRequirements(BaseModel):
    realtime_weather_needed: bool = True
    weather_variables: List[str] = Field(default_factory=list)
    reasoning_task: str = "general_weather_advice"

class FullyProcessedPayload(BaseModel):
    domain: str
    intent: str
    location: Optional[str] = None
    geographical_location: GeographicalLocation = Field(default_factory=GeographicalLocation)
    time_range: TimeRange = Field(default_factory=TimeRange)
    involved_context: List[str] = Field(default_factory=list)
    knowledge_context: KnowledgeContext = Field(default_factory=KnowledgeContext)
    mcp_context: MCPContext = Field(default_factory=MCPContext)
    intelligence_requirements: IntelligenceRequirements = Field(default_factory=IntelligenceRequirements)
    user_constraints: List[str] = Field(default_factory=list)
    raw_user_input: str = ""
```

---

## 2. Dữ Liệu Payload Mẫu Thực Tế (JSON Payload Example)

Dưới đây là một JSON ví dụ thực tế được thu thập và điền đầy đủ ngữ cảnh bởi **Tourism Context Agent** trước khi gửi sang **Intelligence Layer**:

```json
{
  "domain": "tourism",
  "intent": "travel_planning",
  "location": "Da Nang",
  "geographical_location": {
    "country": "Vietnam",
    "city": "Da Nang",
    "coordinates": {
      "latitude": 16.0544,
      "longitude": 108.2022
    }
  },
  "time_range": {
    "raw_text": "next week",
    "start": "2026-06-15",
    "end": "2026-06-21",
    "timezone": "Asia/Ho_Chi_Minh"
  },
  "involved_context": [
    "weather_forecast",
    "tourist_attractions",
    "indoor_outdoor_classification",
    "opening_hours",
    "travel_time",
    "weather_risk_rules",
    "backup_plan_options"
  ],
  "knowledge_context": {
    "found_context": {
      "weather_risk_rules": "Outdoor activities are risky if rain probability > 60% or wind speed > 30km/h."
    },
    "missing_context": [
      "tourist_attractions",
      "opening_hours"
    ]
  },
  "mcp_context": {
    "coordinates": {
      "latitude": 16.0544,
      "longitude": 108.2022
    },
    "weather_forecast": {
      "latitude": 16.05,
      "longitude": 108.2,
      "timezone": "Asia/Ho_Chi_Minh",
      "daily": {
        "temperature_2m_max": [32.5, 33.0, 31.2, 29.5, 30.1, 31.0, 32.0],
        "precipitation_probability_max": [10, 20, 75, 80, 40, 15, 10],
        "wind_speed_10m_max": [12.0, 15.2, 28.5, 32.0, 18.0, 14.0, 10.5]
      },
      "hourly": {
        "temperature_2m": [28.0, 29.5, 31.0, 32.5, 30.0],
        "precipitation_probability": [5, 10, 20, 75, 80]
      }
    },
    "realtime_weather": null,
    "places": [
      {
        "name": "Ba Na Hills",
        "category": "tourist_attraction",
        "description": "Theme park and resort on mountains",
        "type": "outdoor"
      },
      {
        "name": "Dragon Bridge",
        "category": "tourist_attraction",
        "description": "Famous bridge with fire/water show",
        "type": "outdoor"
      },
      {
        "name": "Cham Museum",
        "category": "tourist_attraction",
        "description": "Historical sculpture museum",
        "type": "indoor"
      }
    ],
    "opening_hours": {
      "Ba Na Hills": "08:00 - 17:00",
      "Dragon Bridge": "24/7",
      "Cham Museum": "07:30 - 17:00"
    },
    "time_range_resolved": {
      "start": "2026-06-15",
      "end": "2026-06-21"
    },
    "external_risk_data": null
  },
  "intelligence_requirements": {
    "realtime_weather_needed": true,
    "weather_variables": [
      "rain_probability",
      "temperature",
      "wind_speed",
      "humidity"
    ],
    "reasoning_task": "tourism_travel_planning"
  },
  "user_constraints": [
    "avoid heavy rain"
  ],
  "raw_user_input": "Plan a 3-day trip in Da Nang next week and avoid heavy rain."
}
```
