# NexusOS API Documentation

## Overview
NexusOS is a self-hosted Operating System for Agentic AI. It provides:
- Multi-agent orchestration
- JWT authentication
- MCP tool protocol
- Webhook system
- Usage analytics

## Base URL
```
http://localhost:8080/api
```

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

**Response:**
```json
{
  "user_id": "uuid",
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "name": "John Doe"
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

**Response:**
```json
{
  "user_id": "uuid",
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "name": "John Doe",
  "role": "user"
}
```

### Refresh Token
```http
POST /api/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ..."
}
```

**Response:**
```json
{
  "access_token": "eyJ..."
}
```

### Logout
```http
POST /api/auth/logout
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "status": "logged_out"
}
```

---

## Chat

### Send Message
```http
POST /api/chat
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "message": "What is the weather?",
  "agent_id": "optional-agent-id"
}
```

**Response:**
```json
{
  "response": "The current weather is...",
  "agent_id": "agent-uuid",
  "usage": {
    "input_tokens": 100,
    "output_tokens": 250
  }
}
```

---

## Agents

### List Agents
```http
GET /api/agents
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "agents": [
    {
      "id": "uuid",
      "name": "Research Agent",
      "status": "running",
      "model": "phi3",
      "tools": ["file_read", "web_search"]
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
  "name": "My Agent",
  "model": "phi3",
  "system_prompt": "You are a helpful assistant...",
  "tools": ["file_read", "web_search"],
  "max_tokens": 4096
}
```

### Start Agent
```http
POST /api/agents/<agent_id>/start
Authorization: Bearer <access_token>
```

### Stop Agent
```http
POST /api/agents/<agent_id>/stop
Authorization: Bearer <access_token>
```

### Delete Agent
```http
DELETE /api/agents/<agent_id>
Authorization: Bearer <access_token>
```

---

## Webhooks

### Create Webhook
```http
POST /api/webhooks
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "event_type": "agent.created",
  "url": "https://example.com/webhook"
}
```

### List Webhooks
```http
GET /api/webhooks
Authorization: Bearer <access_token>
```

### Delete Webhook
```http
DELETE /api/webhooks/<webhook_id>
Authorization: Bearer <access_token>
```

### List Available Events
```http
GET /api/webhooks/events
```

**Response:**
```json
{
  "events": [
    "agent.created",
    "agent.started",
    "agent.stopped",
    "chat.message",
    "chat.complete",
    "user.registered",
    "user.login",
    "webhook.created",
    "webhook.deleted",
    "usage.exceeded"
  ]
}
```

---

## Usage Analytics

### Get Usage
```http
GET /api/usage?days=30
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "period_days": 30,
  "summary": {
    "total_tokens": 150000,
    "total_requests": 500,
    "total_cost": 0.50
  },
  "breakdown": [
    {
      "model": "phi3",
      "provider": "ollama",
      "tokens": 100000,
      "requests": 300,
      "cost": 0.0
    }
  ]
}
```

---

## Inter-Agent Communication

### Publish Message
```http
POST /api/messages/publish
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "channel": "agent.researcher",
  "type": "event",
  "from_agent": "coordinator",
  "payload": {
    "task": "research",
    "query": "AI trends"
  }
}
```

### Delegate Task
```http
POST /api/agents/delegate
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "capability": "web_search",
  "from_agent": "coordinator",
  "payload": {
    "query": "latest AI news"
  }
}
```

### Shared State
```http
# Get
GET /api/shared/project_context

# Set
PUT /api/shared/project_context
Content-Type: application/json

{
  "value": {"current_project": "NexusOS", "phase": 2}
}
```

---

## MCP Protocol

### List Tools
```http
GET /mcp/tools
```

### List Resources
```http
GET /mcp/resources
```

### Initialize
```http
POST /mcp/initialize
Content-Type: application/json

{
  "protocolVersion": "1.0",
  "capabilities": {"tools": true}
}
```

### Call Tool
```http
POST /mcp
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "file_read",
    "arguments": {"path": "/etc/hostname"}
  }
}
```

---

## System

### Status
```http
GET /api/status
```

**Response:**
```json
{
  "version": "5.0.0",
  "running": true,
  "enterprise": true,
  "components": {
    "database": true,
    "llm_manager": true,
    "postgresql": true,
    "redis": false
  }
}
```

### Health
```http
GET /api/health
```

### Roles
```http
GET /api/roles
```

### Permissions
```http
GET /api/permissions
```

---

## Error Responses

All endpoints may return:

```json
{
  "error": "Error message"
}
```

Common status codes:
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error
