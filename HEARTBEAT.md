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

**Progress (2026-03-16):**
- ✅ All 6 Inner Life capabilities built
- ✅ **DEPLOYED TO HOSTINGER** - Docker containers running (API on :8080, Ollama on :11435)
- ✅ **PostgreSQL** - 8 tables (users, conversations, messages, agents, memory, audit_log, events, api_usage)
- ✅ **Redis** - Shared state + Celery broker
- ✅ **JWT Authentication** - Register/Login/Refresh/Logout, bcrypt, token rotation
- ✅ **Agent Lifecycle** - Create, start, stop, pause, resume, delete agents
- ✅ **Web UI** - /ui with dark theme, login/register, chat, agents, settings
- ✅ **MCP Protocol** - JSON-RPC at /mcp with 8 tools, 5 resources
- ✅ **Cron Jobs** - Health check (5min), backup (3AM), logs-rotate (4AM), etc.
- ✅ **Easy-Install Package** - `easy-install/` with one-line deploy:
  - `docker-compose.yml` - minimal (API + DB + Redis + optional Ollama)
  - `install.sh` - `curl -sL https://get.nexusos.cloud | bash`
  - Auto-generates secure secrets
  - Health checks + automatic migrations
- ✅ **Extended Tools** - Added to `tools/`:
  - `browser_tool.py` - open, click, type, screenshot (Playwright)
  - `web_tool.py` - web_search, web_fetch  
  - `messaging_tool.py` - telegram, discord, slack
  - `node_tool.py` - camera, photos, location, notifications
  - `email_tool.py` - send, inbox, read, search (IMAP/SMTP)
  - `cron_tool.py` - schedule, run, list jobs
  - Integrated into `tool_engine.py`
  - Dockerfile updated with dependencies

# Notes
- Positioning revised: "Self-hosted AI agent platform" not "enterprise competitor"
- Path: PostgreSQL ✅ → Redis ✅ → JWT Auth ✅ → Agent Lifecycle ✅ → Easy-Install ✅ → Tools ✅ → Deploy → Observability
- Cut: Subscription tiers, marketplace, SSO, SOC2 (deferred)
- Don't interrupt during quiet hours (10PM-6AM MT) unless urgent
- Batch findings into brief bullet points
- Always confirm when tasks complete