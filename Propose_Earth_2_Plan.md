# 🛠️ Weatherise — Earth-2 Enterprise Intelligence Layer Implementation Guide

> **Updated direction:** Weatherise is no longer only a Da Nang travel planner.  
> It is now an **enterprise-ready orchestration, setup, parsing, and interpretation layer around NVIDIA Earth-2 and related AI weather tools**.  
> The Da Nang travel optimizer remains the **demo domain**, while the reusable core is an Earth-2-powered weather intelligence platform for enterprises.

---

## 0. Executive Summary

### What Weatherise is now

Weatherise is a **multi-agent enterprise weather intelligence system** that helps organizations use advanced AI weather models such as **NVIDIA Earth-2** without needing to deeply understand every deployment detail, raw tensor format, or scientific weather variable.

The project solves three enterprise problems:

1. **Earth-2 setup is powerful but complex**  
   Enterprises may struggle with GPU allocation, NIM containers, Earth2Studio, model endpoints, output files, weather variables, and deployment health checks.

2. **Earth-2 output is not business-readable by default**  
   Earth-2 and similar weather models produce weather fields, arrays, tensors, NetCDF/Zarr-like data, forecast grids, or model-specific outputs. Enterprise users need risk summaries, action recommendations, APIs, dashboards, and alerts.

3. **Weather prediction must be translated into domain impact**  
   A logistics team, tourism operator, port manager, school, construction site, or agriculture team does not only need “precipitation = X.” They need “what should we do?”

### Updated core idea

```txt
Earth-2 / Weather Model Output
        ↓
Weatherise Earth-2 Setup + Health Layer
        ↓
Weatherise Output Parser + Standard Forecast Schema
        ↓
Weatherise Weather Signal Detection
        ↓
Weatherise Enterprise Risk Interpretation
        ↓
Dashboard / API / Alert / Domain Workflow
```

### One-line pitch

> **Earth-2 predicts the atmosphere. Weatherise turns that prediction into enterprise-ready decisions.**

---

## 1. Project Positioning

### Old framing

```txt
Weatherise = weather-aware Da Nang travel planner
```

### New framing

```txt
Weatherise = enterprise middleware and intelligence layer for Earth-2 weather AI
```

### Demo framing

```txt
Da Nang travel optimization = first demo use case
```

This means the Da Nang itinerary system is not thrown away. Instead, it becomes a clear proof of how Weatherise can apply Earth-2 outputs to a real domain:

```txt
Weather risk
→ outdoor activity suitability
→ route optimization
→ dynamic re-planning
→ SMS/WebSocket alert
```

### Reusable domains

The same Weatherise core can later support:

| Domain | Weatherise output |
|---|---|
| Tourism | Rain-safe itinerary, attraction replacement, SMS alert |
| Logistics | Route delay risk, unsafe loading window, warehouse warning |
| Agriculture | Irrigation/spraying timing, heat/rain/wind risk |
| Construction | Crane/wind risk, rain delay, outdoor work safety |
| Ports/coastal ops | Wind/rain/sea-weather operational risk |
| Events | Outdoor event timing, backup indoor plan |
| Disaster response | Heavy-rain and strong-wind risk summaries |

---

## 2. Core Value Compared to Earth-2 Alone

Weatherise does **not** replace Earth-2.

Weatherise adds the missing enterprise layers around it.

| Layer | Earth-2 provides | Weatherise adds |
|---|---|---|
| Model capability | Forecasting, nowcasting, downscaling | Setup wrapper, fallback routing, health checks |
| Data output | Weather fields, tensors, arrays, model outputs | Standard JSON schema and readable summaries |
| Scientific meaning | Raw variables like wind, precipitation, pressure | Risk levels, business impact, confidence |
| Deployment | Model containers/tooling | Guided deployment scripts and diagnostics |
| Domain usage | General weather capability | Tourism/logistics/agriculture/etc. workflows |
| Output format | Model/API-specific output | Dashboard, REST API, WebSocket, SMS, reports |
| Reliability | Single model endpoint | Multi-source fallback and status monitoring |

---

## 3. Updated System Architecture

### High-level architecture

```mermaid
graph TB
    subgraph "User / Enterprise Layer"
        USER[Enterprise User / Tourist / Operator]
        UI[Dashboard / PWA / Gradio Demo]
        API[FastAPI Enterprise API]
    end

    subgraph "Weatherise Multi-Agent Core"
        ORCH[Orchestrator Agent<br/>LangGraph StateGraph]
        SETUP[Setup & Health Agent]
        SRC[Source & Data Agent]
        E2A[Earth-2 Inference Agent]
        PARSER[Weather Output Parser Agent]
        RISK[Risk & Business Impact Agent]
        DELIV[Delivery Agent]
    end

    subgraph "Earth-2 + Weather Model Layer"
        E2STUDIO[Earth2Studio]
        FCN[FourCastNet / FourCastNet3]
        ATLAS[Atlas / Medium Range]
        STORM[StormScope / Nowcasting]
        CORR[CorrDiff Downscaling]
        MOCK[Fallback / Mock Earth-2 Client]
    end

    subgraph "External Weather Sources"
        OM[Open-Meteo]
        OWM[OpenWeatherMap]
        GFS[NOAA GFS]
        ECMWF[ECMWF Open Data]
        RADAR[RainViewer / Radar]
    end

    subgraph "Optional Da Nang Travel Demo"
        RAG[RAG Knowledge Base]
        CUOPT[NVIDIA cuOpt]
        VAL[Valhalla / OSM]
        SMS[SpeedSMS]
    end

    subgraph "Storage & Infrastructure"
        REDIS[(Redis Cache)]
        PG[(PostgreSQL)]
        MILVUS[(Milvus Vector DB)]
        RAID[/raid/team Storage]
        GPU[8× NVIDIA H200]
    end

    USER --> UI
    UI --> API
    API --> ORCH

    ORCH --> SETUP
    ORCH --> SRC
    ORCH --> E2A
    ORCH --> PARSER
    ORCH --> RISK
    ORCH --> DELIV

    SETUP --> GPU
    SETUP --> E2STUDIO
    SRC --> OM
    SRC --> OWM
    SRC --> GFS
    SRC --> ECMWF
    SRC --> RADAR

    E2A --> E2STUDIO
    E2A --> FCN
    E2A --> ATLAS
    E2A --> STORM
    E2A --> CORR
    E2A --> MOCK

    PARSER --> RAID
    PARSER --> PG
    RISK --> REDIS
    DELIV --> UI
    DELIV --> API
    DELIV --> SMS

    DELIV --> RAG
    DELIV --> CUOPT
    CUOPT --> VAL
    RAG --> MILVUS

    style E2A fill:#76B900,color:#fff
    style E2STUDIO fill:#76B900,color:#fff
    style FCN fill:#76B900,color:#fff
    style CORR fill:#76B900,color:#fff
    style STORM fill:#76B900,color:#fff
    style ORCH fill:#FF6B35,color:#fff
    style RISK fill:#EF4444,color:#fff
    style DELIV fill:#0EA5E9,color:#fff
```

---

## 4. Updated Earth-2 Optimization Workflow

This is the new core workflow that should be added to the README and implementation plan.

```mermaid
flowchart TD
    A[Enterprise request<br/>location, asset, time horizon, risk type] --> B[Setup & Health Agent]
    B --> C{Earth-2 available?}

    C -- Yes --> D[Earth-2 Inference Agent]
    C -- No --> F[Fallback Weather Source<br/>Open-Meteo / GFS / Mock]

    D --> D1[FourCastNet / Atlas<br/>global or medium-range forecast]
    D --> D2[StormScope<br/>0-6h nowcasting if available]
    D --> D3[CorrDiff<br/>regional downscaling if available]

    D1 --> E[Raw Forecast Output]
    D2 --> E
    D3 --> E
    F --> E

    E --> G[Weather Output Parser Agent<br/>xarray / NetCDF / Zarr / JSON / tensor → standard schema]
    G --> H[Weather Signal Detection<br/>rain, wind, heat, storm, monsoon, typhoon]
    H --> I[Enterprise Risk Model<br/>thresholds + confidence + domain rules]
    I --> J[Business Impact Interpreter<br/>tourism/logistics/agriculture/construction]
    J --> K[Delivery Agent<br/>dashboard, API, alert, report]

    K --> L[User-readable result]
    K --> M[Machine-readable API JSON]
    K --> N[SMS / WebSocket alert]
```

### Main principle

Weatherise should treat Earth-2 output as **scientific weather data**, then transform it into **enterprise weather intelligence**.

```txt
Raw model field
→ normalized forecast schema
→ risk score
→ business impact
→ recommended action
```

---

## 5. Updated Agent Design

### Agent 1 — Setup & Health Agent

**Purpose:** Make Earth-2 easier to set up, verify, and operate.

Responsibilities:

```txt
- Check GPU visibility
- Check CUDA and PyTorch
- Check NGC API key presence
- Check NIM containers
- Check Earth2Studio import
- Check model endpoint health
- Check storage paths
- Check fallback weather APIs
- Produce setup diagnostic report
```

Output example:

```json
{
  "gpu_available": true,
  "gpu_count": 8,
  "earth2studio_import": "ok",
  "fourcastnet_endpoint": "unavailable",
  "fallback_openmeteo": "ok",
  "status": "degraded_but_usable"
}
```

---

### Agent 2 — Source & Data Agent

**Purpose:** Collect data from Earth-2 and non-Earth-2 weather sources.

Sources:

```txt
- Earth2Studio
- FourCastNet / Atlas
- StormScope
- CorrDiff
- Open-Meteo
- OpenWeatherMap
- GFS
- ECMWF Open Data
- RainViewer
```

Role:

```txt
- Choose available source
- Handle fallback logic
- Fetch forecast input/output
- Cache repeated results
- Store raw response
```

---

### Agent 3 — Earth-2 Inference Agent

**Purpose:** Run or call Earth-2 tools.

Earth-2 tools to support:

| Tool | Use in Weatherise |
|---|---|
| Earth2Studio | Python workflow for Earth-2 data/model operations |
| FourCastNet / FourCastNet3 | Global short-to-medium range forecast |
| Atlas / Medium Range | Longer-horizon global forecast, if available |
| StormScope | 0-6h nowcasting / storm movement, if available |
| CorrDiff | Downscale coarse forecast into higher-resolution local field |
| NIM containers | Serve model endpoints locally when available |
| Mock Earth-2 client | Fallback when real Earth-2 is not ready |

Important rule:

```txt
The demo must not fail if Earth-2 cannot run.
```

Fallback plan:

```txt
if Earth-2 real endpoint available:
    use Earth-2
elif GFS/Open-Meteo available:
    use fallback source
else:
    use mock Earth-2 sample output
```

---

### Agent 4 — Weather Output Parser Agent

**Purpose:** Convert raw model output into a simple Weatherise schema.

Possible raw Earth-2 output formats:

```txt
- xarray Dataset / DataArray
- NetCDF
- Zarr
- NumPy tensors
- GRIB-style weather files
- tar/archive files from NIM output
- API JSON
```

Standard Weatherise schema:

```json
{
  "source": "earth2_or_fallback",
  "model": "fourcastnet_or_openmeteo",
  "location": {
    "name": "Da Nang",
    "lat": 16.0544,
    "lon": 108.2022
  },
  "time_horizon": "24h",
  "forecast_time": "2026-06-09T12:00:00Z",
  "variables": {
    "precipitation_mm": 24.5,
    "rain_probability": 0.82,
    "temperature_2m_c": 30.2,
    "wind_speed_10m_kmh": 31.0,
    "wind_gust_10m_kmh": 48.0,
    "pressure_msl_hpa": 1005.1,
    "humidity_percent": 84
  },
  "metadata": {
    "resolution": "model-dependent",
    "status": "real",
    "raw_path": "/raid/team/weatherise/data/weather/run_001.nc"
  }
}
```

---

### Agent 5 — Risk & Business Impact Agent

**Purpose:** Convert weather variables into enterprise risk and action.

Risk categories:

```txt
- Heavy rain risk
- Strong wind risk
- Heat risk
- Storm risk
- Outdoor activity risk
- Route disruption risk
- Coastal operation risk
- Agriculture timing risk
- Construction safety risk
```

Example output:

```json
{
  "asset": "Da Nang Outdoor Tour",
  "risk_level": "high",
  "risk_type": "heavy_rain",
  "confidence": 0.78,
  "time_window": "next 24h",
  "business_impact": "Outdoor tourist activities may be disrupted.",
  "recommended_action": "Move outdoor locations to morning or replace with indoor attractions.",
  "explanation": [
    "High precipitation signal detected",
    "Wind direction suggests moisture transport from coastal area",
    "Fallback Open-Meteo and Earth-2-style forecast agree"
  ]
}
```

---

### Agent 6 — Delivery Agent

**Purpose:** Deliver the result to different consumers.

Outputs:

```txt
- Dashboard card
- REST API response
- WebSocket alert
- SMS message
- PDF/PNG report
- Enterprise JSON export
- Da Nang itinerary replacement
```

Example API endpoint:

```http
POST /v1/weather-risk
```

Example request:

```json
{
  "domain": "tourism",
  "locations": [
    {
      "name": "Ba Na Hills",
      "lat": 15.9953,
      "lon": 107.9968
    }
  ],
  "time_horizon": "24h",
  "risk_types": ["rain", "wind"]
}
```

Example response:

```json
{
  "location": "Ba Na Hills",
  "rain_risk": "high",
  "wind_risk": "medium",
  "confidence": 0.76,
  "recommended_action": "Suggest indoor alternative or move visit to earlier time window.",
  "source_status": {
    "earth2": "unavailable",
    "openmeteo": "used",
    "mock_earth2": "not_used"
  }
}
```

---

## 6. Updated Repository Structure

```txt
WeatherRise-2026/
│
├── backend/
│   └── app/
│       ├── main.py                     # FastAPI entry point
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── agents/
│       │   ├── orchestrator.py         # LangGraph StateGraph
│       │   ├── weather.py              # Weather Agent (Earth-2 + fallback)
│       │   ├── attraction.py           # Attraction Agent (RAG)
│       │   ├── route.py                # Route Agent (cuOpt + OSM)
│       │   ├── local_expert.py         # Local Expert Agent (RAG)
│       │   ├── safety.py               # Safety Agent (NeMo Guardrails)
│       │   ├── watcher.py              # Weather Watcher (APScheduler background)
│       │   └── notifier.py             # Notification Agent (SMS + WebSocket)
│       ├── services/
│       │   ├── earth2_client.py        # Earth-2 model interface (FourCastNet/CorrDiff/StormScope)
│       │   ├── openmeteo_client.py     # Open-Meteo fallback weather API
│       │   ├── gfs_client.py           # GFS weather data client
│       │   ├── risk_rules.py           # Weather → travel/enterprise risk translator
│       │   ├── llm.py                  # NIM LLM client (OpenAI-compatible)
│       │   ├── rag.py                  # Milvus RAG retrieval
│       │   ├── cuopt.py                # NVIDIA cuOpt route optimizer
│       │   ├── sms.py                  # SpeedSMS wrapper
│       │   └── export.py               # Plan → PNG image + QR code
│       ├── configs/
│       │   └── config.py               # App configuration & env loading
│       ├── schemas/
│       │   └── weather_schema.py       # Pydantic weather schema (Weatherise standard)
│       └── models/
│           ├── request_schema.py       # User request Pydantic models
│           ├── forecast_schema.py      # Earth-2 forecast output schema
│           └── risk_schema.py          # Risk level Pydantic models
│
├── data/
│   ├── data_example.py                 # Example data loading script
│   ├── attractions/                    # Scraped attraction data (TripAdvisor, Google Places)
│   ├── milvus/                         # Milvus vector DB storage
│   ├── parsed/                         # Processed/chunked documents for RAG
│   ├── postgres/                       # PostgreSQL data directory
│   ├── raw/                            # Raw scraped data (HTML, JSON)
│   ├── redis/                          # Redis persistence data
│   ├── risk_outputs/                   # Cached risk translation results
│   └── weather/                        # Earth-2 / API weather data cache
│
├── frontend/
│   └── app/                            # Next.js PWA (Day 4-5)
│       └── app/                        # Next.js app router
│
├── gradio-ui/
│   ├── app.py                          # Gradio ChatInterface MVP
│   └── requirements.txt
│
├── scripts/
│   ├── healthcheck.sh                  # Service health check (all ports)
│   ├── start_gpu_services.sh           # Start NIM containers on specific GPUs
│   ├── start_data_services.sh          # Start Redis, Milvus, PostgreSQL
│   ├── test_earth2.py                  # Earth-2 integration test
│   ├── test_openmeteo.py               # Open-Meteo API test
│   ├── ingest_travel_data.py           # Data scraping & ingestion pipeline
│   └── setup_milvus.py                 # Milvus collection creation
│
└── reports/
|   └── report_example.py               # Report generation example
|
├── .gitignore
├── LICENSE
├── README.md                           # Main project documentation
├── IMPLEMENTATION_GUIDE.md             # Original implementation plan
```

---

## 7. Environment Variables

```bash
# === Cluster Access ===
NGC_API_KEY=<from-VTS>
CLUSTER_IP=<from-VTS>

# === Earth-2 / Model Services ===
EARTH2_MODE=auto                  # auto | real | fallback | mock
EARTH2_URL=http://localhost:8081
EARTH2STUDIO_CACHE=/raid/team/weatherise/models/earth2
FOURCASTNET_URL=http://localhost:8081/fourcastnet
CORRDIFF_URL=http://localhost:8082/corrdiff
STORMSCOPE_MODEL_PATH=/raid/team/weatherise/models/stormscope

# === Fallback Weather APIs ===
OPEN_METEO_BASE=https://api.open-meteo.com/v1
OPENWEATHERMAP_API_KEY=<your-key>
GFS_ENABLED=false
ECMWF_ENABLED=false

# === Da Nang Default Demo Coordinates ===
DANANG_LAT=16.0544
DANANG_LNG=108.2022

# === Intelligence Services ===
LLM_BASE_URL=http://localhost:8000/v1
EMBED_BASE_URL=http://localhost:8001/v1
RERANK_BASE_URL=http://localhost:8002/v1
CUOPT_URL=http://localhost:8083

# === Storage ===
REDIS_URL=redis://localhost:6379
MILVUS_HOST=localhost
MILVUS_PORT=19530
POSTGRES_URL=postgresql://postgres:weatherise@localhost:5432/weatherise

# === Optional Domain Integrations ===
SPEEDSMS_TOKEN=<your-token>
GOOGLE_PLACES_API_KEY=<your-key>
LANGSMITH_API_KEY=<optional>

# === App Config ===
WEATHER_WATCH_INTERVAL=600
```

---

## 8. Updated Phase Plan

## Phase 0 — Pre-Hackathon Preparation

### Required accounts

| Service | Why needed | Priority |
|---|---|---|
| NGC API Key | Pull/run NVIDIA NIM containers | Critical |
| Open-Meteo | Fallback weather source, no key | Critical |
| OpenWeatherMap | Fallback current/5-day weather | High |
| SpeedSMS | SMS demo alerts | Optional/High |
| Google Places | Da Nang travel demo | Optional |
| HuggingFace | Earth-2/checkpoint download | High |
| LangSmith | Agent tracing | Nice-to-have |

### Pre-write these files

```txt
backend/app/services/earth2_client.py
backend/app/services/openmeteo_client.py
backend/app/services/weather_schema.py
backend/app/services/risk_rules.py
backend/app/agents/setup_health_agent.py
backend/app/agents/earth2_inference_agent.py
backend/app/agents/output_parser_agent.py
backend/app/agents/risk_business_agent.py
backend/app/agents/delivery_agent.py
scripts/healthcheck.sh
scripts/test_earth2.py
```

---

## Phase 1 — Cluster Setup & Service Health

**Goal:** Make the environment usable and prove the Earth-2/fallback pipeline can run.

### Step 1.1 — Access cluster

```bash
ssh <user>@<CLUSTER_IP>
nvidia-smi
df -h /raid
docker ps
```

### Step 1.2 — Create project folders

```bash
mkdir -p /raid/team/weatherise/{code,data,models,logs}
mkdir -p /raid/nim-cache
mkdir -p /raid/team/weatherise/data/{weather,parsed,risk_outputs,attractions,milvus,postgres,redis}
```

### Step 1.3 — Deploy NIM LLM

```bash
export NGC_API_KEY=<key-from-VTS>

docker run -d --name nim-llm \
  --gpus '"device=0,1"' \
  --shm-size=16g \
  -e NGC_API_KEY \
  -v /raid/nim-cache:/opt/nim/.cache \
  -p 8000:8000 \
  nvcr.io/nim/nvidia/llama-3.1-nemotron-nano-8b-v1:latest
```

### Step 1.4 — Deploy embedding/reranker NIMs

```bash
docker run -d --name nim-embed \
  --gpus '"device=4"' \
  --shm-size=8g \
  -e NGC_API_KEY \
  -v /raid/nim-cache:/opt/nim/.cache \
  -p 8001:8000 \
  nvcr.io/nim/nvidia/nv-embedqa-e5-v5:latest

docker run -d --name nim-rerank \
  --gpus '"device=5"' \
  --shm-size=8g \
  -e NGC_API_KEY \
  -v /raid/nim-cache:/opt/nim/.cache \
  -p 8002:8000 \
  nvcr.io/nim/nvidia/nv-rerankqa-mistral-4b-v3:latest
```

### Step 1.5 — Deploy cuOpt

```bash
docker run -d --name cuopt \
  --gpus '"device=6"' \
  -e NGC_API_KEY \
  -v /raid/nim-cache:/opt/nim/.cache \
  -p 8083:5000 \
  nvcr.io/nvidia/cuopt:latest
```

### Step 1.6 — Earth2Studio setup

```bash
pip install earth2studio xarray netcdf4 zarr huggingface-hub
python -c "import earth2studio; print('Earth2Studio OK')"
```

If Earth2Studio fails, do not block the team. Switch to fallback mode:

```bash
export EARTH2_MODE=fallback
```

### Step 1.7 — Data services

```bash
docker run -d --name redis \
  -p 6379:6379 \
  -v /raid/team/weatherise/data/redis:/data \
  redis:7-alpine --appendonly yes

docker run -d --name postgres \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=weatherise \
  -e POSTGRES_DB=weatherise \
  -v /raid/team/weatherise/data/postgres:/var/lib/postgresql/data \
  postgres:16

docker run -d --name milvus \
  -p 19530:19530 -p 9091:9091 \
  -v /raid/team/weatherise/data/milvus:/var/lib/milvus \
  -e ETCD_USE_EMBED=true \
  -e COMMON_STORAGETYPE=local \
  milvusdb/milvus:latest milvus run standalone
```

---

## Phase 2 — Earth-2 Client + Output Parser

**Goal:** Build the core Weatherise value: convert hard-to-read weather model output into a standard enterprise schema.

### Build `earth2_client.py`

Responsibilities:

```txt
- Try real Earth-2 call
- Try Earth2Studio
- Try Open-Meteo fallback
- Try mock Earth-2 output
- Always return a standard forecast schema
```

Pseudo-logic:

```python
def get_forecast(location, horizon):
    if earth2_available():
        raw = call_earth2(location, horizon)
        return parse_earth2_output(raw)

    if openmeteo_available():
        raw = call_openmeteo(location, horizon)
        return parse_openmeteo_output(raw)

    raw = load_mock_forecast(location, horizon)
    return parse_mock_output(raw)
```

### Build `weather_schema.py`

Minimum schema:

```python
from pydantic import BaseModel
from typing import Optional, Dict

class Location(BaseModel):
    name: str
    lat: float
    lon: float

class ForecastVariables(BaseModel):
    precipitation_mm: Optional[float] = None
    rain_probability: Optional[float] = None
    temperature_2m_c: Optional[float] = None
    wind_speed_10m_kmh: Optional[float] = None
    wind_gust_10m_kmh: Optional[float] = None
    pressure_msl_hpa: Optional[float] = None
    humidity_percent: Optional[float] = None

class ForecastOutput(BaseModel):
    source: str
    model: str
    location: Location
    time_horizon: str
    forecast_time: str
    variables: ForecastVariables
    metadata: Dict
```

### Success condition

```txt
One function call returns a clean JSON forecast object,
regardless of whether the backend source is Earth-2, Open-Meteo, or mock data.
```

---

## Phase 3 — Risk & Business Impact Layer

**Goal:** Convert forecast data into readable enterprise decision output.

### Build `risk_rules.py`

Example rules:

```python
def classify_rain_risk(rain_probability, precipitation_mm):
    if rain_probability is not None and rain_probability >= 0.75:
        return "high"
    if precipitation_mm is not None and precipitation_mm >= 20:
        return "high"
    if rain_probability is not None and rain_probability >= 0.45:
        return "medium"
    return "low"

def classify_wind_risk(wind_speed_kmh, wind_gust_kmh):
    if wind_gust_kmh and wind_gust_kmh >= 50:
        return "high"
    if wind_speed_kmh and wind_speed_kmh >= 30:
        return "medium"
    return "low"
```

### Domain templates

| Domain | Example interpretation |
|---|---|
| Tourism | Replace outdoor attractions with indoor alternatives |
| Logistics | Delay outdoor loading or reroute vehicles |
| Agriculture | Delay spraying/irrigation decision |
| Construction | Review crane/outdoor work schedule |
| Event planning | Move outdoor event to indoor backup |

### Success condition

```txt
The system can convert forecast JSON into:
- risk level
- confidence
- business impact
- recommended action
- explanation
```

---

## Phase 4 — API + Dashboard Demo

**Goal:** Make the enterprise layer visible.

### Required endpoints

```txt
GET  /health
GET  /v1/source-status
POST /v1/weather-risk
POST /v1/domain-recommendation
GET  /v1/demo/danang
```

### Example `/v1/weather-risk`

Request:

```json
{
  "domain": "tourism",
  "locations": [
    {
      "name": "Ba Na Hills",
      "lat": 15.9953,
      "lon": 107.9968
    }
  ],
  "time_horizon": "24h",
  "risk_types": ["rain", "wind"]
}
```

Response:

```json
{
  "location": "Ba Na Hills",
  "source": "openmeteo_fallback",
  "earth2_status": "unavailable",
  "rain_risk": "high",
  "wind_risk": "medium",
  "confidence": 0.72,
  "business_impact": "Outdoor tourism activity may be disrupted.",
  "recommended_action": "Suggest an indoor alternative or move visit to morning.",
  "explanation": [
    "Rain probability exceeds threshold.",
    "Outdoor activity has high weather exposure."
  ]
}
```

### Dashboard cards

Minimum UI:

```txt
- Earth-2 service status
- Active data source
- Forecast variables
- Risk level
- Business impact
- Recommended action
- Raw JSON toggle
```

---

## Phase 5 — Da Nang Travel Demo Integration

**Goal:** Use the enterprise weather layer in the original travel demo.

Travel flow:

```txt
User asks for Da Nang itinerary
        ↓
Weatherise checks weather risk for each outdoor attraction
        ↓
Risk layer flags unsafe/unfavorable time windows
        ↓
RAG finds indoor alternatives
        ↓
cuOpt re-optimizes route
        ↓
LLM formats final itinerary
        ↓
SMS/WebSocket alerts if weather changes
```

Updated Mermaid:

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Dashboard / PWA
    participant API as FastAPI
    participant ORCH as Orchestrator
    participant WR as Weatherise Risk Layer
    participant E2 as Earth-2 / Fallback
    participant RAG as Attraction RAG
    participant CU as cuOpt
    participant LLM as LLM Formatter

    U->>UI: Request Da Nang travel plan
    UI->>API: POST /v1/demo/danang
    API->>ORCH: Start itinerary workflow

    ORCH->>WR: Check weather risk for candidate locations
    WR->>E2: Get forecast / nowcast / fallback
    E2-->>WR: Raw weather output
    WR-->>ORCH: Risk JSON + recommended actions

    ORCH->>RAG: Get attractions + indoor alternatives
    RAG-->>ORCH: Ranked POIs

    ORCH->>CU: Optimize route with weather constraints
    CU-->>ORCH: Optimized sequence

    ORCH->>LLM: Format itinerary and explanation
    LLM-->>API: Final travel plan
    API-->>UI: Map + cards + SMS option
```

---

## Phase 6 — Polish, Monitoring, and Presentation

### Monitoring

Track:

```txt
- GPU status
- Earth-2 status
- fallback source status
- API latency
- forecast freshness
- number of risk requests
- parse failures
- model/source disagreement
```

### Demo story

Use this final story:

```txt
1. Enterprise weather AI setup is hard.
2. Earth-2 output is powerful but not directly business-readable.
3. Weatherise wraps Earth-2/fallback sources into a simple enterprise API.
4. Weatherise converts raw weather fields into risk, impact, and action.
5. The Da Nang travel demo proves the workflow:
   rain risk → indoor alternative → route re-optimization → alert.
```

### Final pitch

> **Weatherise is an enterprise-ready intelligence layer for Earth-2. It simplifies deployment, standardizes raw model outputs, converts forecasts into business risk, and delivers decisions through APIs, dashboards, and domain workflows.**

---

## 9. Updated GPU Allocation

```mermaid
graph LR
    subgraph "GPU 0-1: LLM Serving"
        G0[NIM LLM<br/>Nemotron / Llama]
        G1[Tensor Parallel Pair]
    end

    subgraph "GPU 2-3: Earth-2 Weather Layer"
        G2[Earth2Studio<br/>FourCastNet / Atlas]
        G3[StormScope / CorrDiff<br/>if available]
    end

    subgraph "GPU 4-5: Retrieval Layer"
        G4[NV-Embed]
        G5[NV-Rerank]
    end

    subgraph "GPU 6: Optimization"
        G6[cuOpt]
    end

    subgraph "GPU 7: Reserve"
        G7[Fallback LLM / Batch Jobs]
    end

    style G0 fill:#1A237E,color:#fff
    style G2 fill:#0D47A1,color:#fff
    style G4 fill:#1B5E20,color:#fff
    style G6 fill:#4A148C,color:#fff
    style G7 fill:#374151,color:#fff
```

---

## 10. Master Checklist

### Core enterprise layer

- [ ] Setup & Health Agent implemented
- [ ] Earth2Studio import test implemented
- [ ] Earth-2 real/fallback/mock client implemented
- [ ] Open-Meteo fallback implemented
- [ ] Standard forecast schema implemented
- [ ] Output parser implemented
- [ ] Risk rules implemented
- [ ] Business interpretation templates implemented
- [ ] `/v1/weather-risk` endpoint implemented
- [ ] Dashboard shows Earth-2 status and fallback source
- [ ] Raw JSON → readable risk demo works

### Da Nang demo layer

- [ ] Attraction RAG loaded
- [ ] Indoor/outdoor metadata added
- [ ] Weather risk flags outdoor attractions
- [ ] cuOpt receives weather-aware constraints
- [ ] Route re-optimization works
- [ ] SMS/WebSocket alert demo works
- [ ] Travel plan shows weather explanation

### Presentation

- [ ] Explain Earth-2 is not replaced
- [ ] Explain Weatherise is the enterprise layer around Earth-2
- [ ] Show setup difficulty problem
- [ ] Show raw forecast vs readable risk
- [ ] Show Da Nang demo
- [ ] Show fallback reliability
- [ ] Show future enterprise domains

---

## 11. Minimum / Strong / Maximum Deliverables

### Minimum deliverable

```txt
Weatherise can call a weather source, parse output into a standard schema,
classify rain/wind risk, and display readable enterprise recommendations.
```

### Strong deliverable

```txt
Weatherise can run with Earth2Studio or fallback Open-Meteo,
show service health, produce domain-specific risk output,
and integrate the risk result into the Da Nang itinerary demo.
```

### Maximum deliverable

```txt
Weatherise can call Earth-2/FourCastNet or StormScope,
parse model output, downscale/interpret risk,
compare with fallback sources, trigger alerts,
and re-optimize enterprise/travel decisions in real time.
```

---

## 12. Final Understanding

Weatherise is now:

> **An enterprise AI weather middleware layer built around NVIDIA Earth-2.**

It is useful because:

```txt
Earth-2 provides powerful weather model output.
Weatherise makes that output easier to deploy, parse, understand, compare, and use.
```

The Da Nang travel system is the first complete demo:

```txt
Earth-2/fallback weather
→ readable risk
→ itinerary adaptation
→ route optimization
→ real-time alert
```
