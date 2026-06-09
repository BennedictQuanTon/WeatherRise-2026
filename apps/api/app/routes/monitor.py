"""
SSE endpoint — streams real-time pipeline log events to /monitor page.
"""
import asyncio
import json
import time
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from typing import AsyncIterator

router = APIRouter()

# In-memory ring buffer of log entries (max 1000)
_LOG_BUFFER: list[dict] = []
_SUBSCRIBERS: list[asyncio.Queue] = []


def emit(level: str, service: str, message: str, duration_ms: int | None = None, data: dict | None = None):
    """Call this from pipeline steps to push a log entry to all subscribers."""
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


async def _event_stream(queue: asyncio.Queue) -> AsyncIterator[str]:
    """Generator that yields SSE events from the queue."""
    # Send buffered logs first (last 100)
    for entry in _LOG_BUFFER[-100:]:
        yield f"data: {json.dumps(entry)}\n\n"
    # Stream new events
    while True:
        try:
            entry = await asyncio.wait_for(queue.get(), timeout=15.0)
            yield f"data: {json.dumps(entry)}\n\n"
        except asyncio.TimeoutError:
            # heartbeat
            yield f"data: {json.dumps({'type': 'ping', 'ts': int(time.time() * 1000)})}\n\n"


@router.get("/api/monitor/stream")
async def monitor_stream():
    """SSE stream for real-time pipeline logs."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    _SUBSCRIBERS.append(queue)

    async def cleanup():
        async for chunk in _event_stream(queue):
            yield chunk
        _SUBSCRIBERS.remove(queue)

    return StreamingResponse(
        cleanup(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/monitor/logs")
async def get_logs(limit: int = 200):
    """Return last N log entries as JSON."""
    return {"logs": _LOG_BUFFER[-limit:], "total": len(_LOG_BUFFER)}
