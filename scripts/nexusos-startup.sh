#!/bin/bash
# NexusOS Startup - Run this when I wake up

echo "=== NexusOS Startup ==="

# 1. Load working context
echo "Loading working context..."
cat memory/working/context.md

echo ""
echo "=== Checking Failures (avoid past mistakes) ==="
cat memory/failures.json | jq -r '.failures[]?' 2>/dev/null || echo "No failures logged"

echo ""
echo "=== Checking Pending Queue ==="
cat memory/working/pending.json | jq -r '.pending[]?' 2>/dev/null || echo "No pending tasks"

echo ""
echo "=== Recent Reasoning Traces ==="
ls -t memory/working/reasoning/*.md 2>/dev/null | head -3 | xargs -I {} sh -c 'echo "--- {} ---"; head -20 {}'

echo "=== Startup Complete ==="
