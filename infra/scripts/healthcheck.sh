#!/bin/bash
# Weatherise V3 — Health Check Script
set -e

BASE_URL="${1:-http://localhost}"
PASS=0; FAIL=0; WARN=0

check() {
  local name=$1; local url=$2; local expected=$3
  result=$(curl -sf --max-time 5 "$url" 2>/dev/null || echo "FAIL")
  if echo "$result" | grep -q "$expected"; then
    echo "  ✅ $name — OK"
    PASS=$((PASS+1))
  else
    echo "  ❌ $name — FAIL (got: $result)"
    FAIL=$((FAIL+1))
  fi
}

check_qdrant_kb() {
  result=$(curl -sf --max-time 5 "http://localhost:6333/collections/tourism_knowledge" 2>/dev/null || echo "FAIL")
  if echo "$result" | grep -q "points_count"; then
    count=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('result',{}).get('points_count','?'))" 2>/dev/null || echo "?")
    if [ "$count" = "0" ] || [ "$count" = "?" ]; then
      echo "  ⚠️  Qdrant KB — NOT SEEDED (run: python3 knowledge/scripts/seed_qdrant.py)"
      WARN=$((WARN+1))
    else
      echo "  ✅ Qdrant KB tourism_knowledge — OK ($count vectors)"
      PASS=$((PASS+1))
    fi
  elif echo "$result" | grep -q "404\|Not Found"; then
    echo "  ⚠️  Qdrant KB — COLLECTION MISSING (run: python3 knowledge/scripts/seed_qdrant.py)"
    WARN=$((WARN+1))
  else
    echo "  ❌ Qdrant KB — UNREACHABLE"
    FAIL=$((FAIL+1))
  fi
}

echo "🩺 Weatherise V3 Health Checks"
echo "================================"
check "Nginx"          "$BASE_URL:8080/"                   ""
check "API Health"     "$BASE_URL:8080/health"             "ok"
check "MCP Health"     "http://localhost:9000/health"      "ok"
check "NIM LLM"        "http://localhost:8001/v1/models"   "nemotron"
check "NIM Embed"      "http://localhost:8002/v1/models"   "nv-embedqa"
check "Qdrant Cluster" "http://localhost:6333/readyz"      "all shards are ready"
check_qdrant_kb

echo ""
echo "================================"
echo "  PASS: $PASS  WARN: $WARN  FAIL: $FAIL"
if [ $FAIL -eq 0 ] && [ $WARN -eq 0 ]; then
  echo "  🎉 All checks passed!"
elif [ $FAIL -eq 0 ]; then
  echo "  ⚠️  Healthy with warnings. Review above."
  exit 0
else
  echo "  🚨 Some checks FAILED. Review output above."
  exit 1
fi

set -e

BASE_URL="${1:-http://localhost}"
