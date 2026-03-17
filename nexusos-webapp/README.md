# NexusOS Webapp

**Web-based dashboard for NexusOS**

## Features

- **Chat** - Talk to your AI agent with quality settings
- **Agents** - Manage your AI agents
- **Memory** - View memory system stats
- **Skills** - Enable/disable skills and tools
- **Usage** - View usage statistics and costs
- **Settings** - Configure default model, auto-route, buy credits

## Tech Stack

- Vanilla JavaScript (no framework)
- CSS Grid + Flexbox
- Connects to Nexus Server API

## Running

```bash
# Install
npm install

# Run
npx serve src

# Or open src/index.html directly in browser
```

## API Connection

Update API_URL in app.js to point to your Nexus Server:
```javascript
const API_URL = 'http://localhost:8080/api';
```

## Mobile Ready

This webapp is responsive and works on mobile browsers. For a native experience, see:
- nexusos-ios/ (iOS app)
- nexusos-android/ (Android app)
