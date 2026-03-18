# NexusOS Web Dashboard — Your AI Command Center

**Beautiful web interface for managing your enterprise AI agents**

> **Stop building in the dark.** See your AI agents, their memory, and usage statistics in one elegant dashboard. No more CLI guessing games.

## Why This Matters

**Traditional AI tools** force you to build blind. You send prompts, get responses, and have zero visibility into what's actually happening.

**NexusOS Web Dashboard** changes everything:
- **Visual management** of all your AI agents
- **Real-time memory** monitoring and insights
- **Usage analytics** to optimize performance
- **One-click deployment** of new agents and skills

## Key Benefits

### 🧠 **Memory Transparency**
See exactly how your agents learn and remember. Monitor memory usage, search through conversations, and ensure context is being built properly.

### 🤖 **Agent Management Made Simple**
Deploy, configure, and monitor multiple AI agents from one dashboard. Set quality preferences, manage API usage, and track performance metrics.

### 📊 **Usage Analytics & Cost Control**
Track token usage, API costs, and performance metrics. Set budgets, monitor efficiency, and optimize your AI infrastructure spending.

### 🔧 **Zero-Friction Configuration**
Change models, enable/disable skills, and configure behavior without touching code. Perfect for teams and non-technical stakeholders.

### 📱 **Mobile-Ready**
Access your AI command center from anywhere. Responsive design works perfectly on phones, tablets, and desktop.

## What You Get

- **Chat Interface** — Talk to your agents with quality controls
- **Agent Management** — Deploy and configure multiple AI agents
- **Memory Explorer** — Search through your agents' memory and context
- **Skills Marketplace** — Enable/disable tools and integrations
- **Usage Dashboard** — Monitor performance, costs, and efficiency
- **Settings Panel** — Configure models, API keys, and preferences

## Quick Start (2 Minutes)

```bash
# Clone and start the dashboard
git clone https://github.com/nexusos-ai/web-dashboard.git
cd web-dashboard

# Install dependencies
npm install

# Connect to your NexusOS server
# Update API_URL in app.js to point to your server:
# const API_URL = 'http://localhost:8080/api';

# Start the development server
npm start

# Open http://localhost:3000
```

## Production Deployment

For production use, build the optimized version:

```bash
# Build for production
npm run build

# Deploy the dist/ folder to your web server
# The dashboard connects to your NexusOS server at:
# http://your-nexusos-server:8080/api
```

## API Connection

The dashboard connects to your NexusOS server via REST API:

- **Default connection:** `http://localhost:8080/api`
- **Authentication:** API key-based auth (configurable)
- **Real-time updates:** WebSocket connections for live data

Update the API configuration in `src/js/config.js` to connect to your server.

## Tech Stack

- **Frontend:** Vanilla JavaScript (no frameworks = fast)
- **Styling:** CSS Grid + Flexbox (responsive by design)
- **Backend:** Connects to NexusOS server API
- **Mobile:** Fully responsive, works on all devices

## Perfect For

- **Development teams** who want visibility into AI agent behavior
- **Managers** who need to monitor usage and costs
- **Enterprises** requiring audit trails and compliance reporting
- **Researchers** studying AI agent memory and learning patterns

## Why Not Just Use CLI?

**CLI tools are great for developers, but terrible for everyone else.**

The web dashboard gives your entire team:
- **Visual insights** into AI performance
- **Easy configuration** without code changes
- **Team collaboration** with shared access
- **Compliance reporting** with audit trails

---

**Ready to see your AI agents in action?** [Deploy NexusOS](https://docs.nexusos.cloud) and start using the web dashboard today.

**Questions?** [Join our community](https://github.com/nexusos-ai) or [email us](mailto:hello@nexusos.cloud).