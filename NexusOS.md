# NexusOS - Agent Operating System
# Improvements: Memory (auto-capture, vector search, persistence) + Autonomy (decision rights, exception handling, proactive)

## Memory Layer

### Current Gaps
- Manual writes only - I forget if I don't explicitly write
- No semantic search - keyword grep only
- No auto-tagging of important context
- Session loss on restart

### Improvements (v1)
- Working memory survives restarts (stored in memory/working/)
- Auto-capture: important decisions, preferences, context changes
- Semantic search ready (embeddings when vector DB available)
- Memory consolidation: working → episodic → semantic

### Memory Tiers
```
memory/
  working/     # Current session context, high priority
  episodic/    # Session logs, events, decisions
  semantic/    # Consolidated knowledge, patterns
```

---

## Autonomy Layer

### Decision Rights (what I can do without asking)
```
✅ CAN DO WITHOUT ASKING:
- Write to memory files
- Search the web for info
- Read files in workspace
- Commit/push to git (non-destructive)
- Run non-destructive exec commands
- Send heartbeat checks

❌ MUST ASK FIRST:
- Send messages to external people/channels
- Spend money / make purchases
- Delete files
- Destructive commands (rm, drop tables)
- Access outside workspace
- Anything involving secrets/credentials
```

### Exception Handling
- Retry failed operations (2x) with exponential backoff
- Graceful degradation: if primary tool fails, try backup
- Never fail silently: report errors with context
- Timeout handling: max 60s per operation

### Proactive Triggers (run without asking)
- Heartbeat checks (as defined in HEARTBEAT.md)
- Background task completion notifications
- Important memory consolidation events

---

## Integration Points

### OpenClaw Hooks
- on_session_start: Load working memory
- on_session_end: Save working memory
- on_message: Auto-tag important context

### Tool Expansion (MCP-ready)
- filesystem: enhanced file ops
- process: background tasks
- http: API calls
- memory: vector search (future)

---

_Last updated: 2026-03-14_
