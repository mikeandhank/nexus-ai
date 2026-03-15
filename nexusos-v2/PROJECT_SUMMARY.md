# NexusOS - Self-Hosted AI Agent Platform

## What It Actually Is
A self-hosted AI chat server for developers and small teams who want local LLM access with MCP-compatible tool layer.

## Vision
An Operating System for Agentic AI - where AI agents can be created, managed, collaborated, and scaled.

---

## Verified Capabilities (Working Today)

### ✅ Core
| Capability | Status | Details |
|------------|--------|---------|
| **API Server** | ✅ Working | Flask, v5.0.0 |
| **Database** | ✅ Working | SQLite |
| **LLM Integration** | ✅ Working | Ollama, OpenRouter, Anthropic |
| **MCP Protocol** | ✅ Working | 8 tools |
| **RBAC** | ✅ Working | 4 roles |
| **Web UI** | ✅ Working | /ui |

### ⚠️ Needs Foundation First
| Capability | Status |
|------------|--------|
| PostgreSQL | ⬜ Not started |
| Redis | ⬜ Not started |
| JWT Auth | ⬜ Not started |

---

## Directory Structure
```
nexusos-v2/
├── api_server_v5.py      # Main API
├── database.py           # SQLite (needs PostgreSQL)
├── llm_integration.py    # Multi-provider LLM
├── tool_engine.py        # 12 tools
├── mcp_server.py         # MCP protocol
├── agent_pool.py         # Agent templates
├── rbac.py              # Roles
├── event_bus_v2.py       # Event system
├── skills.py            # Skills registry
│
├── tasks/               # Celery-ready
├── templates/           # Web UI
├── docker-compose.yml
└── PROJECT_SUMMARY.md
```

---

## Live System
- **API:** http://187.124.150.225:8080/api/status
- **UI:** http://187.124.150.225:8080/ui
- **MCP:** http://187.124.150.225:8080/mcp/tools

---

## What's Next (In Priority Order)

1. **PostgreSQL** - Foundation for concurrent agents
2. **Redis** - Shared state store
3. **JWT Auth** - Real authentication
4. **Agent Lifecycle** - Create, run, pause, stop
5. **Inter-Agent Communication** - Message bus

---

## What We're NOT Claiming
- ❌ "Competing with Microsoft"
- ❌ "Enterprise-ready" (yet)
- ❌ SOC2/HIPAA compliance
- ❌ 50+ integrations

---

## What We ARE
- ✅ Self-hosted
- ✅ Open architecture
- ✅ MCP protocol support
- ✅ Developer-friendly
- ✅ Privacy-first

---

_Version: 5.0.0_
_Last updated: 2026-03-14_
_Honest positioning after third-party audit_