#!/bin/bash
# ==============================================================================
# Script: healthcheck.sh
# Objective: Optimized multi-socket verification check for Weatherise cluster
# Core Path: /raid/team/test/weatherise/scripts/healthcheck.sh
# ==============================================================================

# Terminal ANSI Color Escape Codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Service Configurations
REDIS_CONTAINER="redis"
API_URL="http://localhost:8008/health"
LLM_URL="http://localhost:8001/v1/models"
EMBED_URL="http://localhost:8002/v1/models"
RERANK_URL="http://localhost:8003/v1/models"
CUOPT_URL="http://localhost:8083/health"
MILVUS_URL="http://localhost:9091/healthz"
POSTGRES_CONTAINER="postgres"

echo -e "${BLUE}${BOLD}==================================================${NC}"
echo -e "${BLUE}${BOLD}      WEATHERISE INFRASTRUCTURE DIAGNOSTICS       ${NC}"
echo -e "${BLUE}${BOLD}==================================================${NC}"

# Helper function to print standardized evaluation columns
print_status() {
    local service_name="$1"
    local status="$2"
    local message="$3"
    
    if [ "$status" = "OK" ]; then
        printf "${BOLD}%-25s${NC} [ ${GREEN}✅ ACTIVE${NC} ] %s\n" "$service_name" "$message"
    elif [ "$status" = "WARN" ]; then
        printf "${BOLD}%-25s${NC} [ ${YELLOW}⚠️  WARN${NC}   ] %s\n" "$service_name" "$message"
    else
        printf "${BOLD}%-25s${NC} [ ${RED}❌ DOWN${NC}   ] %s\n" "$service_name" "$message"
    fi
}

# --- 1. CORE APPLICATION LAYER ---
echo -e "\n${BOLD}--- CORE APPLICATION LAYER ---${NC}"

# Redis Core Evaluation
if ! docker ps -q -f name=^/${REDIS_CONTAINER}$ > /dev/null; then
    print_status "Redis Engine (6379)" "FAIL" "Container instance dead or stopped."
else
    REDIS_PING=$(docker exec "$REDIS_CONTAINER" redis-cli ping 2>/dev/null | tr -d '\r\n')
    if [ "$REDIS_PING" = "PONG" ]; then
        print_status "Redis Engine (6379)" "OK" "Handshake connection successful."
    else
        print_status "Redis Engine (6379)" "FAIL" "Invalid database response: ${REDIS_PING}"
    fi
fi

# FastAPI Gateway Evaluation
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL" --connect-timeout 3 || echo "000")
if [ "$HTTP_STATUS" = "200" ]; then
    HEALTH_PAYLOAD=$(curl -s "$API_URL")
    print_status "FastAPI Core (8008)" "OK" "HTTP 200 - ${HEALTH_PAYLOAD}"
elif [ "$HTTP_STATUS" = "000" ]; then
    print_status "FastAPI Core (8008)" "FAIL" "Socket connection refused / uvicorn process inactive."
else
    print_status "FastAPI Core (8008)" "FAIL" "HTTP Status Exception: ${HTTP_STATUS}"
fi

# --- 2. NVIDIA NIM & INFRASTRUCTURE INTERFACES ---
echo -e "\n${BOLD}--- NVIDIA NIM & ACCELERATION RUNTIMES ---${NC}"

# LLM NIM Model Check
LLM_ID=$(curl -s --connect-timeout 3 "$LLM_URL" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data'][0]['id'])" 2>/dev/null || echo "FAIL")
if [ "$LLM_ID" != "FAIL" ]; then
    print_status "LLM NIM (8001)" "OK" "Model registered: ${LLM_ID}"
else
    print_status "LLM NIM (8001)" "FAIL" "Service context unavailable."
fi

# Embedding NIM Model Check
EMBED_ID=$(curl -s --connect-timeout 3 "$EMBED_URL" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data'][0]['id'])" 2>/dev/null || echo "FAIL")
if [ "$EMBED_ID" != "FAIL" ]; then
    print_status "Embed NIM (8002)" "OK" "Model registered: ${EMBED_ID}"
else
    print_status "Embed NIM (8002)" "FAIL" "Service context unavailable."
fi

# Reranker NIM Model Check
RERANK_ID=$(curl -s --connect-timeout 3 "$RERANK_URL" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data'][0]['id'])" 2>/dev/null || echo "FAIL")
if [ "$RERANK_ID" != "FAIL" ]; then
    print_status "Rerank NIM (8003)" "OK" "Model registered: ${RERANK_ID}"
else
    print_status "Rerank NIM (8003)" "FAIL" "Service context unavailable."
fi

# cuOpt Decision Optimizer Engine
if curl -s --connect-timeout 2 "$CUOPT_URL" > /dev/null; then
    print_status "cuOpt Core (8083)" "OK" "Optimization server responding."
else
    print_status "cuOpt Core (8083)" "FAIL" "Routing kernel connection failed."
fi

# --- 3. STORAGE & DATA BACKBONE ---
echo -e "\n${BOLD}--- KNOWLEDGE & PERSISTENCE TIER ---${NC}"

# Milvus Standalone Cluster Storage Interface
if curl -s --connect-timeout 2 "$MILVUS_URL" > /dev/null; then
    print_status "Milvus Vector (19530)" "OK" "Metadata storage cluster stable."
else
    print_status "Milvus Vector (19530)" "FAIL" "Vector abstraction channel unreachable."
fi

# PostgreSQL Transaction Store
if ! docker ps -q -f name=^/${POSTGRES_CONTAINER}$ > /dev/null; then
    print_status "PostgreSQL (5432)" "FAIL" "Container instance dead or stopped."
else
    if docker exec "$POSTGRES_CONTAINER" pg_isready -q 2>/dev/null; then
        print_status "PostgreSQL (5432)" "OK" "Accepting active service write queries."
    else
        print_status "PostgreSQL (5432)" "FAIL" "Database engine rejecting connections."
    fi
fi

# --- 4. BARE-METAL TELEMETRY METRICS ---
echo -e "\n${BOLD}--- HARDWARE TELEMETRY METRICS ---${NC}"
if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${RED}[ERROR] NVIDIA driver subsystem detached / command unresolvable.${NC}"
else
    nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv,noheader,nounits | while IFS=, read idx name used total; do
        pct=$((used * 100 / total))
        
        # Color code threshold allocations
        if [ "$pct" -gt 85 ]; then
            COLOR_ATTR="${RED}"
        elif [ "$pct" -gt 50 ]; then
            COLOR_ATTR="${YELLOW}"
        else
            COLOR_ATTR="${GREEN}"
        fi
        
        echo -e "$(echo "$name" | sed 's/^ //')" "$used"MiB/"$total"MiB "($pct%)"
    done | awk -F'|' '{printf "  %-45s | %s\n", $1, $2}'
fi

echo -e "\n${BLUE}${BOLD}==================================================${NC}"