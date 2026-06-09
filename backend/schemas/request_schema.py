from pydantic import BaseModel
from typing import Optional

class WeatherAnalyzeRequest(BaseModel):
    destination_id: str
    forecast_date: str # YYYY-MM-DD
    forecast_time: str # HH:MM
    monitoring_enabled: bool = False
    alert_channel: str = "ui_banner"
    phone_number: Optional[str] = None
