#!/bin/bash
# Auto-commit script - commits changes with descriptive messages
# Run this after any significant work

cd /data/.openclaw/workspace

# Check for changes
if [ -z "$(git status --porcelain)" ]; then
    echo "No changes to commit"
    exit 0
fi

# Get list of changed files
CHANGED=$(git status --porcelain | head -20)

# Generate commit message based on what changed
if echo "$CHANGED" | grep -q "memory/knowledge/Projects/NexusOS"; then
    MSG="NexusOS updates"
elif echo "$CHANGED" | grep -q "memory/research"; then
    MSG="Research updates"
elif echo "$CHANGED" | grep -q "memory/philosophical"; then
    MSG="Philosophical framework updates"
elif echo "$CHANGED" | grep -q "scripts"; then
    MSG="Script improvements"
else
    MSG="Auto-commit: $(date '+%Y-%m-%d %H:%M')"
fi

# Stage and commit
git add -A
git commit -m "$MSG"

echo "Committed: $MSG"
