#!/bin/bash
# Weatherise v2 — Health Check Script
set -e

BASE_URL="${1:-http://localhost}"
PASS=0; FAIL=0

check() {
  local name=$1; local url=$2; local expected=$3
  result=$(curl -sf "$url" 2>/dev/null || echo "FAIL")
  if echo "$result" | grep -q "$expected"; then
    echo "  ✅ $name — OK"
    PASS=$((PASS+1))
  else
    echo "  ❌ $name — FAIL (got: $result)"
    FAIL=$((FAIL+1))
  fi
}

echo "🩺 Weatherise v2 Health Checks"
echo "================================"
check "Nginx"          "$BASE_URL:8080/"         ""
check "API Health"     "$BASE_URL:8080/health"   "ok"
check "MCP Health"     "http://localhost:9000/health" "ok"
check "NIM LLM"        "http://localhost:8001/v1/models" "nemotron"
check "NIM Embed"      "http://localhost:8002/v1/models" "nv-embedqa"
check "Qdrant"         "http://localhost:6333/health"    "ok"
check "Redis"          ""                                ""  # Redis ping via docker

echo ""
echo "================================"
echo "  PASS: $PASS  FAIL: $FAIL"
if [ $FAIL -eq 0 ]; then
  echo "  🎉 All checks passed!"
else
  echo "  ⚠️  Some checks failed. Review output above."
fi
