# NexusOS

Persistent memory for AI agents.

## What is this?

Your AI agent forgets everything between conversations. NexusOS gives it memory that survives restarts.

**Core features:**
- Three-tier memory (working, episodic, semantic)
- MCP tool servers (filesystem, HTTP, process)
- LanceDB for vector storage
- Docker one-command deploy

## Why NexusOS?

| Problem | NexusOS Solution |
|---------|-----------------|
| Agent forgets between sessions | Persistent episodic memory survives restarts |
| Context window saturation | Semantic memory gives structured access to knowledge |
| No persistence | SQLite + LanceDB for durable storage |
| Hard to scale | Docker-compose, MCP protocol |

**The pain:** 95% of enterprise AI pilots stall due to memory issues. Your agent works great for 30 minutes, then forgets everything.

**The fix:** NexusOS adds three-tier memory that persists across sessions.

## Quick Start (5 minutes)

### 1. Clone and go
```bash
git clone https://github.com/your-repo/NexusOS.git
cd NexusOS
```

### 2. Create .env file
```bash
cp .env.example .env
# Edit .env and add your API keys
```

### 3. Start it
```bash
docker compose up -d
```

### 4. Verify it's running
```bash
curl http://localhost:4893/health
# Should return: {"status":"healthy",...}
```

## Connect Your Agent

### OpenClaw
Add to your config:
```json
{
  "memory": {
    "url": "http://localhost:4893"
  }
}
```

### Claude Code / Other
Send HTTP requests to memory endpoints:

```bash
# Start a session
curl -X POST http://localhost:4893/memory/working/start \
  -H "Content-Type: application/json" \
  -d '{"sessionId":"my-session"}'

# Add a message
curl -X POST http://localhost:4893/memory/working/message \
  -H "Content-Type: application/json" \
  -d '{"content":"Remember this","role":"user"}'

# End session (saves to persistent memory)
curl -X POST http://localhost:4893/memory/working/end

# Later: query persistent memory
curl -X POST http://localhost:4893/memory/episodic/search \
  -H "Content-Type: application/json" \
  -d '{"query":"remember","limit":5}'
```

## API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Health check |
| `POST /memory/working/start` | Start session |
| `POST /memory/working/message` | Add message |
| `POST /memory/working/end` | End session (persist) |
| `POST /memory/episodic/search` | Query memory |
| `GET /memory/episodic/recent` | Recent memories |

## Troubleshooting

**Nothing running?**
```bash
docker compose logs
```

**Port conflict?**
Edit docker-compose.yml to change ports

**Need to restart?**
```bash
docker compose restart
```

## Requirements

- Docker
- 2GB RAM minimum
- For local LLM: 8GB+ RAM (optional)

---

**Got questions?** Open an issue. This is v0.1 — we expect friction.

_Last updated: 2026-03-13_
