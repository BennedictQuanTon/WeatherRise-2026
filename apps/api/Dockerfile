FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/api/ /app/apps/api/
COPY agents/ /app/agents/
COPY knowledge/ /app/knowledge/
COPY data/ /app/data/

# Ensure all top-level packages are discoverable
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "apps.api.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

