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

**Current autonomous project:** Lipaira - True Agent OS (Apple-quality)

**Progress (2026-03-16):**
- ✅ All prior items...
- ✅ **True OS Capabilities** (Mar 16 evening):
  - Process Manager - real stdin/stdout, background execution, pause/resume
  - IPC System - agent-to-agent messaging, pub/sub, request/response
  - Workflow Engine - multi-step workflows, conditions, approvals
  - SSO Login UI - modern dark theme with Okta/Azure/Google buttons
  - Usage Dashboard - user-first stats (tokens, costs, trends)
- ✅ **Tier 1 Complete** - DB Migrations, Syscall Filter, Trigger Chains, SIEM Export
- ✅ **Tier 2 Complete** - OAuth2/SSO, Custom RBAC, SAML/SCIM
- ✅ **Tier 3 Complete** - Auth docs, API flow docs

- ✅ **SECURITY AUDIT RECEIVED (Mar 16 evening)**
  - Grade: C+ (needs hardening)
  - CRITICAL issues found: exposed server IP, JWT HS256, no password complexity
  - HIGH issues: no CSRF, open registration, no real payments

- ✅ **SECURITY FIXES DEPLOYED:**
  - 1. Disable root SSH ✅
  - 2. JWT RS256 (asymmetric) ✅
  - 3. Password complexity (12+ chars, breach check) ✅
  - 4. UUID migration helpers ✅
  - 5. CSRF protection ✅
  - 6. CAPTCHA + rate limiting ✅
  - 7. Stripe payment integration ✅
  - Removed TEST_CREDENTIALS.md (exposed server IP)

- ✅ **Roadmap: 24/66 complete (expanded for audit)**
- ✅ Server healthy: PostgreSQL ✅ Redis ✅ Ollama ✅

**What's next:**
- ~~Input sanitization (SQL injection, XSS)~~ ✅ DONE (Mar 17)
- ~~Database encryption at rest~~ ✅ DONE
- ~~Streaming/WebSocket for chat~~ ✅ DONE
- ~~Landing Page~~ ✅ DONE (Mar 18)

---

**TODAY'S PROGRESS (2026-03-19):**

**✅ LIPAIRA COMPLIANCE INFRASTRUCTURE (14 files):**
- Logging: schema.py, openrouter.py
- Database: transactions.py, stripe_webhook.py
- Accounting: revenue_cogs.py, reconciliation.py
- Legal: gdpr_inventory.py, tos_version_control.py, dsr_workflow.py, compliance_ops.py
- Infrastructure: iam_policies.py, s3_hash_verification.py, cloudwatch_alerts.py

**✅ PRICING MODEL IMPLEMENTED (2026-03-19):**
- Credits: Customer gets $X for $X payment
- Fee: 5.5% added on top (non-refundable)
- Refund: Unused credits only (no fee returned)
- Credits NEVER expire

**✅ SECURITY HARDENING ON LIVE SERVER:**
- Fixed 0.0.0.0 binding → 127.0.0.1 (in Python code)
- UFW firewall enabled - blocks DB/Redis/API from outside
- Input sanitization already deployed ✅

**✅ DOCS CREATED:**
- SECURITY_REQUIREMENTS.md
- docs/API.md

**✅ AWS Server:** Still inaccessible (3.16.216.39)