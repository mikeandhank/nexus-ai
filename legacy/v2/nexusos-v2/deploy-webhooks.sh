#!/bin/bash
# NexusOS - Deploy Webhook System
# Run this on the server: 187.124.150.225

set -e

echo "=== NexusOS Webhook System Deployment ==="

# 1. Pull latest code
cd /opt/nexusos || cd ~/nexus-ai
git pull origin main

# 2. Check if webhooks.py exists
if [ ! -f "nexusos-v2/webhooks.py" ]; then
    echo "ERROR: webhooks.py not found"
    exit 1
fi

# 3. Add webhook routes to api_server_v5.py
if ! grep -q "from webhooks import" nexusos-v2/api_server_v5.py; then
    echo "Adding webhooks import to api_server_v5.py..."
    
    # Add import after other imports
    sed -i '/^from flask import send_from_directory/a\
from webhooks import webhook_bp' nexusos-v2/api_server_v5.py
    
    # Add registration before if __name__ == '__main__'
    sed -i '/^if __name__/i app.register_blueprint(webhook_bp)' nexusos-v2/api_server_v5.py
fi

# 4. Ensure webhooks table exists
echo "Verifying webhooks table..."
sqlite3 /opt/nexusos-data/nexusos.db "CREATE TABLE IF NOT EXISTS webhooks (id TEXT PRIMARY KEY, user_id TEXT, event_type TEXT, url TEXT, secret TEXT, enabled INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP)"

# 5. Restart the service
echo "Restarting NexusOS..."
docker restart nexusos-v2-flask 2>/dev/null || systemctl restart nexusos 2>/dev/null || pkill -f "python.*api_server" && sleep 2 && cd /opt/nexusos/nexusos-v2 && python api_server_v5.py &

# 6. Verify
sleep 3
echo ""
echo "=== Testing webhook endpoints ==="
echo "Available endpoints:"
echo "  POST /api/webhooks/register - Register a webhook"
echo "  GET  /api/webhooks - List webhooks"
echo "  DELETE /api/webhooks/<id> - Remove a webhook"
echo "  POST /api/webhooks/test - Test webhook delivery"

echo ""
echo "=== Deployment Complete ==="