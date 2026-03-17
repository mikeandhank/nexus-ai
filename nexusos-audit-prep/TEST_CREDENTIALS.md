# Test Credentials

## ⚠️ SECURITY WARNING
These credentials are for **testing purposes only**. Do not use in production.

---

## Test Accounts

| Email | Password | Role | Purpose |
|-------|----------|------|---------|
| `audit@nexusos.test` | `AuditTest123!` | developer | API testing |
| `admin@nexusos.test` | `AdminTest123!` | admin | Full access |
| `viewer@nexusos.test` | `ViewerTest123!` | viewer | Read-only testing |

## Server Access

| Service | URL | Credentials |
|---------|-----|-------------|
| API | https://nexusos.cloud/api | Use test accounts above |
| Web UI | https://nexusos.cloud/ui | Use test accounts above |
| MCP | https://nexusos.cloud/mcp/tools | Requires JWT |

## Database Access

**DO NOT SHARE - Internal Only**

```bash
# SSH to server
ssh root@187.124.150.225

# Connect to PostgreSQL
docker exec -it nexusos-postgres psql -U nexusos -d nexusos

# Connect to Redis
docker exec -it nexusos-redis redis-cli
```

## API Testing Examples

### Register new test user
```bash
curl -X POST https://nexusos.cloud/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@test.com",
    "password": "Test123",
    "name": "Test User"
  }'
```

### Login (get JWT)
```bash
curl -X POST https://nexusos.cloud/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "audit@nexusos.test",
    "password": "AuditTest123!"
  }'
```

### Use JWT in requests
```bash
# Replace TOKEN with actual JWT from login response
curl https://nexusos.cloud/api/agents \
  -H "Authorization: Bearer TOKEN"
```

### Test chat endpoint
```bash
curl -X POST https://nexusos.cloud/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "message": "Hello, world!"
  }'
```

### Test MCP tools
```bash
curl https://nexusos.cloud/mcp/tools \
  -H "Authorization: Bearer TOKEN"
```

## Test Data

### Pre-created test agents
- `test-agent-1` - Basic agent for testing
- `test-agent-2` - Agent with custom tools

### Test conversations
- Create via API using test accounts

---

## Reset Test Data

To reset test data to clean state:

```bash
ssh root@187.124.150.225

# Delete test users
docker exec nexusos-postgres psql -U nexusos -c "
  DELETE FROM users WHERE email LIKE '%@nexusos.test';
"

# Reset sequences
docker exec nexusos-postgres psql -U nexusos -c "
  ALTER SEQUENCE users_user_id_seq RESTART;
  ALTER SEQUENCE agents_agent_id_seq RESTART;
"
```

---

*Last updated: 2026-03-16*
