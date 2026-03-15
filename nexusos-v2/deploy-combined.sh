#!/bin/bash
# NexusOS - Deploy Usage Analytics + Webhooks (Combined)
# Run on server: 187.124.150.225
#   cd /opt/nexusos && bash nexusos-v2/deploy-combined.sh

set -e

echo "=== NexusOS Combined Deployment (Analytics + Webhooks) ==="

# Ensure we're in the right directory
cd /opt/nexusos || cd ~/nexus-ai || exit 1

# 1. Pull latest code
echo "[1/6] Pulling latest code..."
git pull origin main 2>/dev/null || echo "Not a git repo or pull failed, continuing..."

# 2. Check required files exist
echo "[2/6] Verifying required files..."
[ -f "nexusos-v2/usage_analytics.py" ] || { echo "ERROR: usage_analytics.py not found"; exit 1; }
[ -f "nexusos-v2/webhooks.py" ] || { echo "ERROR: webhooks.py not found"; exit 1; }
[ -f "nexusos-v2/api_server_v5.py" ] || { echo "ERROR: api_server_v5.py not found"; exit 1; }
echo "  ✓ All required files present"

# 3. Ensure database tables exist
echo "[3/6] Setting up database tables..."
DB_PATH="/opt/nexusos-data/nexusos.db"
[ -f "$DB_PATH" ] && sqlite3 "$DB_PATH" "CREATE TABLE IF NOT EXISTS usage_stats (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, model TEXT, provider TEXT, input_tokens INTEGER DEFAULT 0, output_tokens INTEGER DEFAULT 0, total_tokens INTEGER DEFAULT 0, requests INTEGER DEFAULT 0, cost_usd REAL DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP)" && echo "  ✓ usage_stats table ready"

[ -f "$DB_PATH" ] && sqlite3 "$DB_PATH" "CREATE TABLE IF NOT EXISTS webhooks (id TEXT PRIMARY KEY, user_id TEXT, event_type TEXT, url TEXT, secret TEXT, enabled INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP)" && echo "  ✓ webhooks table ready"

# 4. Ensure imports are in api_server_v5.py
echo "[4/6] Ensuring API imports..."
cd nexusos-v2

# Add usage_analytics if not present
if ! grep -q "from usage_analytics import" api_server_v5.py; then
    sed -i '/^from flask import/a from usage_analytics import usage_bp' api_server_v5.py
    sed -i '/^if __name__/i app.register_blueprint(usage_bp)' api_server_v5.py
    echo "  ✓ Added usage_analytics blueprint"
else
    echo "  ✓ usage_analytics already integrated"
fi

# Add webhooks if not present  
if ! grep -q "from webhooks import" api_server_v5.py; then
    sed -i '/^from flask import/a from webhooks import webhook_bp' api_server_v5.py
    sed -i '/^if __name__/i app.register_blueprint(webhook_bp)' api_server_v5.py
    echo "  ✓ Added webhooks blueprint"
else
    echo "  ✓ webhooks already integrated"
fi

# 5. Restart the service
echo "[5/6] Restarting NexusOS service..."
cd /opt/nexusos/nexusos-v2 || cd ~/nexus-ai/nexusos-v2

# Try different restart methods
if docker restart nexusos-v2-flask 2>/dev/null; then
    echo "  ✓ Restarted via Docker"
elif systemctl restart nexusos 2>/dev/null; then
    echo "  ✓ Restarted via systemctl"
else
    # Manual restart
    pkill -f "python.*api_server" 2>/dev/null || true
    sleep 2
    nohup python api_server_v5.py > /var/log/nexusos.log 2>&1 &
    sleep 3
    echo "  ✓ Restarted manually"
fi

# 6. Verify deployment
echo "[6/6] Verifying deployment..."
sleep 2

echo ""
echo "=== Testing Endpoints ==="
echo -n "  /api/usage: "
curl -s http://localhost:8080/api/usage 2>/dev/null | head -c 100 || echo "FAILED"

echo ""
echo -n "  /api/webhooks: "
curl -s http://localhost:8080/api/webhooks 2>/dev/null | head -c 100 || echo "FAILED (may need auth)"

echo ""
echo ""
echo "=== Deployment Complete ==="
echo "Run this on the server to deploy:"
echo "  cd /opt/nexusos && git pull origin main && bash nexusos-v2/deploy-combined.sh"
