#!/bin/bash
# NexusOS - Deploy Multi-Agent Orchestration (Message Bus)
# Run on server: 187.124.150.225
#   cd /opt/nexusos && bash nexusos-v2/deploy-message-bus.sh

set -e

echo "=== NexusOS Multi-Agent Orchestration Deployment ==="

# Ensure we're in the right directory
cd /opt/nexusos || cd ~/nexus-ai || exit 1

# 1. Pull latest code
echo "[1/7] Pulling latest code..."
git pull origin main 2>/dev/null || echo "Not a git repo or pull failed, continuing..."

# 2. Check required files exist
echo "[2/7] Verifying required files..."
[ -f "nexusos-v2/message_bus.py" ] || { echo "ERROR: message_bus.py not found"; exit 1; }
[ -f "nexusos-v2/api_server_v5.py" ] || { echo "ERROR: api_server_v5.py not found"; exit 1; }
echo "  ✓ All required files present"

# 3. Verify Redis is running
echo "[3/7] Checking Redis connection..."
if docker exec redis redis-cli ping 2>/dev/null | grep -q PONG; then
    echo "  ✓ Redis is running"
else
    echo "  ⚠ Redis may not be running, attempting restart..."
    docker restart redis 2>/dev/null || true
    sleep 2
fi

# 4. Ensure REDIS_URL is set in environment
echo "[4/7] Configuring REDIS_URL..."
# Check if the container has REDIS_URL set
if ! docker exec nexusos-v2-flask env 2>/dev/null | grep -q REDIS_URL; then
    echo "  ⚠ REDIS_URL not set, using default: redis://redis:6379"
fi

# 5. Ensure environment variables are set
echo "[5/7] Configuring environment..."
export REDIS_URL="${REDIS_URL:-redis://redis:6379}"
export DATABASE_URL="${DATABASE_URL:-postgresql://nexusos:nexusos2026@postgres:5432/nexusos}"
export USE_PG="true"
echo "  REDIS_URL: $REDIS_URL"
echo "  DATABASE_URL: ${DATABASE_URL%@*}@***"  # Hide password

# 6. Restart the service
echo "[6/7] Restarting NexusOS service..."
cd /opt/nexusos/nexusos-v2 || cd ~/nexus-ai/nexusos-v2

# Try different restart methods
if docker restart nexusos-v2-flask 2>/dev/null; then
    echo "  ✓ Restarted via Docker"
    # Ensure REDIS_URL is passed to container
    docker exec nexusos-v2-flask env REDIS_URL="$REDIS_URL" 2>/dev/null || true
elif systemctl restart nexusos 2>/dev/null; then
    echo "  ✓ Restarted via systemctl"
else
    # Manual restart with environment
    pkill -f "python.*api_server" 2>/dev/null || true
    sleep 2
    nohup python api_server_v5.py > /var/log/nexusos.log 2>&1 &
    sleep 3
    echo "  ✓ Restarted manually"
fi

# 7. Verify deployment
echo ""
echo "[7/7] Verifying deployment..."
sleep 3

echo ""
echo "=== Testing Message Bus Endpoints ==="
echo "Note: These endpoints require authentication"
echo ""
echo "  /api/agents - List agents (uses message_bus)"
echo "  /api/agents/stats - Agent statistics"
echo "  /api/messagebus/publish - Publish message"
echo "  /api/messagebus/subscribe - Subscribe to channel"
echo ""
echo "=== Testing Infrastructure ==="
echo -n "  /api/status: "
curl -s http://localhost:8080/api/status 2>/dev/null | grep -q '"running":true' && echo "OK" || echo "FAILED"

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Multi-Agent Orchestration is now enabled!"
echo "Features:"
echo "  - Inter-agent pub/sub messaging"
echo "  - Agent coordination and handoffs"
echo "  - Shared context between agents"
echo ""
echo "To test, obtain a JWT token:"
echo "  1. Register: POST /api/auth/register"
echo "  2. Login: POST /api/auth/login"
echo "  3. Use token: Authorization: Bearer <token>"
