# NexusOS GUI

**Tile-based iOS-style desktop interface for NexusOS**

## Screen Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  ⬜⬜⬜ LEFT 1/3          │        RIGHT 2/3                   │
│  Chat / Prompt Area    │    App Dock + Launcher              │
│  (paper white/charcoal)│    (iOS-style tiles)                 │
│                        │                                      │
│  [ Type commands... ]  │   ┌────┐ ┌────┐ ┌────┐ ┌────┐       │
│                        │   │Chat│ │Agents│ │Files│ │Code│     │
│                        │   └────┘ └────┘ └────┘ └────┘       │
│                        │   ┌────┐ ┌────┐ ┌────┐ ┌────┐       │
│   [💬] (toggle)        │   │Term │ │Memory│ │Skills│ │⚙️ │     │
│                        │   └────┘ └────┘ └────┘ └────┘       │
└─────────────────────────────────────────────────────────────────┘
```

## Features

- **Chat-first design**: Left panel always has AI chat accessible
- **Tile-based apps**: iOS-style grid of app tiles on the right
- **Fullscreen apps**: Apps can expand to cover everything
- **One-click chat**: Always return to chat with one button press

## Running

```bash
# Install dependencies
npm install

# Run in development
npm start

# Build for production
npm run build
```

## Tech Stack

- Electron 28+
- Vanilla JavaScript (no frameworks)
- CSS Grid for tile layout

## Connecting to Server

The GUI connects to `http://localhost:8080` by default.
Update `main.js` to point to your Nexus Server URL.
