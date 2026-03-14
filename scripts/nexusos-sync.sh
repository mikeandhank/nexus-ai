#!/bin/bash
# NexusOS Sync Script
# Syncs OpenClaw workspace memory to NexusOS memory server

NEXUS_URL="${NEXUS_URL:-http://localhost:4893}"
WORKSPACE="${WORKSPACE:-/data/.openclaw/workspace}"
MEMORY_DIR="$WORKSPACE/memory"

# Check if memory server is running
if ! curl -s "$NEXUS_URL/health" > /dev/null 2>&1; then
  echo "ERROR: NexusOS memory server not running at $NEXUS_URL"
  exit 1
fi

# Get today's memory file - check multiple possible locations
MEMORY_FILE="$MEMORY_DIR/$(date +%Y-%m-%d).md"
if [ ! -f "$MEMORY_FILE" ]; then
  MEMORY_FILE="$MEMORY_DIR/archive/$(date +%Y-%m-%d).md"
fi
if [ ! -f "$MEMORY_FILE" ]; then
  MEMORY_FILE="$MEMORY_DIR/daily-reflections/$(date +%Y-%m-%d).md"
fi
SESSION_ID="openclaw-$(date +%Y%m%d-%H%M%S)"

if [ -f "$MEMORY_FILE" ]; then
  echo "Syncing $MEMORY_FILE to NexusOS..."
  
  # Start session
  curl -s -X POST "$NEXUS_URL/memory/working/start" \
    -H "Content-Type: application/json" \
    -d "{\"sessionId\":\"$SESSION_ID\"}" > /dev/null
  
  # Read and send each line as a message (simplified)
  while IFS= read -r line; do
    if [ -n "$line" ] && [ "${line:0:1}" != "#" ]; then
      curl -s -X POST "$NEXUS_URL/memory/working/message" \
        -H "Content-Type: application/json" \
        -d "{\"content\":\"$line\",\"role\":\"user\"}" > /dev/null
    fi
  done < "$MEMORY_FILE"
  
  # End session (persist to episodic)
  curl -s -X POST "$NEXUS_URL/memory/working/end" \
    -H "Content-Type: application/json" \
    -d "{}" > /dev/null
  
  echo "Synced to NexusOS session: $SESSION_ID"
else
  echo "No memory file found: $MEMORY_FILE"
fi

# Query recent memories
echo "Recent NexusOS memories:"
curl -s "$NEXUS_URL/memory/episodic/recent?limit=3" | jq -r '.episodes[]?.content // "none"' 2>/dev/null | head -5
