# 🌦️ Weatherise MVP — Simplified Multi-Agent System

> **Team:** Weatherise (4 members) | **Hackathon Duration:** 5 days | **MVP Focus:** Core Weather-Risk Intelligence & Proactive Alerts 

---

## 📋 Table of Contents

1. [Project Overview (MVP Scope)](#-project-overview-mvp-scope)
2. [Why This Matters Now](#-why-this-matters-now)
3. [Platform Strategy](#-platform-strategy)
4. [System Architecture](#-system-architecture)
5. [Agent Design](#-agent-design)
6. [Data & API Sources](#-data--api-sources)
7. [Tech Stack](#-tech-stack)
8. [User Input / Output](#-user-input--output)
9. [UI / Frontend Design](#-ui--frontend-design)
10. [Deployment](#-deployment)
11. [Monitoring & Observability](#-monitoring--observability)

---

## 🎯 Project Overview (MVP Scope)

**Weatherise MVP** focuses exclusively on the core innovation of the platform: **translating raw weather data into Vietnam-specific weather risks and proactively alerting users when conditions change.** 

The MVP operates as a **4-agent system** that proves the highest-value concept:
```
User Query → Orchestrator Agent → Weather Agent → Risk Analysis & Recommendation
                                        ↕ (real-time loop via Redis)
                          Weather Watcher Agent → Notification Agent → Real-Time Alert
```

### MVP Focus Areas

| Area | Description |
|------|-------------|
| 🌤️ **Weather** | Open-Meteo (hourly) + OpenWeatherMap (current). Mock Earth-2 pipeline for demonstration. |
| ⚡ **Risk Scoring** | Rule-based engine translating Rain, Heat, and Wind into actionable insights. |
| 🔔 **Real-Time Alerts** | Background monitoring detecting weather conflicts and pushing WebSocket/UI banner alerts. |
| 🔄 **Architecture** | Built on LangGraph and FastAPI to provide a robust, stateful agent workflow. |

---

## 🔥 Why This Matters Now

Even in its simplified MVP state, Weatherise solves a critical problem: **Tourists lack proactive weather guidance.**
While standard apps show "30% rain", they do not say "It is unsafe to visit Son Tra Peninsula at 4 PM due to high wind risk." The MVP proves we can bridge this gap automatically.

---

## 📱 Platform Strategy

### Recommended: **Gradio / Streamlit UI (Fast Demo)**

For the MVP, we use a Python-based UI (Gradio or Streamlit) that connects to our robust FastAPI backend. This allows rapid iteration while ensuring the backend logic is completely decoupled and production-ready.

```mermaid
graph LR
    subgraph "MVP Frontend"
        A[Gradio / Streamlit Chat UI] -->|REST / WS| B[FastAPI Backend]
    end
    subgraph "MVP Backend"
        B --> C[4-Agent LangGraph System]
        C --> D[(Redis Session Store)]
    end
    style A fill:#4CAF50,color:#fff
    style B fill:#FF9800,color:#fff
```

---

## 🏗️ System Architecture

### High-Level MVP Architecture

```mermaid
graph TB
    %% 1. Tầng User & Browser
    subgraph "👤 User Space"
        Client[Client] <--> Browser[Browser]
    end

    %% 2. Tầng Frontend
    subgraph "🖥️ Frontend Layer"
        UI[Gradio / Streamlit UI]
    end

    %% 3. Tầng API Gateway
    subgraph "🔌 API Gateway"
        GW[FastAPI Gateway]
        WS[WebSocket Stream]
    end

    %% 4. Tầng Multi-Agent Orchestration Layer
    subgraph "🤖 Multi-Agent Orchestration Layer"
        ORCH[Orchestrator Agent<br/>LangGraph StateGraph]
        WA[Weather Agent<br/>Forecast & Risk Scoring]
    end

    %% 5. Tầng Real-Time Monitor
    subgraph "⏰ Real-Time Monitor (Background)"
        WW[Weather Watcher Agent<br/>APScheduler]
        NA[Notification Agent<br/>Alert Delivery]
    end

    %% 6. Tầng Notification
    subgraph "📱 Notification Layer"
        UIALERT[UI Alert Banner]
        WSOCK[WebSocket Push]
    end

    %% 7. Tầng Knowledge
    subgraph "📚 Knowledge Layer"
        RD[(Redis Cache<br/>Sessions & Weather)]
    end

    %% 8. Tầng External Services
    subgraph "🌍 External Services"
        OM[Open-Meteo API<br/>Free Hourly]
        OWM[OpenWeatherMap API<br/>Current]
        E2MOCK[Earth-2 Mock Client]
    end

    %% --- ĐƯỜNG KẾT NỐI HỆ THỐNG ---

    Browser <--> UI
    UI --> GW
    GW --> WS
    WS --> ORCH
    
    ORCH --> WA
    WA --> RD
    
    WA --> OM
    WA --> OWM
    WA -.-> E2MOCK
    
    ORCH -->|1. Register session| RD
    WW -->|2. Scan active sessions| RD
    WW -->|3. Query live forecast| OM
    WW -->|3. Query live forecast| OWM
    WW -->|4. Detect conflict| NA
    
    NA -->|5. Trigger Re-plan| ORCH
    NA -->|5. Push WebSocket| WSOCK
    NA -->|5. Show Alert| UIALERT
    
    WSOCK -.->|Real-time alert| UI
    UIALERT -.->|Banner update| UI

    %% Style & Màu sắc
    style ORCH fill:#FF6B35,color:#fff,stroke:#333,stroke-width:2px
    style WW fill:#E91E63,color:#fff,stroke:#333,stroke-width:2px
    style NA fill:#E91E63,color:#fff,stroke:#333,stroke-width:2px
    style WA fill:#FF9800,color:#fff
    style UI fill:#2196F3,color:#fff
    style OM fill:#4CAF50,color:#fff
    style RD fill:#DC382D,color:#fff
```
![alt text](diagram/mvp_system_architecture.png)
### Request Flow (Sequence Diagram)

```mermaid
sequenceDiagram
    participant U as 👤 User
    participant UI as 🖥️ Gradio UI
    participant O as 🎯 Orchestrator Agent
    participant W as 🌦️ Weather Agent
    participant RD as 🗄️ Redis Session
    participant WW as 🔔 Weather Watcher
    participant N as 📢 Notification Agent

    U->>UI: "I want to visit Son Tra at 6 PM"
    UI->>O: Parse Intent & Plan Task
    O->>W: Get Weather Risk for Son Tra @ 6 PM
    W->>W: Fetch Open-Meteo & Score Risks
    W->>O: Return (High Rain Risk, Poor Suitability)
    O->>UI: Return Recommendation (Avoid outdoor)
    O->>RD: Save Session (Son Tra, 6 PM, Status)
    
    Note over WW,RD: Background Loop (Every 5 mins)
    WW->>RD: Scan active sessions
    WW->>W: Fetch latest weather for Son Tra
    W-->>WW: Rain probability increased!
    WW->>WW: Detect Conflict
    WW->>N: Trigger Notification Event
    
    N->>UI: WebSocket Push / Alert Banner
    N->>O: Request safer alternative
    O->>UI: Show Indoor Alternative
```

---

## 🤖 Agent Design

We implement 4 highly focused agents for the MVP:

### 1. Orchestrator Agent (LangGraph)
- **Role:** The brain of the system. Manages the workflow state.
- **Responsibilities:** Extracts location/time from user input, invokes the Weather Agent, formats the final output, and saves active sessions to Redis.

### 2. Weather Agent
- **Role:** Weather data fetcher and risk interpreter.
- **Responsibilities:** Fetches data from Open-Meteo/OWM. Applies a Rule-Based logic engine (e.g., Rain > 60% = High Risk). Outputs a standardized `WeatheriseRiskSchema`.

### 3. Weather Watcher Agent (Background)
- **Role:** Proactive monitoring daemon.
- **Responsibilities:** Uses `APScheduler` to iterate over active user sessions in Redis. Re-fetches weather data periodically, compares risk against baseline, and triggers alerts if weather degrades.

### 4. Notification Agent
- **Role:** Alert formatting and delivery.
- **Responsibilities:** Takes conflict data from the Watcher, formats it into readable text, and pushes the alert to the UI via WebSocket.

---

## 🌍 Data & API Sources

| Service | Purpose | Type |
|---------|---------|------|
| **Open-Meteo API** | Free, no-key hourly forecasts (16-day). | Primary Data Source |
| **OpenWeatherMap** | Current conditions fallback. | Secondary Data Source |
| **Earth-2 Mock** | Simulated NVIDIA Earth-2 data endpoints. | Demo Integration |

---

## 🛠️ Tech Stack

| Category | MVP Technology |
|----------|----------------|
| **Backend Framework** | FastAPI, Uvicorn |
| **Agent Orchestration** | LangGraph, LangChain |
| **Frontend UI** | Gradio / Streamlit |
| **State & Caching** | Redis |
| **LLM / Parsing** | OpenAI API (fallback) / Mock |
| **Background Jobs** | APScheduler |

---

## 📥 User Input / Output

### Input Mechanisms:
- Natural language text query via the Chat Interface.
- Manual "Trigger Weather Alert" developer button for demonstration purposes.

### Output Mechanisms:
1. **Chat Response:** Clear weather summary + risk level + structured recommendation.
2. **Real-time Alert Banner:** A dynamic warning banner that pops up natively in the UI via WebSocket when the background agent detects a conflict.

---

## 🎨 UI / Frontend Design

### Gradio Interface Layout
- **Left Panel:** Main chat interface for user interaction and itinerary requests.
- **Right Panel (Debug & Status):**
  - Displays the current active sessions stored in Redis.
  - Controls to manually "Simulate Weather Degradation" for judges.
- **Top Banner:** Hidden by default. Flashes with warning colors when the Notification Agent pushes an alert.

---

## 🚀 Deployment

### Local Docker Compose
The MVP is designed to run seamlessly on a local machine or a lightweight cloud VM using Docker Compose.

```yaml
services:
  redis:
    image: redis:alpine
    ports: ["6379:6379"]
  backend:
    build: .
    ports: ["8000:8000"]
    depends_on: [redis]
```
*(The UI application can run alongside the backend or as a separate container).*

---

## 📊 Monitoring & Observability

- **Application Logs:** Standard Python `logging` to stdout.
- **Agent Tracing:** LangGraph standard debug output to terminal to trace node execution.
- **Background Jobs:** Console output indicating when APScheduler scans Redis sessions and detects changes.

---


