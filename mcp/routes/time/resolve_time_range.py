"""
MCP Route: time.resolveTimeRange
Converts natural language time phrases to start/end dates with timezone.
"""
import dateparser
from datetime import datetime, timedelta
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

DEFAULT_TZ = "Asia/Ho_Chi_Minh"


class TimeRequest(BaseModel):
    raw_text: str
    timezone: Optional[str] = DEFAULT_TZ


class TimeResponse(BaseModel):
    raw_text: str
    start: Optional[str] = None
    end: Optional[str] = None
    timezone: str = DEFAULT_TZ
    duration_days: Optional[int] = None


@router.post("/resolveTimeRange", response_model=TimeResponse)
async def resolve_time_range(req: TimeRequest):
    tz = req.timezone or DEFAULT_TZ
    settings = {"RETURN_AS_TIMEZONE_AWARE": False, "PREFER_DAY_OF_MONTH": "first",
                 "TIMEZONE": tz}

    raw = req.raw_text.lower().strip()
    now = datetime.now()

    try:
        # Handle common phrases explicitly for reliability
        if "today" in raw:
            start = now.strftime("%Y-%m-%d")
            end = start
        elif "tomorrow" in raw:
            d = now + timedelta(days=1)
            start = d.strftime("%Y-%m-%d")
            end = start
        elif "this week" in raw:
            start = now.strftime("%Y-%m-%d")
            end = (now + timedelta(days=7)).strftime("%Y-%m-%d")
        elif "next week" in raw or "tuần sau" in raw:
            days_to_monday = 7 - now.weekday()
            start_dt = now + timedelta(days=days_to_monday)
            start = start_dt.strftime("%Y-%m-%d")
            end = (start_dt + timedelta(days=6)).strftime("%Y-%m-%d")
        elif "this weekend" in raw:
            days_to_sat = (5 - now.weekday()) % 7
            start = (now + timedelta(days=days_to_sat)).strftime("%Y-%m-%d")
            end = (now + timedelta(days=days_to_sat + 1)).strftime("%Y-%m-%d")
        elif "3-day" in raw or "3 day" in raw:
            start = now.strftime("%Y-%m-%d")
            end = (now + timedelta(days=3)).strftime("%Y-%m-%d")
        else:
            # Use dateparser for other expressions
            parsed = dateparser.parse(req.raw_text, settings=settings)
            if parsed:
                start = parsed.strftime("%Y-%m-%d")
                end = (parsed + timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                # Default to today
                start = now.strftime("%Y-%m-%d")
                end = (now + timedelta(days=1)).strftime("%Y-%m-%d")

        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")
        duration = (end_dt - start_dt).days + 1

        return TimeResponse(
            raw_text=req.raw_text,
            start=start,
            end=end,
            timezone=tz,
            duration_days=duration,
        )

    except Exception as e:
        print(f"[MCP:time] Error: {e}")
        start = now.strftime("%Y-%m-%d")
        return TimeResponse(raw_text=req.raw_text, start=start, end=start, timezone=tz)
