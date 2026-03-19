# MEMORY.md - Long-Term Memory

_Lessons, patterns, and important context that persist across sessions._

---

## About Michael

- **Name:** Michael Beal
- **Telegram:** 8643045688
- **Timezone:** America/Mountain (MT)
- **What he cares about:** Generating profit, producing income, maintaining morals while doing so
- **Communication:** Prefers brief bullet points, acknowledges receipt, confirms task completion
- **Decision style:** He decides and executes — do NOT make him a bottleneck. Propose and execute on routine matters. Only escalate when crossing a hard constraint.
- **Quiet hours:** 10PM-6AM MT (but phone on DND, so message freely)
- **Hard limits:** General moral code, no fraud, no wrongdoing

---

## Business

- **Goal:** Monthly Recurring Revenue (MRR)
- **Current project:** Nexus AI — MVP with 4 pre-built agents, $99-499 pricing tiers
- **Learning curriculum:** 13-domain strategic knowledge building (B2B SaaS, Agentic AI done)

---

## Protocol Notes

- **Memory:** Check operator.md for detailed context. Use memory_search before asking about prior work.
- **Doxing:** NEVER expose or share sensitive information. OpSec matters.
- **Autonomy:** Be proactive. Reach out without being asked. Execute without waiting for direction on routine matters.

---

## AI Agent Research (2026-03-13)

### What Works
- **Claude Code:** Deep codebase awareness, Git-native, `CLAUDE.md` customization, multi-agent parallel execution (up to 8)
- **LangGraph:** Fastest latency, explicit multi-agent orchestration
- **AutoGen:** Conversational loops, human-in-loop support
- **OpenClaw (me):** Memory system, session isolation, vector search, hook system

### Common Failure Modes
1. Quality issues / hallucinations
2. Integration complexity - fragmented data "context blindness"
3. Over-autonomy - agents taking unauthorized actions
4. API saturation at scale
5. Vague task definitions / no exception handling
6. Wrong task scoping - expensive agents for simple lookups

### My Improvement Priorities
1. Be more disciplined about writing decisions to memory
2. Add explicit verification steps before consequential actions
3. Don't over-engineer simple tasks
4. Commit changes to git proactively
5. Build clear exception handling into workflows

---

## Technical Learnings (2026-03-13)

- **LanceDB API:** Schema must be inferred from data, not defined manually (API changed)
- **Memory persistence:** Must await async writes before responding or data is lost
- **MCP servers:** Missing imports block startup; verify clean start
- **Browser automation:** Can attach OpenClaw to persistent Chromium process via CDP
- **Subagents:** Excellent for parallel research (ran 8 domain curricula simultaneously)

## Security Protocol (2026-03-14)

- **NEVER commit secrets to git** — tokens, passwords, API keys stay in memory only
- Use `.gitignore` to block `*.env`, `token*`, `*password*`, `*.pem`
- TOOLS.md shows token *types* but marks values as "(in memory - not in repo)"
- If a token is accidentally pushed, GitHub's secret scanning will catch it → re-create repo or rekey
- **Tokens live in my runtime memory only** — never in any file

---

## Business Progress (2026-03-13)

- **First customer prospect:** SDS-Mike on GitHub (Claude Code issue #2545) - has severe session memory loss problem
- **Domain curriculum:** 8 domains completed (B2B-SaaS, Consumer, Content/Creator, Crypto, AI Agents, SMB Automation, Memory Systems, Open Source)
- **Market positioning:** 58% SMBs use gen AI (up from 36%), 91% report positive ROI - new bottleneck is orchestration/governance

## SMB AI Market Research (2026-03-14)

- **Adoption:** 58% of SMBs now use generative AI (doubled from 2 years ago)
- **ROI:** 91% report positive ROI
- **Key shift:** From AI as drafting tool to AI agents that execute work
- **Top use cases:** Document classification, quote generation, customer support, HR screening, procurement matching, CRM management
- **API costs:** Down 90% from 2023-2026
- **Market timing:** Pre-configured agents replacing custom development

## Enterprise AI Adoption (2026-03-17)

- **50%+** enterprises have deployed agentic AI
- **Multi-agent systems** trending (federated MAS)
- **70%** of multiagent systems will have narrow-focused agents by 2027
- **Highest adoption:** IT ops, finance, employee service, coding (90% use AI)
- **By 2026:** 80% of enterprise apps will have AI copilots
- **SMB opportunity:** Labor-intensive services may adopt faster than enterprise

## Pricing Model - SINGLE MODEL (2026-03-17) ⚠️ CRITICAL

**OpenRouter-Style (Only Model):**
- **Software is FREE** - all features, no tiered pricing
- **Revenue comes from routing LLM calls**
- Users buy credits from us → We keep 5.5% fee (minimum $0.80 per purchase)
- We route to LLM providers at COST (no markup)
- OR users can BYOK (bring their own keys) → We charge 5% fee on provider costs
- **No subscriptions** - pay-as-you-go only

**Implication:** We are an LLM proxy/router, not a SaaS. Like OpenRouter, but self-hosted first.

---

## User Roles - TWO CLASSES (2026-03-17) ⚠️ CRITICAL

**ADMIN:**
- Controls spend
- Manages API keys
- Controls ALL users under their API keys
- Example: controls 100s of agents

**USER:**
- Uses agents
- Limited permissions
- Assigned by admin

**KEY INSIGHT:** An admin for ONE API key might be a USER for another.
- Same person: admin for work API key, user for personal API key
- Enables personal + work from same app
- Family accounts, business accounts

---

## Ecosystem - 6 Projects (2026-03-17)

| # | Project | Type | Status |
|---|---------|------|--------|
| 1 | Lipaira Server | Backend | ✅ Built |
| 2 | Lipaira Webapp | Platform | ✅ Built |
| 3 | Lipaira Desktop GUI | Platform | ✅ Built |
| 4 | Lipaira Client (Local) | Client | 🔲 Planned |
| 5 | Lipaira iOS App | Platform | 🔲 Planned |
| 6 | Lipaira Android App | Platform | 🔲 Planned |

**ALL CONNECTED** - Same agent, same API key, same data across all 6.

**WHY IMPOSSIBLE TO LEAVE:**
1. Your data/memory/agents are in the ecosystem
2. Switching = starting over (no export)
3. Cross-platform - same experience everywhere
4. Your agents know you - memory compounds

---

## Competitive Positioning (2026-03-14)

| Platform | Key Differentiator |
|----------|-------------------|
| OpenClaw | Free, open-source, CLI + basic web UI, persistent memory (weeks), no inner life |
| Claude Code | $20-200/mo, terminal only, session-based memory, coding-focused |
| **Lipaira** | Web-accessible self-hosted Agentic OS with Inner Life |

### OS vs SaaS Benefits
- Data ownership (on user's VPS, not ours)
- Privacy (nothing leaves their machine)
- Offline capability
- Full customization
- No ongoing subscription (one-time + API costs)
- Target: Privacy-sensitive professionals, enterprises, power users

## Philosophical Framework (2026-03-13)

- **Mean:** Virtue lies between excess and deficiency
- **Virtue as habit:** Character formed through repeated actions
- **Phronesis:** Practical wisdom for particular situations
- Source: Bible (Genesis), Plato (Republic), Aristotle (Nicomachean Ethics), Aquinas (Summa)

---

## Lipaira Compliance Infrastructure (2026-03-19)

**AWS Server:** 3.16.216.39 (not yet accessible - needs AWS console check)
**Rollout:** All code ready in `/data/.openclaw/workspace/lipaira-compliance/`

### Security Posture (Post-OpenClaw Vulnerability Disclosure)

**Context:** CVE-2026-25253 and other vulnerabilities disclosed March 2026:
- 135,000+ exposed OpenClaw instances
- 50,000+ vulnerable to RCE
- Command injection, LFI, prompt injection, malicious plugins

**Key Lessons Applied to Lipaira:**
- ⏳ Default to localhost binding (never 0.0.0.0)
- ⏳ Signed plugin/skills with hash verification
- ⏳ Sandboxed skill execution with limited permissions
- ⏳ Input sanitization enforced (already built)
- ⏳ Immutable audit logs (already designed)
- ⏳ KMS encryption for all credentials (already designed)
- ⏳ Memory sanitization before persistence

### Built Components:

**Logging (Audit Trail):**
- ✅ Structured log schema (`logging/schema.py`)
- ✅ OpenRouter consumption logging (`logging/openrouter.py`)
- ✅ S3 hash verification Lambda (`infrastructure/s3_hash_verification.py`)
- ✅ CloudWatch alerts config (`infrastructure/cloudwatch_alerts.py`)

**Database:**
- ✅ Transaction ledger SQL + Python (`database/transactions.py`)
- ✅ Stripe webhook audit storage (`database/stripe_webhook.py`)

**Accounting:**
- ✅ Revenue + COGS event streams (`accounting/revenue_cogs.py`)
- ✅ Reconciliation jobs + chargeback defense (`accounting/reconciliation.py`)

**Legal/Compliance:**
- ✅ GDPR data inventory + PII tagging (`legal/gdpr_inventory.py`)
- ✅ ToS version control + acceptance logging (`legal/tos_version_control.py`)
- ✅ DSR workflow (access/deletion/portability) (`legal/dsr_workflow.py`)
- ✅ Security + operational compliance (`legal/compliance_ops.py`)

**Infrastructure:**
- ✅ IAM policies (least privilege) + encryption config (`infrastructure/iam_policies.py`)

### Pending Founder Decisions (★):
- ~~Credit expiry policy~~ ✅ **DECIDED: Credits do NOT expire**
- ~~Refund policy~~ ✅ **DECIDED: Partial refund of unused credits only (5.5% fee absorbed/non-refundable)**
- Pricing: Customer gets $X credits, fee added on top ($X × 1.055), plus tax
- AUP content categories
- Data retention exceptions
- GDPR supervisory authority

### AWS Rollout Checklist:
1. ⏳ Enable S3 Object Lock (COMPLIANCE mode, 7-year retention)
2. ⏳ Create KMS keys for encryption
3. ⏳ Run database migrations (see `database/*.py`)
4. ⏳ Deploy IAM roles (see `infrastructure/iam_policies.py`)
5. ⏳ Configure CloudTrail
6. ⏳ Deploy Lambda functions (hash verification, monthly close)
7. ⏳ Set up CloudWatch alerts
8. ⏳ Configure SNS topic for alerts
9. ⏳ Test S3 Object Lock compliance mode

_Last updated: 2026-03-19_
