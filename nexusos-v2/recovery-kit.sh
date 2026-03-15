#!/bin/bash
# NexusOS Production Recovery Kit
# Run on production server as: sudo bash recovery-kit.sh
# Created: 2026-03-15

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║        NEXUSOS PRODUCTION RECOVERY KIT                      ║"
echo "║        $(date '+%Y-%m-%d %H:%M:%S')                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ "$2" = "OK" ]; then
        echo -e "${GREEN}✓${NC} $1"
    elif [ "$2" = "WARN" ]; then
        echo -e "${YELLOW}⚠${NC} $1"
    elif [ "$2" = "FAIL" ]; then
        echo -e "${RED}✗${NC} $1"
    else
        echo "  $1"
    fi
}

echo "=== STEP 1: Checking Current Status ==="
echo ""

# Check if docker is available
if ! command -v docker &> /dev/null; then
    print_status "Docker not found" "FAIL"
    exit 1
fi
print_status "Docker available" "OK"

# Check docker-compose
if ! command -v docker compose &> /dev/null; then
    print_status "Docker Compose not found" "FAIL"
    exit 1
fi
print_status "Docker Compose available" "OK"

echo ""
echo "=== STEP 2: Checking Docker Containers ==="
echo ""

# List containers
docker ps -a --filter "name=nexusos" --filter "name=redis" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "=== STEP 3: Checking Redis ==="
echo ""

# Check if redis container exists
REDIS_CONTAINER=$(docker ps -a --filter "name=redis" --format "{{.Names}}" | head -1)

if [ -z "$REDIS_CONTAINER" ]; then
    print_status "Redis container does not exist!" "FAIL"
    echo ""
    echo "Starting Redis..."
    docker compose -f /root/nexusos-v2/docker-compose.yml up -d redis
    sleep 3
else
    print_status "Redis container: $REDIS_CONTAINER" "INFO"
    
    # Check if running
    if docker ps --filter "name=redis" --format "{{.Names}}" | grep -q "redis"; then
        print_status "Redis is RUNNING" "OK"
        
        # Test Redis connectivity
        if docker exec redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
            print_status "Redis responds to PING" "OK"
        else
            print_status "Redis not responding - restarting..." "WARN"
            docker restart redis
            sleep 2
        fi
    else
        print_status "Redis container exists but NOT RUNNING" "WARN"
        echo ""
        echo "Starting Redis..."
        docker start redis
        sleep 3
    fi
fi

echo ""
echo "=== STEP 4: Checking PostgreSQL ==="
echo ""

# Check PostgreSQL
if docker ps --filter "name=postgres" --format "{{.Names}}" | grep -q "postgres"; then
    print_status "PostgreSQL is RUNNING" "OK"
else
    print_status "PostgreSQL may not be running" "WARN"
fi

echo ""
echo "=== STEP 5: Checking API Server ==="
echo ""

# Check API
if docker ps --filter "name=nexusos-api" --format "{{.Names}}" | grep -q "nexusos"; then
    print_status "NexusOS API container is RUNNING" "OK"
    
    # Test API
    if curl -s http://localhost:8080/api/status > /dev/null 2>&1; then
        print_status "API responds to /api/status" "OK"
        
        # Get full status
        echo ""
        echo "=== API Status ==="
        curl -s http://localhost:8080/api/status | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8080/api/status
    else
        print_status "API not responding - may need restart" "WARN"
    fi
else
    print_status "NexusOS API container not found" "WARN"
fi

echo ""
echo "=== STEP 6: Fixing Redis Connection ==="
echo ""

# Ensure Redis is accessible
if docker ps --filter "name=redis" --format "{{.Names}}" | grep -q "redis"; then
    # Restart API to pick up Redis
    print_status "Restarting API to connect to Redis..." "INFO"
    docker restart nexusos-api 2>/dev/null || echo "Could not restart API (may not be in docker-compose)"
    sleep 3
fi

echo ""
echo "=== FINAL STATUS ==="
echo ""

# Final check
echo "Component Status:"
curl -s http://localhost:8080/api/status 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f\"  API Server: {'OK' if data.get('running') else 'FAIL'}\")
print(f\"  PostgreSQL: {'OK' if data.get('components',{}).get('postgresql') else 'FAIL'}\")
print(f\"  Redis: {'OK' if data.get('components',{}).get('redis') else 'FAIL'}\")
print(f\"  LLM Manager: {'OK' if data.get('components',{}).get('llm_manager') else 'FAIL'}\")
" 2>/dev/null || echo "  (Could not get final status)"

echo ""
echo "=== QUICK FIX COMMANDS (if needed) ==="
echo ""
echo "# Full Redis fix:"
echo "  docker compose -f /root/nexusos-v2/docker-compose.yml restart redis"
echo "  docker restart nexusos-api"
echo ""
echo "# Check logs:"
echo "  docker logs redis"
echo "  docker logs nexusos-api"
echo ""
echo "=== DONE ==="
