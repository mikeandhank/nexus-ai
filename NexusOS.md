# NexusOS - Agent Operating System

## Status: SHIPPING (as of 2026-03-14)

Platform for AI agents with inner life. Built on OpenClaw (MIT licensed).

---

## What's Built

### Inner Life Capabilities
| Capability | Status | Notes |
|------------|--------|-------|
| Affect Layer | ✅ Working | Analyzes context before responding |
| Socratic Dialogue | ✅ Working | Adversarial reasoning available |
| Pattern Library | ⚠️ Empty | Needs real interactions |
| Inner Narrative | ⚠️ Basic | Exists, minimal content |
| Theory of Mind | ⚠️ Empty | Needs real data |
| Background Processing | ✅ Working | 10-min continuous loop |

### Product Features
| Feature | Status | Notes |
|---------|--------|-------|
| **User Auth** | ✅ Live | Simple token-based, works |
| **Per-User Memory** | ✅ Live | Conversations stored per user |
| **Multi-LLM Support** | ✅ Live | Ollama (free) + BYOK (paid) |
| **Web UI** | ✅ Live | `https://your-nexusos-server.example.com` |

### LLM Options
| Backend | Type | Cost | Models |
|---------|------|------|--------|
| Ollama | Local | Free | phi3, llama2, mistral |
| OpenAI | BYOK | User pays | gpt-4o, gpt-4o-mini |
| Anthropic | BYOK | User pays | claude-sonnet, claude-haiku |

---

## Usage

### Web Interface
```
https://your-nexusos-server.example.com
```
- Enter name/email to create account
- Chat with Ollama (free) or add OpenAI/Anthropic API key
- Conversations persist per user

### API
```bash
# List available models
curl https://your-nexusos-server.example.com/api/models

# Chat (requires user_id from login)
curl -X POST https://your-nexusos-server.example.com/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "YOUR_USER_ID", "message": "Hello"}'
```

---

## Architecture

```
┌─────────────────────────────────────────┐
│           Web Browser / API             │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│         NexusOS API (8080)              │
│  - Auth (token-based)                   │
│  - User memory (per-user JSON)          │
│  - Multi-LLM router                     │
│  - Chat interface                       │
└────────────────┬────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
┌───▼───┐              ┌──────▼──────┐
│Ollama │              │ BYOK (OpenAI│
│(free) │              │  Anthropic) │
└───────┘              └─────────────┘
```

---

## Monetization Model

| Tier | LLM Cost | Our Margin |
|------|----------|------------|
| Free (Ollama) | $0 | $0 |
| BYOK | User pays | $0 (yet) |
| **Future: OOTB** | We pay | 20-30% margin |

---

## What's Next

1. Wire NexusOS inner life into response flow (affect, socratic, etc.)
2. Add paid tier with our API keys (upcharge 20-30%)
3. Improve memory (patterns, lessons learned)
4. Add more free LLMs (local alternatives)

---

_Last updated: 2026-03-14_