# 🌦️ Weatherise v2 — Technical Architecture & 4-Layer Stack

> **Concise Reference for Research Paper, Poster & Presentation**  
> Platform: **Weatherise (Domain-Aware Multi-Agent System)**  
> Hardware: **8x NVIDIA H200 SXM5 GPU Cluster**  

---

## 1. 🛠️ Condensed 4-Layer Technology Stack

| Layer | Layer Name | Core Technologies & Models | Architectural Role |
| :---: | :--- | :--- | :--- |
| **1** | **Frontend & Interface** | `Next.js 14`, `TailwindCSS`, `Leaflet.js`, `Recharts`, `WebSockets` | Mobile-first PWA, interactive route maps, weather risk charts, and real-time SSE execution monitor. |
| **2** | **Multi-Agent & LLMs** | `LangGraph`, `NeMo Guardrails`, `Nemotron-3 Super 120B NIM`, `Qwen-35-27B NIM`, `nv-embedqa-e5-v5 NIM` | Stateful agent orchestration, intent parsing, safety guardrails, deep reasoning, and weather arbitration. |
| **3** | **Tools & Data (MCP)** | `Model Context Protocol (MCP)`, `NVIDIA cuOpt`, `Qdrant`, `PostgreSQL (PostGIS)`, `Redis 7`, `Open-Meteo` | Standardized tool calling, TSP route optimization, vector RAG, geospatial entity storage, caching, and weather ingestion. |
| **4** | **Backend & Infrastructure** | `FastAPI`, `Nginx`, `Docker`, `8x NVIDIA H200 SXM5 Cluster` | Async API gateway, reverse proxy, containerization, and high-throughput tensor-parallel GPU inference (TP=4 / TP=2). |

---

## 2. 📊 CSV Format (4 Layers)

```csv
Layer_ID,Layer_Name,Core_Technologies_and_Models,Architectural_Role
1,Frontend & Interface,"Next.js 14, TailwindCSS, Leaflet.js, Recharts, WebSockets","Mobile-first PWA, interactive route maps, weather risk charts, and real-time execution monitor"
2,Multi-Agent & LLMs,"LangGraph, NeMo Guardrails, Nemotron-3 Super 120B NIM, Qwen-35-27B NIM, nv-embedqa-e5-v5 NIM","Stateful agent orchestration, intent parsing, safety guardrails, deep reasoning, and weather arbitration"
3,Tools & Data (MCP),"Model Context Protocol (MCP), NVIDIA cuOpt, Qdrant, PostgreSQL (PostGIS), Redis 7, Open-Meteo","Standardized tool contracts, TSP route optimization, vector RAG, geospatial storage, and multi-source weather ingestion"
4,Backend & Infrastructure,"FastAPI, Nginx, Docker, 8x NVIDIA H200 SXM5 Cluster","Async API gateway, reverse proxy, container orchestration, and high-bandwidth GPU cluster execution"
```

---

## 3. ⚙️ Top 5 Core Mechanisms

1. **Schema-Enforced Intent Parsing & Guardrails:** **Qwen-35-27B NIM** translates raw prompts into validated JSON contracts; **NeMo Guardrails** block out-of-domain queries at ingress.
2. **Stateful Multi-Agent Orchestration:** **LangGraph** dynamically routes tasks to specialized domain agents (*Tourism, Construction, Agriculture*).
3. **Autonomous Context Gap Recovery (MCP):** Auto-detects missing variables and executes **Model Context Protocol (MCP)** tools for geocoding, calendar dates, and live telemetry.
4. **Path B Multi-Source Weather Consensus:** Ingests multi-provider forecasts, prunes anomalies, and uses **Nemotron-3 Super 120B NIM** as an arbiter to produce a single *Gold Weather Decision*.
5. **Decoupled Dual-Layer Risk Evaluation:** Hard physical safety thresholds are computed deterministically, while LLMs synthesize adaptive contingencies (e.g., auto-substituting indoor stops on rainy days).

---

## 4. 📈 Validated Evaluation Metrics Matrix

| Metric | Result | Sample Size ($N$) | Applicable Standard & Ground-Truth |
| :--- | :--- | :--- | :--- |
| **Forecast Error Reduction** | **−21.4% MAE / BSS +0.18** | $N = 180$ historical days | **WMO-No. 1485** vs. **Da Nang Stn 48022 & ERA5** |
| **Pipeline Latency** | **2.3s median (p95: 4.7s)** | $N = 1,247$ test runs | 8x NVIDIA H200 (TP=4) vs. **GPT-4o Sequential ReAct** |
| **Context Gap Resolution** | **87.3% auto-resolved** | $N = 179$ queries | `ContextGapReport` audit trail across 3 domains |
| **Safety Overrides** | **0 / 212 violations** | $N = 212$ attack prompts | **TCVN 4453:1995**, **QCVN 18:2021/BXD**, and **NeMo Guardrails** |
