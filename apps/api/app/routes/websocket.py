import uuid
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from apps.api.app.services.pipeline_service import run_pipeline_streaming

router = APIRouter()


@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for streaming responses.
    Client sends: {"message": "...", "session_id": "..."}
    Server streams: {"type": "step", "step": "...", "data": {...}}
                    {"type": "result", "data": {...}}
                    {"type": "error", "error": "..."}
    """
    await websocket.accept()
    session_id = str(uuid.uuid4())

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "error": "Invalid JSON"})
                continue

            message = payload.get("message", "").strip()
            if not message:
                await websocket.send_json({"type": "error", "error": "Empty message"})
                continue

            session_id = payload.get("session_id", session_id)

            # Stream pipeline steps back to client
            async for event in run_pipeline_streaming(raw_input=message, session_id=session_id):
                await websocket.send_json(event)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "error": str(e)})
        except Exception:
            pass
