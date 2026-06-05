# 🛠️ Weatherise — Implementation Guide & Timeline

> **Cluster:** NVIDIA Open Hackathon 2026 — 8× H200 (141 GB each), 192 CPU cores, ~2 TB RAM, ~28 TB NVMe `/raid`
> **Access:** JupyterLab (`http://<IP>:8888`) + SSH
> **Docker:** `default-runtime: nvidia`, NGC pre-authenticated (`nvcr.io`)
> **Duration:** 6 days (Day 1-3: MVP, Day 4-5: Polish, Day 6: Presentation)

---

## 📋 Table of Contents

- [Pre-Hackathon Preparation](#-pre-hackathon-preparation)
- [Phase 1: Cluster Setup & Model Deployment (Day 1 Morning)](#-phase-1-cluster-setup--model-deployment-day-1-morning)
- [Phase 2: Data Ingestion & RAG Pipeline (Day 1 PM — Day 2)](#-phase-2-data-ingestion--rag-pipeline-day-1-pm--day-2)
- [Phase 3: Agent Development (Day 2 — Day 3)](#-phase-3-agent-development-day-2--day-3)
- [Phase 4: Frontend MVP + Real-Time Features (Day 3 — Day 4)](#-phase-4-frontend-mvp--real-time-features-day-3--day-4)
- [Phase 5: Polish, Export & Monitoring (Day 4 — Day 5)](#-phase-5-polish-export--monitoring-day-4--day-5)
- [Phase 6: Demo & Presentation (Day 6)](#-phase-6-demo--presentation-day-6)
- [Master Checklist](#-master-checklist)

---

## 🔑 Pre-Hackathon Preparation

### API Keys & Accounts to Register BEFORE Hackathon

> **IMPORTANT:** Register these accounts **before** the hackathon starts. Some take hours to approve.

| # | Service | URL | What You Need | Cost | Priority |
|---|---------|-----|--------------|------|----------|
| 1 | **NGC API Key** | Provided by VTS (hackathon organizer) | Key for NIM container model downloads | FREE | 🔴 Critical |
| 2 | **OpenWeatherMap** | https://openweathermap.org/api | API key for current weather + 5-day forecast | FREE (1,000 calls/day) | 🔴 Critical |
| 3 | **SpeedSMS** | https://speedsms.vn | Account + API token for Vietnam SMS | FREE trial (2,000 VND ≈ 5-6 msgs) | 🟡 High |
| 4 | **Google Places API** | https://console.cloud.google.com | API key for attractions, reviews, photos | FREE ($200 credit/month) | 🟡 High |
| 5 | **HuggingFace** | https://huggingface.co | Token for downloading models (Llama, etc.) | FREE | 🟡 High |
| 6 | **LangSmith** | https://smith.langchain.com | API key for agent tracing (optional) | FREE tier | 🟢 Nice-to-have |
| 7 | **Open-Meteo** | https://open-meteo.com | **No key needed!** Just call the API | FREE | ✅ Ready |

### Data to Pre-Download (on laptop, SCP later)

| Data | Source | Est. Size | Method |
|------|--------|-----------|--------|
| Da Nang attractions list (top 100) | TripAdvisor | ~50 MB | Manual scrape or export |
| Wikivoyage Da Nang pages | wikivoyage.org | ~5 MB | `trafilatura` scrape |
| Food blog articles | Various | ~20 MB | `trafilatura` scrape |
| OpenStreetMap Da Nang extract | download.geofabrik.de | ~200 MB | `.osm.pbf` file |

### Code to Pre-Write (on laptop)

```
weatherise/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── agents/
│   │   │   ├── orchestrator.py   # LangGraph StateGraph
│   │   │   ├── weather.py        # Weather Agent
│   │   │   ├── attraction.py     # Attraction Agent
│   │   │   ├── route.py          # Route Agent
│   │   │   ├── local_expert.py   # Local Expert Agent
│   │   │   ├── safety.py         # Safety Agent
│   │   │   ├── watcher.py        # Weather Watcher (background)
│   │   │   └── notifier.py       # Notification Agent (SMS + WS)
│   │   ├── services/
│   │   │   ├── llm.py            # NIM client (OpenAI-compatible)
│   │   │   ├── weather_api.py    # Open-Meteo + OWM wrapper
│   │   │   ├── sms.py            # SpeedSMS wrapper
│   │   │   ├── rag.py            # Milvus retrieval
│   │   │   └── export.py         # Plan → image + QR
│   │   ├── models/               # Pydantic schemas
│   │   └── config.py             # Environment config
│   ├── requirements.txt
│   └── Dockerfile
├── gradio-ui/
│   ├── app.py                    # Gradio ChatInterface
│   └── requirements.txt
├── frontend/                     # Next.js PWA (Day 4-5)
├── scripts/
│   ├── ingest_data.py            # Data ingestion pipeline
│   ├── setup_milvus.py           # Milvus collection setup
│   └── healthcheck.sh            # Health check all services
├── data/                         # Raw data files
└── .env                          # API keys
```

### Environment Variables File (`.env`)

```bash
# === Cluster Access (VTS provides) ===
NGC_API_KEY=<from-VTS>
CLUSTER_IP=<from-VTS>

# === API Keys (register before hackathon) ===
OPENWEATHERMAP_API_KEY=<your-key>
SPEEDSMS_TOKEN=<your-token>
GOOGLE_PLACES_API_KEY=<your-key>
HUGGINGFACE_TOKEN=<your-token>
LANGSMITH_API_KEY=<optional>

# === Service URLs (set after GPU containers start) ===
LLM_BASE_URL=http://localhost:8000/v1
EMBED_BASE_URL=http://localhost:8001/v1
RERANK_BASE_URL=http://localhost:8002/v1
EARTH2_URL=http://localhost:8081
CUOPT_URL=http://localhost:8083

# === Open-Meteo (no key needed) ===
OPEN_METEO_BASE=https://api.open-meteo.com/v1
DANANG_LAT=16.0544
DANANG_LNG=108.2022

# === App Config ===
WEATHER_WATCH_INTERVAL=600
REDIS_URL=redis://localhost:6379
MILVUS_HOST=localhost
MILVUS_PORT=19530
POSTGRES_URL=postgresql://postgres:weatherise@localhost:5432/weatherise
```

---

## 🚀 Phase 1: Cluster Setup & Model Deployment (Day 1 Morning)

**Who:** Member B (AI/ML) + Member D (DevOps)
**Duration:** ~4 hours
**Goal:** All GPU services running, all non-GPU services running

### Step 1.1: Access & Sanity Check (15 min)

```bash
# SSH into cluster
ssh <user>@<CLUSTER_IP>

# Sanity checks
nvidia-smi                        # Should show 8× H200, Driver 580.159.03, CUDA 13.0
df -h /raid                       # Should show ~27 TB free
docker ps                         # JupyterLab container running
echo "hello" > /raid/team/test.txt && cat /raid/team/test.txt  # Storage OK
```

### Step 1.2: Create Directory Structure (5 min)

```bash
# All project data goes under /raid/team (= /workspace in JupyterLab)
mkdir -p /raid/team/weatherise/{code,data,models,logs}
mkdir -p /raid/nim-cache
mkdir -p /raid/team/weatherise/data/{weather,attractions,milvus,postgres,redis}

# Upload pre-written code from laptop
scp -r ./weatherise/* <user>@<CLUSTER_IP>:/raid/team/weatherise/code/

# Upload .env file
scp ./.env <user>@<CLUSTER_IP>:/raid/team/weatherise/code/.env
```

### Step 1.3: Deploy LLM — NIM on GPU 0-1 (15 min)

> **NOTE:** The hackathon provides NIM containers pre-authenticated on NGC. Use NIM instead of raw vLLM — it's OpenAI-compatible and optimized for H200.

```bash
# Load NGC API Key
export NGC_API_KEY=<key-from-VTS>

# Option A: Nemotron Nano 8B (fast, light — recommended for Day 1-3 MVP)
docker run -d --name nim-llm \
  --gpus '"device=0,1"' \
  --shm-size=16g \
  -e NGC_API_KEY \
  -v /raid/nim-cache:/opt/nim/.cache \
  -p 8000:8000 \
  nvcr.io/nim/nvidia/llama-3.1-nemotron-nano-8b-v1:latest

# Option B: Larger model (upgrade on Day 4 for Polish)
# docker run -d --name nim-llm-large \
#   --gpus '"device=0,1"' \
#   --shm-size=32g \
#   -e NGC_API_KEY \
#   -v /raid/nim-cache:/opt/nim/.cache \
#   -p 8000:8000 \
#   nvcr.io/nim/nvidia/nemotron-3-super-49b:latest

# Wait for startup (~5-10 min first time, downloading model)
docker logs -f nim-llm  # Wait for "Application startup complete"

# Test LLM
curl http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "nvidia/llama-3.1-nemotron-nano-8b-v1",
    "messages": [{"role":"user","content":"Hello Da Nang!"}],
    "max_tokens": 50
  }'
```

### Step 1.4: Deploy Embedding Model — NIM on GPU 4 (10 min)

```bash
# NV-Embed for RAG embeddings
docker run -d --name nim-embed \
  --gpus '"device=4"' \
  --shm-size=8g \
  -e NGC_API_KEY \
  -v /raid/nim-cache:/opt/nim/.cache \
  -p 8001:8000 \
  nvcr.io/nim/nvidia/nv-embedqa-e5-v5:latest

# Wait & test
docker logs -f nim-embed
curl http://localhost:8001/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"model":"nvidia/nv-embedqa-e5-v5","input":"Da Nang beach"}'
```

### Step 1.5: Deploy Reranker — NIM on GPU 5 (10 min)

```bash
docker run -d --name nim-rerank \
  --gpus '"device=5"' \
  --shm-size=8g \
  -e NGC_API_KEY \
  -v /raid/nim-cache:/opt/nim/.cache \
  -p 8002:8000 \
  nvcr.io/nim/nvidia/nv-rerankqa-mistral-4b-v3:latest

# Test
docker logs -f nim-rerank
```

### Step 1.6: Deploy cuOpt — GPU 6 (10 min)

```bash
docker run -d --name cuopt \
  --gpus '"device=6"' \
  -e NGC_API_KEY \
  -v /raid/nim-cache:/opt/nim/.cache \
  -p 8083:5000 \
  nvcr.io/nvidia/cuopt:latest

docker logs -f cuopt
```

### Step 1.7: Earth-2 Setup — GPU 2-3 (30 min)

> Earth-2 Studio runs via Python in JupyterLab, not as a separate NIM container. JupyterLab already has PyTorch + all 8 GPUs visible.

```bash
# In JupyterLab terminal (http://<IP>:8888)
pip install earth2studio

# Test Earth-2 import
python -c "import earth2studio; print('Earth-2 OK')"

# Download StormScope model checkpoint
pip install huggingface-hub
python -c "
from huggingface_hub import snapshot_download
snapshot_download('nvidia/stormscope-goes-mrms', local_dir='/workspace/weatherise/models/stormscope')
print('StormScope model downloaded!')
"

# Note: Earth-2 will use GPU 2-3 via CUDA_VISIBLE_DEVICES when called
# from the Weather Agent. This is set programmatically, not via Docker.
```

### Step 1.8: Non-GPU Services — Data Layer (20 min)

These run on CPU, no GPU needed:

```bash
# Redis (session + cache store)
docker run -d --name redis \
  -p 6379:6379 \
  -v /raid/team/weatherise/data/redis:/data \
  redis:7-alpine --appendonly yes

# PostgreSQL (structured data)
docker run -d --name postgres \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=weatherise \
  -e POSTGRES_DB=weatherise \
  -v /raid/team/weatherise/data/postgres:/var/lib/postgresql/data \
  postgres:16

# Milvus Standalone (vector DB)
docker run -d --name milvus \
  -p 19530:19530 -p 9091:9091 \
  -v /raid/team/weatherise/data/milvus:/var/lib/milvus \
  -e ETCD_USE_EMBED=true \
  -e COMMON_STORAGETYPE=local \
  milvusdb/milvus:latest milvus run standalone

# Verify all running
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Step 1.9: Health Check All Services (5 min)

```bash
# Save as /raid/team/weatherise/code/scripts/healthcheck.sh
#!/bin/bash
echo "=== Weatherise Service Health Check ==="

echo -n "LLM NIM (port 8000):   "
curl -s http://localhost:8000/v1/models | python3 -c "import sys,json; d=json.load(sys.stdin); print('✅', d['data'][0]['id'])" 2>/dev/null || echo "❌ DOWN"

echo -n "Embed NIM (port 8001): "
curl -s http://localhost:8001/v1/models | python3 -c "import sys,json; d=json.load(sys.stdin); print('✅', d['data'][0]['id'])" 2>/dev/null || echo "❌ DOWN"

echo -n "Rerank NIM (port 8002):"
curl -s http://localhost:8002/v1/models | python3 -c "import sys,json; d=json.load(sys.stdin); print('✅', d['data'][0]['id'])" 2>/dev/null || echo "❌ DOWN"

echo -n "cuOpt (port 8083):     "
curl -s http://localhost:8083/health 2>/dev/null && echo " ✅" || echo "❌ DOWN"

echo -n "Redis (port 6379):     "
docker exec redis redis-cli ping 2>/dev/null || echo "❌ DOWN"

echo -n "Milvus (port 19530):   "
curl -s http://localhost:9091/healthz 2>/dev/null && echo " ✅" || echo "❌ DOWN"

echo -n "PostgreSQL (port 5432):"
docker exec postgres pg_isready -q 2>/dev/null && echo " ✅" || echo "❌ DOWN"

echo ""
echo "=== GPU Status ==="
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv,noheader,nounits | while IFS=, read idx name used total; do
  pct=$((used * 100 / total))
  echo "  GPU $idx: $name | ${used}MB / ${total}MB (${pct}%)"
done
echo "=== Done ==="
```

### GPU Allocation Summary (After Phase 1)

```
┌────────┬───────────────────────────────────────────────────────────────┐
│ GPU    │ Service                                                      │
├────────┼───────────────────────────────────────────────────────────────┤
│ GPU 0  │ NIM LLM (Nemotron Nano 8B → upgrade to 49B Day 4)          │
│ GPU 1  │ NIM LLM (tensor-parallel pair with GPU 0)                   │
│ GPU 2  │ Earth-2 Studio (via JupyterLab Python)                      │
│ GPU 3  │ Earth-2 StormScope Nowcasting                               │
│ GPU 4  │ NIM Embedding (NV-Embed-v2)                                 │
│ GPU 5  │ NIM Reranker (NV-Rerank-Mistral-4B)                         │
│ GPU 6  │ cuOpt Route Optimization                                    │
│ GPU 7  │ RESERVE — Llama fallback / batch jobs                       │
└────────┴───────────────────────────────────────────────────────────────┘
```

### ✅ Phase 1 Checklist

- [ ] SSH into cluster, all 8 GPUs visible
- [ ] Directory structure created at `/raid/team/weatherise/`
- [ ] Code uploaded from laptop
- [ ] `.env` file uploaded
- [ ] NIM LLM running on GPU 0-1 (port 8000) → tested with curl
- [ ] NIM Embedding running on GPU 4 (port 8001) → tested with curl
- [ ] NIM Reranker running on GPU 5 (port 8002) → tested
- [ ] cuOpt running on GPU 6 (port 8083) → tested
- [ ] Earth-2 Studio installed + StormScope model downloaded
- [ ] Redis running (port 6379) → PING=PONG
- [ ] Milvus running (port 19530) → healthz OK
- [ ] PostgreSQL running (port 5432) → pg_isready OK
- [ ] `healthcheck.sh` passes ALL services ✅

---

## 📦 Phase 2: Data Ingestion & RAG Pipeline (Day 1 PM — Day 2)

> **⏳ Coming in next update — say "tiếp" to continue**

---

## 🤖 Phase 3: Agent Development (Day 2 — Day 3)

> **⏳ Coming in next update**

---

## 🎨 Phase 4: Frontend MVP + Real-Time Features (Day 3 — Day 4)

> **⏳ Coming in next update**

---

## ✨ Phase 5: Polish, Export & Monitoring (Day 4 — Day 5)

> **⏳ Coming in next update**

---

## 🎤 Phase 6: Demo & Presentation (Day 6)

> **⏳ Coming in next update**

---

## ✅ Master Checklist

### Pre-Hackathon
- [ ] NGC API Key received from VTS
- [ ] OpenWeatherMap API key registered
- [ ] SpeedSMS account + token registered
- [ ] Google Places API key registered
- [ ] HuggingFace token registered
- [ ] Code skeleton pre-written on laptop
- [ ] `.env` file prepared
- [ ] Da Nang data pre-scraped (TripAdvisor, Wikivoyage, blogs)

### Phase 1: Cluster Setup (Day 1 AM)
- [ ] Cluster access verified (SSH + JupyterLab)
- [ ] All 8 GPUs visible
- [ ] NIM LLM on GPU 0-1 ✅
- [ ] NIM Embed on GPU 4 ✅
- [ ] NIM Rerank on GPU 5 ✅
- [ ] cuOpt on GPU 6 ✅
- [ ] Earth-2 on GPU 2-3 ✅
- [ ] Redis + Milvus + PostgreSQL ✅

### Phase 2: Data & RAG (Day 1 PM — Day 2)
- [ ] Raw data uploaded to cluster
- [ ] Chunking pipeline done
- [ ] Embeddings generated via NIM
- [ ] Milvus collection loaded
- [ ] Hybrid retrieval working
- [ ] Reranker integrated

### Phase 3: Agents (Day 2 — Day 3)
- [ ] Orchestrator Agent (LangGraph)
- [ ] Weather Agent (Earth-2 + Open-Meteo)
- [ ] Attraction Agent (RAG)
- [ ] Route Agent (cuOpt)
- [ ] Local Expert Agent (RAG)
- [ ] Safety Agent (NeMo Guardrails)
- [ ] Weather Watcher Agent (APScheduler + background)
- [ ] Notification Agent (SMS + WebSocket)
- [ ] End-to-end pipeline test ✅

### Phase 4: Frontend (Day 3 — Day 4)
- [ ] Gradio MVP chat UI
- [ ] Gradio → FastAPI connection
- [ ] Map integration (Folium/Leaflet)
- [ ] Weather card component
- [ ] SMS opt-in form
- [ ] WebSocket real-time alerts

### Phase 5: Polish (Day 4 — Day 5)
- [ ] Plan export (image + QR code)
- [ ] Next.js PWA (if time)
- [ ] Mobile responsive
- [ ] Monitoring (nvidia-smi dashboard)
- [ ] Demo queries tested
- [ ] Edge cases handled

### Phase 6: Demo (Day 6)
- [ ] Demo script prepared
- [ ] Backup plan ready
- [ ] Presentation slides done
- [ ] Live demo tested 3 times
- [ ] All services running stable
- [ ] Ports accessible for judges
