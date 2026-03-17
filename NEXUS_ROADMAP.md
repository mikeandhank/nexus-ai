# NexusOS Project Roadmap
## Two-Project Architecture: Nexus Server + NexusOS Client
**Last Updated:** March 17, 2026

---

# ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                    NEXUS SERVER (Cloud)                        │
│                 api.nexusos.ai / nexus.ai                       │
├─────────────────────────────────────────────────────────────────┤
│  Purpose: Auth, LLM Routing, Billing, User Management          │
│                                                                     │
│  User signs up → gets Nexus API Key → configures LLM preference  │
│  Client calls API → Server routes to LLM → deducts credits     │
└─────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ X-Nexus-Key: sk-nexus-xxx
                                    │
┌─────────────────────────────────────────────────────────────────┐
│                    NEXUSOS CLIENT (Local)                       │
│                  Runs on User's Machine / VPS                  │
├─────────────────────────────────────────────────────────────────┤
│  Purpose: Agent Runtime, Memory, Tools, Local Processing      │
│                                                                     │
│  Agent Runtime, Memory System, Skills, Tool Engine, Inner Life  │
│  Communicates with Nexus Server for LLM access                 │
└─────────────────────────────────────────────────────────────────┘
```

---

# NEXUS SERVER

## What We Have (✅)
| Component | File | Status |
|-----------|------|--------|
| Multi-provider LLM routing | llm_integration.py | ✅ DONE |
| Credit system | billing.py | ✅ DONE |
| Usage tracking | billing.py | ✅ DONE |
| Encryption at rest | encryption.py, pgcrypto | ✅ DONE |
| JWT Auth | auth.py | ✅ DONE |
| API Key system | server_api.py | ✅ DONE |
| Chat endpoint | server_api.py | ✅ DONE |

## What We Need (🔴)

### Phase 1: Core (This Week)
| # | Item | Status |
|---|------|--------|
| 1 | Deploy server_api.py to production | 🔴 NOT STARTED |
| 2 | Test /api/chat with real API key | 🔴 NOT STARTED |
| 3 | Add provider keys (OpenAI, Anthropic) | 🔴 NOT STARTED |
| 4 | Connect usage tracking to /chat | 🔴 NOT STARTED |

### Phase 2: Auth & Users
| # | Item | Status |
|---|------|--------|
| 5 | API key validation middleware | 🔴 NOT STARTED |
| 6 | User dashboard API | 🔴 NOT STARTED |
| 7 | Register/Login endpoints | 🔴 NOT STARTED |

### Phase 3: Billing
| # | Item | Status |
|---|------|--------|
| 8 | Stripe integration | 🔴 NOT STARTED |
| 9 | Credit purchase flow | 🔴 NOT STARTED |
| 10 | Usage dashboard API | 🔴 NOT STARTED |

---

# NEXUSOS CLIENT

## What We Have (✅)
| Component | File | Status |
|-----------|------|--------|
| Agent Runtime | agent_runtime.py | ✅ DONE |
| Multi-agent Pool | agent_pool.py | ✅ DONE |
| Memory System | memory_consolidation.py | ✅ DONE |
| Skills System | skills.py | ✅ DONE |
| Tool Engine | tool_engine.py | ✅ DONE |
| MCP Protocol | mcp_server.py | ✅ DONE |
| Inner Life | affect_layer.py, theory_of_mind.py, etc | ✅ DONE |
| Background Processing | background_processor.py | ✅ DONE |
| Process Manager | (in agent_runtime) | ✅ DONE |

## What We Need (🔴)

### Phase 1: Server Communication
| # | Item | Status |
|---|------|--------|
| 1 | CLI client (connects to API) | ✅ DONE (client_cli.py) |
| 2 | Nexus API Key config | 🔴 NOT STARTED |
| 3 | /chat command (call server) | 🔴 NOT STARTED |
| 4 | /config command (sync settings) | 🔴 NOT STARTED |

### Phase 2: Integration
| # | Item | Status |
|---|------|--------|
| 5 | Offline mode (Ollama fallback) | 🔴 NOT STARTED |
| 6 | Usage sync | 🔴 NOT STARTED |
| 7 | Auto-retry on failure | 🔴 NOT STARTED |

---

# DATABASE TABLES

## Added This Session
```sql
-- Users (extended)
ALTER TABLE users ADD COLUMN nexus_api_key TEXT UNIQUE;
ALTER TABLE users ADD COLUMN credits numeric DEFAULT 0;
ALTER TABLE users ADD COLUMN subscription_tier TEXT DEFAULT 'free';

-- User LLM Config
CREATE TABLE user_llm_config (
    user_id TEXT REFERENCES users(id),
    provider TEXT DEFAULT 'openai',
    model TEXT DEFAULT 'gpt-4o-mini',
    fallback_provider TEXT,
    fallback_model TEXT,
    is_default BOOLEAN DEFAULT true
);

-- API Keys
CREATE TABLE api_keys (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    key_prefix TEXT DEFAULT 'sk-nexus-',
    key_hash TEXT NOT NULL,
    name TEXT,
    last_used TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);
```

---

# API ENDPOINTS

## Implemented
| Endpoint | Method | Status |
|----------|--------|--------|
| /api/auth/register | POST | ✅ DONE |
| /api/auth/login | POST | ✅ DONE |
| /api/config | GET | ✅ DONE |
| /api/config | PUT | ✅ DONE |
| /api/models | GET | ✅ DONE |
| /api/chat | POST | ✅ DONE |
| /api/credits | GET | ✅ DONE |
| /api/credits/purchase | POST | ✅ DONE |
| /api/usage | GET | ✅ DONE |
| /api/usage/summary | GET | ✅ DONE |

---

# SECURITY MODEL

## Keys Hierarchy
1. **Nexus API Key** (`sk-nexus-xxx`) - identifies user, no LLM access
2. **Provider Keys** - encrypted on server (OpenAI, Anthropic, etc.)
3. **User BYOK Keys** - optional, user provides their own

## Security Rules
- [x] Provider keys encrypted at rest (pgcrypto)
- [ ] Keys decrypted only in RAM at request time
- [ ] Every key use logged
- [ ] Keys rotatable

---

# REVENUE MODEL

```
User buys credits → We route to LLM → We keep 5.5% fee
                                   
User BYOK → We route → We charge 5% of provider cost
```

---

# IMMEDIATE NEXT STEPS

1. **Deploy server_api.py** to production
2. **Add real provider API keys** (OpenAI, Anthropic)
3. **Test end-to-end** (register → get key → chat)
4. **Deploy client** instructions
