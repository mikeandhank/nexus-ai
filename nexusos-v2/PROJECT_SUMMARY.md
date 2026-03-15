# NexusOS - Enterprise AI Agent Operating System

## Project Overview

**NexusOS** is a self-hosted, privacy-first AI Agent Operating System designed for enterprises that cannot use cloud AI solutions due to compliance, privacy, or cost constraints.

### Vision
Redefine enterprise AI by delivering an open, self-hosted alternative to Microsoft Copilot, Salesforce Agentforce, and AWS Bedrock that competitors cannot match.

### Target Market
- Companies that cannot use cloud AI (regulatory compliance)
- Developers who want full control
- Enterprises migrating from expensive platforms

---

## Verified Capabilities (Working Today)

### ✅ Core Infrastructure
| Capability | Status | Details |
|------------|--------|---------|
| **API Server** | ✅ Working | Flask on port 8080, v5.0.0 |
| **Database** | ✅ Working | SQLite, persistent |
| **LLM Integration** | ✅ Working | Ollama, OpenRouter, Anthropic (BYOK) |
| **Multi-Provider** | ✅ Working | Free/Basic/Pro tiers |

### ✅ Features
| Feature | Status | Details |
|---------|--------|---------|
| **MCP Protocol** | ✅ Working | 8 tools (file_read, file_write, process_run, http_get, http_post, system_info, search_files, file_list) |
| **RBAC** | ✅ Working | 4 roles: admin, developer, user, viewer |
| **Web UI** | ✅ Working | Modern dark theme at /ui |
| **BYOK Model** | ✅ Working | Encrypted API key storage |
| **Subscription Tiers** | ✅ Working | Free (Ollama), Basic ($9.99), Pro ($29.99) |

### ✅ Integration Ready
| Integration | Status | Endpoint |
|-------------|--------|----------|
| **REST API** | ✅ Working | /api/* |
| **MCP Protocol** | ✅ Working | /mcp/* |
| **Web UI** | ✅ Working | /ui |
| **Docker** | ✅ Ready | docker-compose.yml |

---

## Directory Structure

```
nexusos-v2/
├── api_server_v5.py      # Main Flask API server
├── api_server_v4.py      # Legacy (deprecated)
├── database.py           # SQLite database layer
├── llm_integration.py    # Multi-provider LLM management
├── tool_engine.py        # Tool execution engine (12 tools)
├── mcp_server.py         # MCP protocol server
├── agent_pool.py         # Multi-agent pool management
├── skills.py             # Built-in skills system
├── event_bus_v2.py       # Event-driven architecture
├── rbac.py              # Role-based access control
│
├── templates/
│   └── index.html       # Web UI (modern dark theme)
│
├── tasks/               # Async task system (Celery-ready)
│   ├── celery_app.py
│   ├── llm_tasks.py
│   └── tool_tasks.py
│
├── docker-compose.yml   # Docker orchestration
├── nginx.conf          # Reverse proxy with TLS
├── ssl/                # Self-signed SSL certificates
│
└── [other config files]
```

---

## What Can It Do Today?

### For End Users
1. **Chat with AI** - Use local (Ollama) or cloud (OpenRouter, Anthropic) models
2. **Self-hosted** - Full control, no vendor lock-in
3. **API Keys** - Bring your own keys (BYOK) for premium models
4. **Multi-tier Pricing** - Free, Basic, Pro plans

### For Developers
1. **MCP Protocol** - Standard agent interface (8 tools)
2. **Tool Engine** - 12 built-in tools (file, process, HTTP, search)
3. **Agent Pool** - Multiple AI agent templates
4. **Skills System** - Extendable skill registry

### For Enterprise
1. **RBAC** - Role-based permissions (admin/developer/user/viewer)
2. **SQLite** - Persistent database
3. **Docker** - Containerized deployment
4. **TLS Ready** - SSL configuration in place

---

## What Are We Working On?

### Phase 1 Priorities (Current Sprint)
| Priority | Feature | Status |
|----------|---------|--------|
| 1 | Multi-Agent Orchestration | Not started |
| 2 | Redis + Celery (async) | Files created |
| 3 | Usage Analytics | Not started |
| 4 | Webhook System | Code added |

### Enterprise Gaps (Roadmap)
- Governance Dashboard
- SSO/SAML
- 50+ Enterprise Integrations
- Rate Limiting/Quotas
- Agent Marketplace
- Hybrid Deployment (cloud + on-prem)
- SOC2 Type II Certification

---

## System Details

### Deployment
- **Server:** 187.124.150.225
- **Port:** 8080 (API), 11435 (Ollama)
- **Container:** nexusos-v2-flask
- **Database:** /opt/nexusos-data/nexusos.db

### Verified Endpoints
```
GET  /api/status           → 200 OK
POST /api/auth/register    → 200 OK
POST /api/auth/login       → 200 OK
POST /api/chat             → 200 OK
GET  /mcp/tools            → 200 OK
GET  /mcp/resources        → 200 OK
POST /mcp/initialize       → 200 OK
POST /mcp                  → 200 OK (JSON-RPC)
GET  /api/roles            → 200 OK
GET  /api/permissions      → 200 OK
GET  /ui                   → 200 OK
```

### Subscription Tiers
- **Free:** Ollama only (local models)
- **Basic ($9.99/mo):** Ollama + OpenRouter
- **Pro ($29.99/mo):** All providers + encrypted key storage

---

## The Goal

**Short-term:** Build the best self-hosted AI agent platform for developers and small teams.

**Long-term:** Compete with Microsoft, Salesforce, and AWS in the enterprise AI space by offering:
- Self-hosting (what they can't easily match)
- Open architecture (no vendor lock-in)
- 10x better price/performance

**Success Metrics:**
- 1000+ self-hosted deployments
- $100K ARR
- 50+ integrations
- 99.9% uptime SLA

---

## How to Evaluate

1. **Start the server:** `curl http://187.124.150.225:8080/api/status`
2. **Register a user:** `POST /api/auth/register`
3. **Chat:** `POST /api/chat` with message
4. **Check MCP:** `GET /mcp/tools`
5. **Access UI:** Open http://187.124.150.225:8080/ui in browser

---

## Cron Jobs Running

| Job | Frequency | Purpose |
|-----|-----------|---------|
| nexusos-enterprise-check | 10 min | Progress vs roadmap |
| nexusos-enterprise-audit | 1 hour | C-Suite evaluation |
| nexusos-api-health | 5 min | Uptime monitoring |
| nexusos-test | 1 hour | Regression tests |
| nexusos-deploy | 30 min | Auto-deploy |
| nexusos-backup | Daily | Database backup |
| nexusos-logs-rotate | Daily | Disk management |
| auto-commit-work | 2 hours | Git commits |

---

_Last updated: 2026-03-14_
_Version: 5.0.0_