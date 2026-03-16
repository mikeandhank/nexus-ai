# NexusOS API Documentation

**Version:** 6.0.0  
**Base URL:** `https://nexusos.cloud`

---

## Authentication

### Register
```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword",
  "name": "John Doe"
}
```

**Response:** `201 Created`
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "role": "user"
}
```

### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbG...",
  "refresh_token": "eyJhbG...",
  "expires_in": 3600
}
```

### Refresh Token
```http
POST /api/auth/refresh
Authorization: Bearer <refresh_token>
```

---

## Agents

### List Agents
```http
GET /api/agents
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "agents": [
    {
      "id": "uuid",
      "name": "MyAgent",
      "role": "general",
      "status": "running",
      "created_at": "2026-03-15T12:00:00Z"
    }
  ]
}
```

### Create Agent
```http
POST /api/agents
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "MyAgent",
  "role": "analyst",
  "system_prompt": "You are a helpful research assistant."
}
```

### Start Agent
```http
POST /api/agents/{agent_id}/start
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "message": "Hello, how can you help me?"
}
```

### Stop Agent
```http
POST /api/agents/{agent_id}/stop
Authorization: Bearer <access_token>
```

---

## Chat

### Send Message
```http
POST /api/chat
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "message": "Hello!"
}
```

**Response:** `200 OK`
```json
{
  "response": "Hello! How can I help you today?",
  "agent_id": "uuid",
  "conversation_id": "uuid"
}
```

---

## Observability

### Health Check
```http
GET /api/observability/health
```

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "ollama": {
      "status": "ok",
      "models": 1
    }
  },
  "timestamp": "2026-03-15T12:00:00Z"
}
```

### System Status
```http
GET /api/status
```

---

## Webhooks

### List Webhooks
```http
GET /api/webhooks
Authorization: Bearer <access_token>
```

### Create Webhook
```http
POST /api/webhooks
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "MyWebhook",
  "url": "https://example.com/webhook",
  "events": ["agent.started", "agent.stopped"]
}
```

---

## MCP Protocol

### List Tools
```http
GET /mcp/tools
```

### Call Tool
```http
POST /mcp/tools/call
Content-Type: application/json

{
  "name": "file_read",
  "arguments": {
    "path": "/path/to/file"
  }
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "Invalid request",
  "message": "Missing required field: email"
}
```

### 401 Unauthorized
```json
{
  "error": "Unauthorized",
  "message": "Invalid or expired token"
}
```

### 403 Forbidden
```json
{
  "error": "Forbidden",
  "message": "Admin access required"
}
```

### 404 Not Found
```json
{
  "error": "Not Found",
  "message": "Resource not found"
}
```

### 429 Too Many Requests
```json
{
  "error": "Rate Limited",
  "message": "Too many requests",
  "retry_after": 60
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal Error",
  "message": "An unexpected error occurred"
}
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| /api/chat | 60/min |
| /api/agents | 10/min |
| /api/* | 100/min |

---

## Code Examples

### Python
```python
import requests

BASE_URL = "https://nexusos.cloud"

# Login
resp = requests.post(f"{BASE_URL}/api/auth/login", json={
    "email": "user@example.com",
    "password": "password"
})
token = resp.json()["access_token"]

# Send message
resp = requests.post(
    f"{BASE_URL}/api/chat",
    headers={"Authorization": f"Bearer {token}"},
    json={"message": "Hello!"}
)
print(resp.json()["response"])
```

### cURL
```bash
# Login
TOKEN=$(curl -s -X POST https://nexusos.cloud/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}' | jq -r '.access_token')

# Send message
curl -X POST https://nexusos.cloud/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello!"}'
```
