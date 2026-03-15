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

## Competitive Positioning (2026-03-14)

| Platform | Key Differentiator |
|----------|-------------------|
| OpenClaw | Free, open-source, CLI + basic web UI, persistent memory (weeks), no inner life |
| Claude Code | $20-200/mo, terminal only, session-based memory, coding-focused |
| **NexusOS** | Web-accessible self-hosted Agentic OS with Inner Life |

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

_Last updated: 2026-03-14_
