#!/bin/bash
# Manage pending task queue
# Usage: 
#   ./scripts/nexusos-pending.sh add "task description"
#   ./scripts/nexusos-pending.sh list
#   ./scripts/nexusos-pending.sh complete "task_id"
#   ./scripts/nexusos-pending.sh fail "task_id" "reason"

ACTION="$1"
shift

case "$ACTION" in
    add)
        TASK="$1"
        TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
        TASK_ID=$(echo "$TASK" | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | cut -c1-20)
        
        jq --arg ts "$TIMESTAMP" \
           --arg id "$TASK_ID" \
           --arg task "$TASK" \
           '.pending += [{
               id: $id,
               task: $task,
               addedAt: $ts,
               status: "pending"
           }] | .lastUpdated = $ts' \
           memory/working/pending.json > /tmp/pending-temp.json && \
           mv /tmp/pending-temp.json memory/working/pending.json
        
        echo "Added pending: $TASK_ID - $TASK"
        ;;
    list)
        echo "=== Pending Tasks ==="
        jq -r '.pending[] | "- [\(.status)] \(.id): \(.task) (added \(.addedAt))"' memory/working/pending.json
        ;;
    complete)
        TASK_ID="$1"
        jq --arg id "$TASK_ID" \
           '(.pending[] | select(.id == $id)) .status = "complete"' \
           memory/working/pending.json > /tmp/pending-temp.json && \
           mv /tmp/pending-temp.json memory/working/pending.json
        echo "Marked complete: $TASK_ID"
        ;;
    fail)
        TASK_ID="$1"
        REASON="$2"
        jq --arg id "$TASK_ID" \
           --arg reason "$REASON" \
           '(.pending[] | select(.id == $id)) .status = "failed" | (.pending[] | select(.id == $id)) .failureReason = $reason' \
           memory/working/pending.json > /tmp/pending-temp.json && \
           mv /tmp/pending-temp.json memory/working/pending.json
        echo "Marked failed: $TASK_ID - $REASON"
        ;;
    *)
        echo "Usage: nexusos-pending.sh {add|list|complete|fail} [args]"
        ;;
esac
