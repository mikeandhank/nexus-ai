#!/bin/bash
# Create a reasoning trace
# Usage: ./scripts/nexusos-reason.sh "task" "option1" "option2" "option3" "decision"

TASK="$1"
OPTA="$2"
OPTB="$3"
OPTC="$4"
DECISION="$5"
PERSIST="${6:-yes}"

TIMESTAMP=$(date -u +%Y-%m-%dT%H%M%S)
FILENAME="memory/working/reasoning/${TIMESTAMP}.md"

cat > "$FILENAME" << EOF
# Reasoning Trace - $TIMESTAMP

## Task
$TASK

## Options Considered
- $OPTA
- $OPTB
$([ -n "$OPTC" ] && echo "- $OPTC")

## Reasoning
[TODO: Fill in my thought process]

## Decision
$DECISION

## Will Persist?
- [ ] Yes - if this reasoning applies to future situations
- [ ] No - too specific to this moment

## Tags
[TODO: keywords for retrieval]
EOF

echo "Created reasoning trace: $FILENAME"
