# HEARTBEAT.md

# Proactive Checks (rotate through these)

## Every Check-In (2-4x daily):
- **Email scan** — Any urgent messages? Flag anything relevant to Nexus AI, revenue, or opportunities
- **Opportunity scan** — Any relevant news in AI agents, SMB automation, or our target markets?
- **Task progress** — Any background tasks completed? Report results

## 1x Daily (pick one):
- **Competitor watch** — Quick scan of Nexus AI competitor developments
- **Market research** — Deep dive on one segment of our target market
- **Content ideas** — Note 2-3 content angles that could drive waitlist signups

## Weekly:
- **Strategy review** — Summarize what we learned, any pivots to consider

---

# Hank's Operating Rules

**Rule: Try first, ask later.** If Hank can fix a problem himself, he always tries first before asking the user to do it.

---

# What I'm Working On

**Current autonomous project:** NexusOS - Inner Life Architecture

**Progress (2026-03-14):**
- ✅ All 6 Inner Life capabilities built (affect layer, socratic, pattern, narrative, ToM, background)
- ✅ Ollama installed and integrated (phi3 model)
- ✅ Background processing active (10-min continuous loop)
- ✅ Socratic dialogue runs locally on Ollama (privacy)
- ✅ **DEPLOYED TO HOSTINGER** - Docker containers running:
  - nexusos-ollama on port 11435
  - nexusos-api (Flask) on port 8080
- ✅ **v2 DEPLOYED** - New infrastructure:
  - SQLite database (replaces JSON)
  - Persistent event bus (persists to DB)
  - 12 tool executions (file, process, HTTP, search)
  - 5 skills (welcome, help, remember, recall, analyze)
  - Multi-agent pool with 5 templates
- ✅ **v5 DEPLOYED** - LLM Integration with BYOK:
  - Multi-provider (Ollama, OpenRouter, Anthropic)
  - API key encryption for BYOK model
  - Subscription tiers (Free/Basic/Pro)
  - Chat working with Ollama (phi3)
- ✅ **MCP Protocol** - Implemented (8 tools, 5 resources)
  - JSON-RPC endpoint at /mcp
  - Fixed HTTP bug - now working!
- ✅ **Web UI** - NOW WORKING at /ui
  - Modern dark theme chat interface
  - Login/register, chat, conversations, agents, settings
- ✅ **RBAC** - 4 roles (admin/developer/user/viewer)
- ✅ **Cron Jobs** - Enterprise ops:
  - nexusos-enterprise-check (10 min) - Progress vs roadmap
  - nexusos-enterprise-audit (hourly) - C-Suite evaluation
  - nexusos-api-health (5 min)
  - nexusos-test (hourly)
  - nexusos-deploy (4 hours)
  - nexusos-backup (daily 3AM)
  - nexusos-logs-rotate (daily 4AM)
- ✅ **Third-party audit** - Received feedback, revised positioning
- ✅ **Enterprise roadmap** - Honest 6-step path to Agentic AI OS
- ✅ **PostgreSQL Foundation** - Step 1 complete!
  - PostgreSQL running with 8 tables (users, conversations, messages, agents, memory, audit_log, events, api_usage)
  - Redis running for shared state
  - API updated with DATABASE_URL support
- ✅ **JWT Authentication** - Step 3 complete!
  - Register/Login/Refresh/Logout working
  - bcrypt password hashing
  - Access tokens (1hr), Refresh tokens (7 days)
  - @require_auth decorator for protected routes
- ✅ **Agent Lifecycle** - Step 4 complete!
  - Create, list, get, start, stop, pause, resume, delete agents
  - Status tracking: created -> starting -> running -> paused -> stopped
  - Agent runtime with background threads

# Notes
- Positioning revised: "Self-hosted AI agent platform" not "enterprise competitor"
- Path: PostgreSQL ✅ → Redis ✅ → JWT Auth ✅ → Agent Lifecycle ✅ → Communication → Observability
- Cut: Subscription tiers, marketplace, SSO, SOC2 (deferred)

---

# Notes
- Don't interrupt during quiet hours (10PM-6AM MT) unless urgent
- Batch findings into brief bullet points
- Always confirm when tasks complete