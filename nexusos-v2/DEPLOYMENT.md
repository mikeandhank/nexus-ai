# NexusOS PostgreSQL Deployment Guide

## What Was Changed

### Phase 1 Foundation - PostgreSQL Support

1. **database_compat.py** - NEW
   - Compatibility layer wrapping PostgreSQL (database_v2) with the old SQLite API
   - Allows api_server_v5.py to work with PostgreSQL without major refactoring
   - Provides: create_user, get_user, verify_password, create_conversation, add_message, track_usage, etc.

2. **api_server_v5.py** - UPDATED
   - Changed import from `database` (SQLite) to `database_compat` (PostgreSQL)

3. **auth.py** - UPDATED
   - Changed imports to use database_compat for consistency

## Deployment Steps

When server 187.124.150.225 is back online:

```bash
# 1. Stop existing container
docker stop nexusos-v2-flask || true
docker rm nexusos-v2-flask || true

# 2. Start fresh with docker-compose (includes PostgreSQL + Redis)
docker-compose -f nexusos-v2/docker-compose.yml up -d

# 3. Check logs
docker-compose -f nexusos-v2/docker-compose.yml logs -f
```

## Expected Services

- PostgreSQL: postgresql://nexusos:nexusos@postgres:5432/nexusos
- Redis: redis://redis:6379/0
- NexusOS API: http://localhost:8080
- Ollama: http://localhost:11435

## Verification

```bash
# Check API status
curl http://187.124.150.225:8080/api/status

# Register a test user
curl -X POST http://187.124.150.225:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","name":"Test User"}'
```

## Phase 1 Completion Checklist

- [x] PostgreSQL database layer (database_v2.py + database_compat.py)
- [x] JWT Auth with refresh tokens (auth.py)
- [x] Webhook System (webhooks.py + webhooks table added)
- [ ] Redis for shared state (docker-compose has it, need to integrate)
- [ ] Connection pooling and health checks

_Last updated: 2026-03-15_