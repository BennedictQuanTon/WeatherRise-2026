"""
MCP Fallback Client — Phase 4 Step 4 Tier 2
============================================
Calls domain-specific Professional MCP servers when Milvus Tier-1 returns empty
or times out. Extracts live operational data directly from the server stream.

Design contract (per context_agents_flow.md Step 4):
  - Invoked only when Tier-1 returns None
  - Fetch live data: port capacity markers, concrete logs, museum scheduling states
  - Return raw parameter dict (no prose, no advisory text)
"""

from __future__ import annotations

import logging
import httpx

from ..configs.settings import settings

logger = logging.getLogger("uvicorn.error")

_TIMEOUT = 10.0  # seconds


class MCPFallbackClient:
    """
    Routes to the domain-specific Professional MCP server when Milvus
    returns an empty array or connection pool timeout.

    Each method fetches live operational data for the given extraction_key
    from the corresponding MCP server endpoint.
    """

    async def _fetch(self, base_url: str, extraction_key: str) -> dict:
        """
        Execute an HTTP GET to the MCP server and return the JSON payload.

        Args:
            base_url: The MCP server base URL (from settings).
            extraction_key: Entity identifier to query.

        Returns:
            Raw dict from the MCP server stream.

        Raises:
            RuntimeError: If the MCP server is unreachable or returns non-200.
        """
        url = f"{base_url}/query"
        params = {"key": extraction_key}

        logger.info("[MCP] Calling MCP server | url=%s | key=%s", url, extraction_key)

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(url, params=params)

        if response.status_code != 200:
            raise RuntimeError(
                f"MCP server returned {response.status_code} for key={extraction_key}"
            )

        data = response.json()
        logger.info("[MCP] Response received | key=%s | fields=%s", extraction_key, list(data.keys()))
        return data

    async def fetch_tourism(self, extraction_key: str) -> dict:
        """
        Fetch live tourism data from the Tourism MCP server.
        Typical fields: site_id, operating_hours, max_capacity, live_visitor_count.
        """
        return await self._fetch(settings.MCP_TOURISM_URL, extraction_key)

    async def fetch_fishery(self, extraction_key: str) -> dict:
        """
        Fetch live fishery/fleet data from the Fishery MCP server.
        Typical fields: port_id, active_vessel_count, fleet_status, berth_availability.
        """
        return await self._fetch(settings.MCP_FISHERY_URL, extraction_key)

    async def fetch_construction(self, extraction_key: str) -> dict:
        """
        Fetch live construction data from the Construction MCP server.
        Typical fields: site_id, permit_status, last_concrete_pour_log, work_suspension_flag.
        """
        return await self._fetch(settings.MCP_CONSTRUCTION_URL, extraction_key)


# Module-level singleton
mcp_client = MCPFallbackClient()
