from pydantic import BaseModel
from typing import Optional

class SessionSchema(BaseModel):
    session_id: str
    destination_id: str
    forecast_date: str
    forecast_time: str
    alert_channel: str
    phone_number: Optional[str] = None
    last_risk_overall: str
    is_active: bool = True
