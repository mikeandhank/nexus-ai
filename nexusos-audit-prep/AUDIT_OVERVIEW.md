# NexusOS - Enterprise Agent Operating System

## Executive Summary

**NexusOS** is a self-hosted, enterprise-grade AI Agent Operating System that enables organizations to deploy, manage, and orchestrate AI agents on their own infrastructure. Positioned as "the Apple of AI" - prioritizing seamless UX, security, and enterprise readiness.

### Key Value Propositions

| Feature | Description |
|---------|-------------|
| **Self-Hosted** | All data stays on user's server - complete data sovereignty |
| **True OS Capabilities** | Process management, IPC, workflows, sandbox isolation |
| **Multi-LLM Support** | Local (llama3, mistral, phi3, codellama) + BYOK premium models |
| **Enterprise Ready** | RBAC, SSO/SAML, SIEM export, usage metering |
| **5.5% Fee Model** | Transparent pricing like OpenRouter |

### Target Market

- **Enterprise**: Revenue-focused with advanced security/compliance needs
- **Indie/SMB**: Community-friendly pricing, full feature access

---

## Technical Architecture

### Core Stack

| Component | Technology |
|-----------|------------|
| **API Server** | Flask + Gunicorn |
| **Database** | PostgreSQL (persistent storage) |
| **Cache/Queue** | Redis (sessions, pub/sub, Celery) |
| **LLM Runtime** | Ollama (local models) |
| **Reverse Proxy** | Traefik v2.9 (TLS/SSL) |
| **Container** | Docker |

### Deployment

- **Server**: 187.124.150.225:8080
- **Domain**: nexusos.cloud (HTTPS enabled)
- **Web UI**: /ui
- **API**: /api/*

### File Structure

```
nexusos-v2/
├── api_server_v5.py       # Main Flask API
├── database.py            # PostgreSQL connection
├── database_v2.py         # Enhanced DB queries
├── jwt_rotation.py        # JWT auth with key rotation
├── user_routes.py         # User management
├── api_keys.py            # API key management
├── llm_integration.py     # Multi-LLM support (Ollama + BYOK)
├── byok_manager.py        # Bring Your Own Key management
├── tool_engine.py         # MCP tool execution engine
├── mcp_security.py        # MCP security middleware
├── connection_pool.py     # PostgreSQL connection pooling
├── message_bus.py         # Redis pub/sub message bus
├── usage_metering.py      # 5.5% fee calculation
├── usage_dashboard.py     # User-facing usage stats
├── dashboard_api.py       # Dashboard API endpoints
├── mcp_agent_memory.py    # Agent memory persistence
├── agent_resources.py     # Resource management
├── agent_trigger_chains.py # Multi-agent orchestration
├── workflow_engine.py     # Multi-step workflows
├── process_manager.py     # Real stdin/stdout, background processes
├── agent_ipc.py           # Inter-agent communication
├── sandbox_isolation.py   # gVisor/LXC/seccomp-bpf sandbox
├── kernel_syscall_filter.py # System call filtering
├── custom_rbac.py         # Enterprise RBAC with custom roles
├── oauth_sso.py           # OAuth2/SSO (Okta, Azure, Google)
├── saml_scim.py           # SAML 2.0 + SCIM 2.0
├── siem_export.py         # Splunk/ELK/Syslog export
├── nexusos_client.py      # Python client library
├── sso_oauth.py           # SSO OAuth utilities

inner_life/                # Agent cognitive layer
├── engine.py              # Inner Life orchestration
├── memory_graph.py        # Knowledge graph
├── affect_layer.py        # Emotional state
├── memory_summarization.py # Context optimization
├── context_optimizer.py   # Token optimization
├── inner_narrative.py     # Self-narrative

docs/                      # Documentation
├── authentication.md      # Bearer token guide
├── api-flow.md            # Auth flow documentation

templates/
└── sso-login.html         # Modern SSO login UI

migrations/                # Database migrations
└── __init__.py           # Alembic setup

docker-compose.yml         # Container orchestration
Dockerfile                 # API container
traefik-static.yml        # Traefik TLS config
traefik-dynamic.yml       # Traefik routing
```

---

## API Endpoints

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register` | POST | Register new user |
| `/api/auth/login` | POST | Login, get JWT |
| `/api/auth/refresh` | POST | Refresh access token |
| `/api/auth/logout` | POST | Invalidate refresh token |

### Core API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | System health |
| `/api/chat` | POST | Chat with agent |
| `/api/agents` | GET/POST | List/create agents |
| `/api/agents/<id>` | GET/PUT/DELETE | Agent CRUD |
| `/api/agents/<id>/start` | POST | Start agent |
| `/api/agents/<id>/stop` | POST | Stop agent |
| `/api/roles` | GET | List RBAC roles |
| `/api/usage` | GET | Usage statistics |
| `/api/reload` | POST | Add balance |

### MCP Protocol

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/tools` | GET | List available tools |
| `/mcp/execute` | POST | Execute tool |
| `/mcp/agents` | GET | List agents |

---

## Security Features

### Authentication & Authorization

- **JWT** with HS256 algorithm
- Access tokens: 1 hour expiry
- Refresh tokens: 7 day expiry
- Key rotation supported

### RBAC Roles

| Role | Permissions |
|------|-------------|
| **admin** | Full system access |
| **developer** | Agents, tools, read API |
| **user** | Basic access |
| **viewer** | Read-only |

### Security Components

- **System Call Filter**: Blocks dangerous syscalls (fork, mount, chroot, etc.)
- **Sandbox Isolation**: gVisor/LXC/seccomp-bpf options
- **Input Sanitization**: SQL injection, XSS prevention
- **Network Rate Limiting**: Per-IP limits
- **Container Isolation**: Docker network segmentation

### Enterprise Features

- **OAuth2/SSO**: Okta, Azure AD, Google Workspace
- **SAML 2.0**: Enterprise identity federation
- **SCIM 2.0**: User provisioning
- **SIEM Export**: Splunk, Elasticsearch, Syslog formats

---

## Database Schema

### Core Tables

| Table | Description |
|-------|-------------|
| `users` | User accounts |
| `conversations` | Chat sessions |
| `messages` | Message history |
| `agents` | Agent definitions |
| `api_usage` | Usage tracking |
| `api_keys` | API key management |
| `audit_log` | Security audit trail |
| `kernel_agents` | Agent runtime state |
| `kernel_events` | System events |
| `kernel_ipc` | IPC message persistence |
| `user_balances` | Prepaid balance |
| `api_reloads` | Balance reloads |

---

## Operational Details

### Running Services

- **PostgreSQL**: Port 5432
- **Redis**: Port 6379
- **Ollama**: Port 11435
- **API**: Port 8080
- **Traefik**: Ports 80, 443

### Available Models

| Model | Type | Context |
|-------|------|---------|
| phi3 | Local | 4K |
| llama3 | Local | 8K |
| mistral | Local | 8K |
| codellama | Local | 8K |

### Cron Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| health check | 5 min | Auto-heal |
| enterprise audit | 1 hour | Product evaluation |
| backup | Daily 3AM | Disaster recovery |
| security scan | Daily 1AM | Vulnerability check |
| logs rotate | Daily 4AM | Disk management |

---

## Compliance & Audit

### Audit Capabilities

- Full API audit logging
- User action tracking
- SIEM export (JSON)
- Compliance reports

### Security Posture

- TLS/SSL enabled (Let's Encrypt)
- HTTP→HTTPS redirect
- No secrets in code
- Environment-based config

---

## Roadmap Status

| Category | Complete | Remaining |
|----------|----------|-----------|
| Critical Blockers | 5 | 0 |
| Core Infrastructure | 10 | 0 |
| Enterprise Features | 7 | 0 |
| True OS Capabilities | 5 | 1 |
| Documentation | 2 | 1 |
| **TOTAL** | **48** | **2** |

---

## Contact & Support

- **Server**: 187.124.150.225
- **Domain**: https://nexusos.cloud
- **API**: https://nexusos.cloud/api
- **Web UI**: https://nexusos.cloud/ui

---

*Generated for third-party audit - March 16, 2026*
