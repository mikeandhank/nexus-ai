#!/bin/bash
# NexusOS - Deploy Usage Analytics Module
# Run this on the server: 187.124.150.225

set -e

echo "=== NexusOS Usage Analytics Deployment ==="

# 1. Pull latest code
cd /opt/nexusos || cd ~/nexus-ai
git pull origin main

# 2. Check if usage_analytics.py exists
if [ ! -f "nexusos-v2/usage_analytics.py" ]; then
    echo "ERROR: usage_analytics.py not found"
    exit 1
fi

# 3. Add the route to api_server_v5.py
# The simplest way: import and register the blueprint
if ! grep -q "usage_analytics" nexusos-v2/api_server_v5.py; then
    echo "Adding usage_analytics import to api_server_v5.py..."
    
    # Add import after other imports
    sed -i '/^from flask import send_from_directory/a\
from usage_analytics import usage_bp' nexusos-v2/api_server_v5.py
    
    # Add registration before if __name__ == '__main__'
    sed -i '/^if __name__/i app.register_blueprint(usage_bp)' nexusos-v2/api_server_v5.py
fi

# 4. Ensure usage_stats table exists (it should in current DB)
echo "Verifying usage_stats table..."
sqlite3 /opt/nexusos-data/nexusos.db "CREATE TABLE IF NOT EXISTS usage_stats (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, model TEXT, provider TEXT, input_tokens INTEGER DEFAULT 0, output_tokens INTEGER DEFAULT 0, total_tokens INTEGER DEFAULT 0, requests INTEGER DEFAULT 0, cost_usd REAL DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP)"

# 5. Restart the service
echo "Restarting NexusOS..."
docker restart nexusos-v2-flask 2>/dev/null || systemctl restart nexusos 2>/dev/null || pkill -f "python.*api_server" && sleep 2 && cd /opt/nexusos/nexusos-v2 && python api_server_v5.py &

# 6. Verify
sleep 3
echo ""
echo "=== Testing /api/usage endpoint ==="
curl -s http://localhost:8080/api/usage 2>/dev/null | head -c 200 || echo "Endpoint not responding yet"

echo ""
echo "=== Deployment Complete ==="
