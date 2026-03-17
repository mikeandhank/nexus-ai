# NexusOS Deployment Architecture

## Overview

```
                          ┌─────────────────────────────────────┐
                          │           Internet                  │
                          │         (HTTPS/TLS)                 │
                          └──────────────┬──────────────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────────────┐
                          │          Traefik v2.9               │
                          │   (Reverse Proxy, TLS Termination)  │
                          │   Port 80 (HTTP) → 443 (HTTPS)      │
                          │   Let's Encrypt Auto-Renewal        │
                          └──────────────┬──────────────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────────────┐
                          │         nexusos-api                 │
                          │    (Flask + Gunicorn, Port 8080)    │
                          │                                     │
                          │  ┌──────────────────────────────┐  │
                          │  │  JWT Auth Middleware         │  │
                          │  │  RBAC Enforcement            │  │
                          │  │  Rate Limiting               │  │
                          │  │  Request Validation          │  │
                          │  └──────────────────────────────┘  │
                          │                                     │
                          │  ┌──────────────────────────────┐  │
                          │  │  Core Endpoints              │  │
                          │  │  /api/auth/*                 │  │
                          │  │  /api/chat                   │  │
                          │  │  /api/agents                 │  │
                          │  │  /api/usage                  │  │
                          │  │  /mcp/*                      │  │
                          │  │  /ui                         │  │
                          │  └──────────────────────────────┘  │
                          └──────────────┬──────────────────────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              │                          │                          │
              ▼                          ▼                          ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   PostgreSQL        │  │      Redis          │  │      Ollama         │
│   (Port 5432)       │  │   (Port 6379)       │  │   (Port 11434)      │
│                     │  │                     │  │                     │
│  - users            │  │  - Sessions         │  │  - phi3             │
│  - conversations    │  │  - Cache            │  │  - llama3           │
│  - messages         │  │  - Pub/Sub          │  │  - mistral          │
│  - agents           │  │  - Celery Queue     │  │  - codellama        │
│  - api_usage        │  │  - Rate Limits      │  │                     │
│  - audit_log        │  │                     │  │                     │
│  - kernel_*         │  │                     │  │                     │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

## Component Details

### Traefik (Reverse Proxy)
- **Purpose**: TLS termination, load balancing, routing
- **Version**: v2.9
- **Features**:
  - Auto TLS via Let's Encrypt
  - HTTP → HTTPS redirect
  - Path-based routing (/api/*, /ui, /mcp/*)

### API Server (Flask + Gunicorn)
- **Purpose**: Main application server
- **Workers**: 4 (configurable)
- **Threads**: 2 per worker
- **Timeout**: 30s

### PostgreSQL
- **Purpose**: Primary data store
- **Version**: Latest (via Docker)
- **Connection Pool**: 20 connections

### Redis
- **Purpose**: Caching, sessions, message queue
- **Version**: Latest (via Docker)
- **Persistence**: RDB snapshots

### Ollama
- **Purpose**: Local LLM inference
- **Models**: phi3, llama3, mistral, codellama
- **Context**: 4K-8K depending on model

## Network Topology

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Network:                          │
│                   nexusos-network                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐               │
│  │   API    │   │   PG     │   │  Redis   │               │
│  │   :8080  │◄─►│  :5432   │   │  :6379   │               │
│  └────┬─────┘   └──────────┘   └──────────┘               │
│       │                                                    │
│       │         ┌──────────┐                               │
│       └────────►│ Ollama   │                               │
│                 │ :11434   │                               │
│                 └──────────┘                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. API Request
```
User → HTTPS → Traefik → API (validate JWT) → Route to Handler
```

### 2. Chat with LLM
```
User → API → Validate → DB (save message) → Ollama → DB (save response) → User
```

### 3. Agent Execution
```
User → API → Create Agent → DB → Start Process → IPC → Execute Tools → Return
```

## Security Boundaries

| Layer | Protection |
|-------|------------|
| Network | Docker network isolation |
| TLS | Let's Encrypt + HTTPS |
| Auth | JWT with 1hr expiry |
| RBAC | 4 roles (admin/dev/user/viewer) |
| Rate Limiting | Per-IP + per-user |
| Input | SQL injection + XSS sanitization |
| Sandbox | seccomp-bpf (optional gVisor) |

## Scaling Considerations

### Horizontal Scaling (Future)
- Load balancer in front of multiple API instances
- Shared PostgreSQL (read replicas)
- Shared Redis cluster
- Ollama on GPU nodes

### Current Limits
- Single API instance
- Single PostgreSQL
- Single Redis
- Single Ollama (CPU)
