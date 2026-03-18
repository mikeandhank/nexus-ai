# NexusOS API Documentation

## Base URL
```
http://187.124.150.225:8080
```

## Authentication
Most endpoints require JWT authentication. Register or login to get a token.

### Register
```bash
curl -X POST http://187.124.150.225:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass123","name":"User"}'
```

### Login
```bash
curl -X POST http://187.124.150.225:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass123"}'
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user_id": "uuid",
  "name": "User"
}
```

### Use Token
Include in headers:
```bash
-H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Core Endpoints

### GET /api/status
System health check.

**Response:**
```json
{
  "running": true,
  "version": "18",
  "components": {
    "database": true,
    "postgresql": true,
    "redis": true,
    "llm_manager": true
  }
}
```

### GET /api/dashboard
Simple system dashboard.

**Response:**
```json
{
  "status": "running",
  "version": "18",
  "infrastructure": {
    "postgresql": "connected",
    "redis": "connected"
  }
}
```

---

## Chat

### POST /api/chat
Send a message to the AI.

```bash
curl -X POST http://187.124.150.225:8080/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"message":"Hello"}'
```

**Response:**
```json
{
  "response": "Hello! How can I help?",
  "model": "phi3"
}
```

---

## Agents

### GET /api/agents
List all agents.

### POST /api/agents
Create an agent.

### POST /api/agents/{id}/start
Start an agent.

### POST /api/agents/{id}/stop
Stop an agent.

---

## Conversations

### GET /api/conversations
List conversations.

### GET /api/conversations/{id}
Get conversation messages.

---

## Memory

### POST /api/memory/remember
Store a memory.
```json
{"key": "preference", "value": "likes coffee"}
```

### POST /api/memory/recall
Recall memories.
```json
{"query": "what do they like?"}
```

---

## Webhooks

### GET /api/webhooks
List webhooks.

### POST /api/webhooks
Register a webhook.
```json
{"url": "https://example.com/hook", "events": ["chat.started"]}
```

### DELETE /api/webhooks/{id}
Delete a webhook.

---

## System

### GET /api/limits
Get rate limits and kill switches.

### GET /api/metrics
Get usage metrics.

### GET /api/logs
Get audit logs.

### POST /api/backup
Create backup.

### GET /api/backup
List backups.

---

## SSO

### GET /api/auth/sso/status
Check SSO providers.

**Response:**
```json
{
  "providers": {
    "google": {"enabled": false, "configured": false},
    "github": {"enabled": false, "configured": false},
    "microsoft": {"enabled": false, "configured": false}
  }
}
```

---

## Models

### GET /api/models
List available LLM models.

### POST /api/models
Add a model.

---

## Tenant Management (Admin)

### GET /api/tenants
List tenants (admin only).

### GET /api/tenants/{id}/users
List users in a tenant.

---

*Generated: 2026-03-15*
