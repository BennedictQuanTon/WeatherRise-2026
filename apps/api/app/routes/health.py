from fastapi import APIRouter
from fastapi.responses import JSONResponse
import httpx
from apps.api.app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check():
    """Health check endpoint — verifies all internal dependencies."""
    checks = {}

    # Check NIM LLM
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{settings.nim_llm_base_url}/models")
            checks["nim_llm"] = "ok" if r.status_code == 200 else "degraded"
    except Exception:
        checks["nim_llm"] = "unreachable"

    # Check NIM Embed
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{settings.nim_embed_base_url}/models")
            checks["nim_embed"] = "ok" if r.status_code == 200 else "degraded"
    except Exception:
        checks["nim_embed"] = "unreachable"

    # Check MCP Server
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{settings.mcp_server_url}/health")
            checks["mcp_server"] = "ok" if r.status_code == 200 else "degraded"
    except Exception:
        checks["mcp_server"] = "unreachable"

    # Check Qdrant
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{settings.qdrant_url}/collections")
            checks["qdrant"] = "ok" if r.status_code == 200 else "degraded"
    except Exception:
        checks["qdrant"] = "unreachable"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return JSONResponse({"status": overall, "services": checks})
