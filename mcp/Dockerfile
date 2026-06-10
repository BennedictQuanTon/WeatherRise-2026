FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY mcp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp/ /app/mcp/

EXPOSE 9000

CMD ["uvicorn", "mcp.server.main:app", "--host", "0.0.0.0", "--port", "9000"]
