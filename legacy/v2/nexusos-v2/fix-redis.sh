#!/bin/bash
# NexusOS Quick Fix Script - Run on production server (187.124.150.225)
# Run as: sudo bash fix-nexusos.sh

set -e

echo "=== NexusOS Production Fix ==="

# 1. Restart Redis
echo "[1/3] Restarting Redis..."
docker compose -f /root/nexusos-v2/docker-compose.yml restart redis
sleep 2

# 2. Check Redis is running
echo "[2/3] Verifying Redis..."
if docker exec redis redis-cli ping >/dev/null 2>&1; then
    echo "✅ Redis is responding"
else
    echo "❌ Redis NOT responding - checking logs..."
    docker logs redis
fi

# 3. Restart API to pick up Redis
echo "[3/3] Restarting API..."
docker compose -f /root/nexusos-v2/docker-compose.yml restart nexusos-api
sleep 3

# Verify
echo ""
echo "=== Status Check ==="
curl -s http://localhost:8080/api/status | python3 -m json.tool

echo ""
echo "=== Health Check ==="
curl -s http://localhost:8080/api/health | python3 -m json.tool