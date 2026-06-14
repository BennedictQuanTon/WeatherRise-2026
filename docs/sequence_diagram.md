# 📊 Sequence Diagram — Weatherise v2

This document details the execution flow of the **Weatherise v2** system, detailing how requests are parsed, enriched, evaluated for weather risk, and returned to the user. All services are optimized for the **8x NVIDIA H200 GPU Cluster** and orchestrated via **NVIDIA NeMo Agent Toolkit**.

---

## 1. System Execution Sequence Diagram

The sequence diagram below shows how a user's natural language request moves through the system:

```mermaid
sequenceDiagram
    autonumber
    actor User as User (Web Browser)
    participant Web as Next.js Web PWA
    participant API as FastAPI Backend
    participant Guard as NeMo Guardrails
    participant Orch as Orchestrator (LangGraph)
    participant Agent as Domain Context Agent
    participant MCP as MCP Server Gateway
    participant Ext as External APIs (Weather/Map)
    participant DB as Data Layer (Postgres/Qdrant)
    participant PathB as PathBWeatherService
    participant NIM as NVIDIA NIM (Nemotron-3 120B)
    participant Localizer as Qwen Localizer NIM

    %% USER REQUEST ENTRY
    User->>Web: Input prompt ("Plan 3 days in Da Nang, avoid storms")
    Web->>API: Send query over WebSocket connection
    
    %% INPUT GUARDRAILS CHECK
    API->>Guard: Validate query (Input Guardrails)
    Guard-->>API: Query approved (Safe, In-domain)
    
    %% PROMPT PARSING
    API->>NIM: Parse query using Qwen-35-27B Parser NIM
    Note over NIM: Accelerated via H200 GPU Inference
    NIM-->>API: Return structured JSON (domain, location, time)
    
    %% ORCHESTRATION START
    API->>Orch: Start state machine execution loop
    Note over Orch: NeMo Agent Toolkit manages state bindings
    Orch->>Agent: Route state payload to TourismContextAgent
    
    %% CONTEXT ENRICHMENT & CACHE-MISS RESOLUTION
    Agent->>DB: Search vector base (Qdrant RAG)
    DB-->>Agent: Return offline attractions and rules
    Agent->>Agent: Generate ContextGapReport (Identify missing details)
    
    alt Coordinates or time are missing
        Agent->>MCP: Call location.resolveCoordinates / time.resolveTimeRange
        MCP->>Ext: Query geocoding / natural time APIs
        Ext-->>MCP: Return resolved Lat/Lon and Calendar dates
        MCP-->>Agent: Return resolved coordinate & temporal metadata
    end

    alt Attraction POIs or Restaurants are sparse
        Agent->>MCP: Call place.searchPlaces / searchRestaurants
        MCP->>Ext: Query OpenStreetMap Overpass API
        Ext-->>MCP: Return nearby POI & Restaurant JSON
        MCP-->>Agent: Return missing POI lists
    end

    %% MULTI-SOURCE WEATHER INGESTION
    Agent->>MCP: Call weather.getForecast (coordinates, target dates)
    MCP->>Ext: Query Open-Meteo, WeatherAPI, and Tomorrow.io
    Ext-->>MCP: Return hourly forecast records
    MCP-->>Agent: Return multi-source weather payload
    
    %% CACHING RESULTS
    Agent->>DB: Cache dynamic POIs & weather (Qdrant & Redis)
    Agent-->>Orch: Return Fully Processed Payload JSON
    Orch-->>API: Return finished orchestration state
    
    %% PATH B WEATHER CONSENSUS
    API->>PathB: Run PathBWeatherService pipeline
    PathB->>PathB: Normalize records & validate quality
    PathB->>NIM: Call NIM Weather Arbiter to resolve contradictions
    NIM-->>PathB: Return selected Consensus forecast (Gold Weather Decision)
    PathB-->>API: Return Gold Weather Decision
    
    %% RULE ENGINE RISK CHECK
    API->>API: Run deterministic Rule Engine (Calculate risk score)
    
    %% FINAL REASONING GENERATION
    API->>NIM: Send prompt (context + risk score + consensus forecast)
    NIM-->>API: Return English itinerary & advice
    
    %% TRANSLATION & LOCALIZATION PASS
    alt Prompt language is Vietnamese
        API->>Localizer: Request translation & Vietnamese naturalization
        Localizer-->>API: Return localized Vietnamese response
    end
    
    %% OUTPUT GUARDRAILS CHECK
    API->>Guard: Check response safety (Output Guardrails)
    Guard-->>API: Response approved
    
    %% FRONTEND PUSH
    API-->>Web: Push final payload (Itinerary JSON + map routes)
    Web-->>User: Render split-pane UI (interactive map + charts)
```

---

## 2. Component Interactions Breakdown

### A. Input Verification (NeMo Guardrails)
Before any LLM calls occur, **NeMo Guardrails** evaluates the incoming string. It blocks SQL injections, script inputs, and questions unrelated to weather, construction, agriculture, or tourism. This step saves H200 GPU resources by filtering out invalid traffic.

### B. Natural Language Parsing
The **Qwen-35-27B Parser NIM** runs on two H200 GPUs. It processes unstructured inputs to extract key parameters (e.g., location name, calendar date range, domain, and constraint strings) and returns them in a structured JSON schema.

### C. Context Enrichment
The routed **Context Agent** evaluates the parser outputs. If details are missing or databases return sparse results, the agent resolves them using the **MCP Server**:
* Geocodes location text to latitude and longitude.
* Translates conversational dates into ISO strings.
* Queries external search engines for tourist spots, construction site info, or agricultural cooperatives.
* Downloads weather telemetry forecasts from multiple providers.

### D. Path B Weather Consensus
The **PathBWeatherService** processes forecasts from multiple providers:
* **Normalizer:** Standardizes different API formats into a single schema.
* **Validator:** Checks for out-of-bounds metrics (e.g., negative wind speeds) and removes faulty sources.
* **Arbiter:** Sends the comparison data to **Nemotron-3 Super 120B** to select the most reliable forecast (Gold Weather Decision).

### E. Reasoning Layer
The **Nemotron-3 Super 120B NIM** processes the final system prompt. It combines the Gold Weather Decision, local rules, and POI details to generate safe, personalized recommendations.

### F. Output Verification (NeMo Guardrails)
Before the response is returned to the user, NeMo Guardrails scans the generated text. It verifies that the advice aligns with safety rules and does not contain factual errors or hallucinations.

### G. Client Presentation
The **Next.js Web PWA** receives the JSON response and displays it. It renders path coordinates on a Leaflet map and plots weather metrics (nhiệt độ, mưa, gió) on Recharts graphs.
