# NexusOS - Agent Operating System

## Status: IN PROGRESS (as of 2026-03-14)

Platform for AI agents with inner life. Built on OpenClaw (MIT licensed).

---

## What's Built

### Inner Life Capabilities
| Capability | Status | Evidence |
|------------|--------|----------|
| Affect Layer | ✅ Working | Returns directives for real messages |
| Socratic Dialogue | ✅ Working | Passes run locally with phi3 |
| Pattern Library | ⚠️ Empty | Needs real interactions |
| Inner Narrative | ⚠️ Basic | Exists, minimal content |
| Theory of Mind | ⚠️ Empty | Needs real interactions |
| Background Processing | ✅ Working | 10-min loop running |

### Infrastructure
- **Hostinger VPS**: 187.124.150.225
- **Web UI**: http://187.124.150.225:8080/
- **Ollama API**: http://187.124.150.225:11435/
- **Model**: phi3 (3.8B params)
- **OpenClaw**: Running on port 47052

### Integration
- `nexusos/openclaw_integration.py` bridges inner life to response flow
- Maps directives to thinking levels
- Ready to wire into actual agent

---

## What Needs Building (Product-Ready)

### 1. Wire Into Response Flow
- **Status**: Integration code exists, not yet live
- **Next**: Add to OpenClaw hooks or agent prompt

### 2. User Authentication
- **Status**: Not started
- **Need**: Simple auth for web UI (per-user accounts)
- **Options**: Simple token-based, or integrate with auth providers

### 3. Per-User Conversation Memory
- **Status**: Not started
- **Need**: Each user gets separate memory/context
- **Approach**: User ID → separate memory stores

---

## Platform Architecture

```
┌─────────────────────────────────────────┐
│           User (Web/Telegram/etc)       │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│         NexusOS Web UI (8080)           │
│  - Auth                                 │
│  - Chat interface                       │
│  - User memory                          │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│    NexusOS Inner Life (OpenClaw)        │
│  - Affect Layer                         │
│  - Socratic Dialogue                    │
│  - Pattern Library                      │
│  - Theory of Mind                       │
│  - Background Processing                │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│      Ollama (phi3) - Hostinger          │
│  - Local LLM                            │
│  - Private reasoning                    │
└─────────────────────────────────────────┘
```

---

## Foundation Knowledge (Configurable, Not Hardcoded)

- Capacity for knowledge exists
- Per-user/configurable:
  - Goals
  - Communication style
  - Domain expertise
  - Product context
- Universal:
  - Conversation patterns
  - Memory architecture
  - Learning from feedback
  - Tool usage
  - Safety guidelines

---

_Last updated: 2026-03-14_