"""
SSE endpoint — streams real-time pipeline log events to /monitor page.
"""
import asyncio
import json
import time
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from typing import AsyncIterator

router = APIRouter()

# In-memory ring buffer of log entries (max 1000)
_LOG_BUFFER: list[dict] = []
_SUBSCRIBERS: list[asyncio.Queue] = []


def emit(level: str, service: str, message: str, duration_ms: int | None = None, data: dict | None = None):
    """Push a log entry to all SSE subscribers + buffer."""
    entry = {
        "id": f"{time.time():.6f}",
        "ts": int(time.time() * 1000),
        "level": level,
        "service": service,
        "message": message,
        "duration": duration_ms,
        "data": data,
    }
    _LOG_BUFFER.append(entry)
    if len(_LOG_BUFFER) > 1000:
        _LOG_BUFFER.pop(0)
    for q in list(_SUBSCRIBERS):
        try:
            q.put_nowait(entry)
        except asyncio.QueueFull:
            pass


async def _event_stream(queue: asyncio.Queue, request: Request) -> AsyncIterator[str]:
    """Generator: sends buffered logs then streams new events. Cleans up on disconnect."""
    _SUBSCRIBERS.append(queue)
    try:
        # Send buffered logs first (last 50)
        for entry in _LOG_BUFFER[-50:]:
            yield f"data: {json.dumps(entry)}\n\n"
        
        # Immediate ping to flush headers
        yield f"data: {json.dumps({'type': 'ping', 'ts': int(time.time() * 1000)})}\n\n"
        
        # Stream new events
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break
            try:
                entry = await asyncio.wait_for(queue.get(), timeout=10.0)
                yield f"data: {json.dumps(entry)}\n\n"
            except asyncio.TimeoutError:
                # heartbeat ping every 10s
                yield f"data: {json.dumps({'type': 'ping', 'ts': int(time.time() * 1000)})}\n\n"
    finally:
        # Always cleanup on disconnect/error
        if queue in _SUBSCRIBERS:
            _SUBSCRIBERS.remove(queue)


@router.get("/api/monitor/stream")
async def monitor_stream(request: Request):
    """SSE stream — browser connects directly (bypasses Next.js proxy)."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=500)
    return StreamingResponse(
        _event_stream(queue, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Expose-Headers": "*",
        },
    )


@router.get("/api/monitor/logs")
async def get_logs(limit: int = 200):
    """Return last N log entries as JSON."""
    return {"logs": _LOG_BUFFER[-limit:], "total": len(_LOG_BUFFER)}
