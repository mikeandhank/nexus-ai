#!/bin/bash
# Log a failure to NexusOS failure memory
# Usage: ./scripts/nexusos-log-failure.sh "operation" "what failed" "why it failed" "how to avoid"

OPERATION="$1"
WHAT="$2"
WHY="$3"
HOW="$4"

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Read existing failures
if [ -f memory/failures.json ]; then
    # Use temp file for atomic write
    jq --arg ts "$TIMESTAMP" \
       --arg op "$OPERATION" \
       --arg what "$WHAT" \
       --arg why "$WHY" \
       --arg how "$HOW" \
       '.failures += [{
           timestamp: $ts,
           operation: $op,
           what: $what,
           why: $why,
           how_to_avoid: $how
       }] | .lastUpdated = $ts' \
       memory/failures.json > /tmp/failures-temp.json && \
       mv /tmp/failures-temp.json memory/failures.json
    echo "Logged failure: $OPERATION"
else
    echo "ERROR: failures.json not found"
    exit 1
fi
