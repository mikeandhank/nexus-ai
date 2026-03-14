#!/bin/bash
# NexusOS Memory Server Launcher
# Keeps the memory server running with auto-restart

PORT="${PORT:-4893}"
NEXUS_DIR="/data/.openclaw/workspace/memory/knowledge/Projects/NexusOS"
LOG_FILE="/tmp/nexusos-memory.log"

start_server() {
    cd "$NEXUS_DIR"
    mkdir -p memory/episodic memory/semantic
    
    nohup node -e "
        process.env.PORT = '$PORT';
        process.env.LANCEDB_PATH = './memory/episodic';
        process.env.SQLITE_PATH = './memory/semantic/nexusos.db';
        require('./tools/memory-server.js');
    " > "$LOG_FILE" 2>&1 &
    
    echo "$(date): NexusOS started" >> "$LOG_FILE"
}

check_server() {
    if curl -s --max-time 2 "http://localhost:$PORT/health" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Check if server is running
if check_server; then
    echo "NexusOS already running on port $PORT"
else
    echo "Starting NexusOS..."
    start_server
    sleep 3
    if check_server; then
        echo "NexusOS started successfully"
    else
        echo "Failed to start. Check $LOG_FILE"
        tail -20 "$LOG_FILE"
    fi
fi