FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY mcp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Core MCP server
COPY mcp/ /app/mcp/

# Knowledge Base (TourismRetriever, VectorStoreClient, ingestion pipeline)
COPY knowledge/ /app/knowledge/

# Mock data (Phase 2 seed + fallback data)
COPY data/ /app/data/

# Ensure top-level packages are discoverable
ENV PYTHONPATH=/app

EXPOSE 9000

CMD ["uvicorn", "mcp.server.main:app", "--host", "0.0.0.0", "--port", "9000"]
