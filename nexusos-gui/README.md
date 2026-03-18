# NexusOS Desktop — Beautiful AI for Your Desktop

**Tile-based iOS-style interface for managing your enterprise AI agents**

> **Finally, AI that looks as good as it performs.** NexusOS Desktop brings the full power of your AI agents to a beautiful, intuitive interface inspired by iOS.

## Why NexusOS Desktop?

**Most AI tools are either:**
- Powerful but ugly (CLI tools)
- Pretty but limited (web chatbots)

**NexusOS Desktop is different:**
- Beautiful iOS-style tile interface
- Full access to all AI agent features
- Persistent chat always one click away
- Built for power users who demand aesthetics

## What Makes It Special

### 🎯 **Chat-First Design**
The left panel is *always* your AI agent. No hunting through menus—just type and talk. Your conversation is always accessible.

### 🧱 **Tile-Based Launcher**
Right panel shows your available apps as beautiful tiles. One click to open any agent, tool, or feature. iOS-inspired, reimagined for AI.

### 🔄 **Instant Context Switching**
Apps can expand to fullscreen, but you're never more than one click away from your chat. Context switches in milliseconds.

### 🎨 **Designed for Developers**
Under the beautiful exterior: full API access, custom styling, keyboard shortcuts, and automation support.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  ⬡ NexusOS Desktop                              [─] [□] [×]   │
├───────────────────┬─────────────────────────────────────────────┤
│                   │                                             │
│  💬 Chat          │    ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │
│                   │    │ Chat │ │Agents│ │Memory│ │Skills│   │
│  [ AI Response   ]│    └──────┘ └──────┘ └──────┘ └──────┘   │
│    appears here   │                                             │
│                   │    ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │
│  ─────────────── │    │ Term │ │Files │ │ Code │ │Settings│  │
│                   │    └──────┘ └──────┘ └──────┘ └──────┘   │
│  [ Type message..]│                                             │
│                   │                                             │
│  [💬] Return      │         Click any tile to open             │
│      to chat      │                                             │
│                   │                                             │
└───────────────────┴─────────────────────────────────────────────┘
```

## Installation

```bash
# Clone the repository
git clone https://github.com/nexusos-ai/desktop.git
cd desktop

# Install dependencies
npm install

# Run in development mode
npm start

# Build for production
npm run build

# Launch the desktop app
open dist/NexusOS-Desktop.app
```

## Connect to NexusOS

The desktop app connects to your NexusOS server:

- **Default:** `http://localhost:8080`
- **Configure:** Update `serverUrl` in `src/main.js`

```javascript
// In src/main.js
const serverUrl = 'http://your-nexusos-server:8080';
```

## Features at a Glance

| Tile | Function |
|------|----------|
| 💬 Chat | Direct conversation with your AI agent |
| 🤖 Agents | Manage multiple specialized agents |
| 🧠 Memory | Visualize and search agent memory |
| 🛠️ Skills | Enable/disable tools and integrations |
| 📟 Terminal | Command-line access |
| 📁 Files | File management and uploads |
| ⚙️ Settings | Configure behavior and preferences |

## Perfect For

- **Developers** who want beautiful tooling
- **Teams** collaborating on AI projects
- **Power users** who spend all day in AI interfaces
- **Enterprises** requiring polished, branded experiences

## Why Not Web-Only?

**Web apps are great, but desktop apps offer:**

- **Offline capability** when you need it
- **System integration** (notifications, shortcuts, tray)
- **Better performance** for real-time updates
- **Native feel** your team will love

---

**Ready to elevate your AI workflow?** [Deploy NexusOS](https://docs.nexusos.cloud) and pair it with NexusOS Desktop.

**Contributing:** We welcome contributions! See [GitHub](https://github.com/nexusos-ai) for development guidelines.

**Questions?** [Join our Discord](https://discord.gg/nexusos) or [email us](mailto:hello@nexusos.cloud).