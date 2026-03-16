# Quick Start

```bash
# One-line install (Linux/macOS)
curl -sL https://get.nexusos.cloud | bash

# Or clone and run manually
git clone https://github.com/your-repo/nexusos.git
cd nexusos/easy-install
./install.sh
```

## Requirements

- Docker 20.10+
- 2GB RAM minimum
- 10GB disk space

## What's Included

| Service | Port | Description |
|---------|------|-------------|
| API | 8080 | REST API + WebSocket |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache + Queue |
| Ollama | 11434 | Local LLM (optional) |

## First Steps

1. Open http://localhost:8080
2. Register your account
3. Create your first agent
4. Start chatting!

## Configuration

Edit `.env` to customize:

```bash
NEXUSOS_API_PORT=8080      # API port
NEXUSOS_DB_PASSWORD=...    # Database password
NEXUSOS_JWT_SECRET=...     # JWT signing key
OLLAMA_URL=http://ollama:11434  # LLM endpoint
```

## Commands

```bash
docker compose logs -f     # View logs
docker compose restart     # Restart services
docker compose down        # Stop everything
docker compose up -d       # Start in background
```

## Production Deployment

For production, add TLS and change defaults:

```bash
# Generate secure secrets
openssl rand -base64 32  # Use for NEXUSOS_SECRET
openssl rand -base64 32  # Use for NEXUSOS_JWT_SECRET

# Run behind nginx with TLS
# See docs/production.md for full guide
```

## Troubleshooting

**Database connection failed:**
```bash
docker compose logs postgres
```

**Reset everything:**
```bash
docker compose down -v   # WARNING: deletes all data
docker compose up -d
```

## Support

- Docs: https://docs.nexusos.cloud
- Issues: https://github.com/your-repo/nexusos/issues
