// NexusOS GUI Renderer

// App definitions
const APPS = [
  { id: 'chat', name: 'Chat', icon: '💬', description: 'AI Chat Interface' },
  { id: 'agents', name: 'Agents', icon: '🤖', description: 'Manage your AI agents' },
  { id: 'files', name: 'Files', icon: '📁', description: 'File browser' },
  { id: 'code', name: 'Code', icon: '💻', description: 'Code editor' },
  { id: 'terminal', name: 'Terminal', icon: '⬛', description: 'Command terminal' },
  { id: 'memory', name: 'Memory', icon: '🧠', description: 'Knowledge & memories' },
  { id: 'skills', name: 'Skills', icon: '🛠️', description: 'Tools & integrations' },
  { id: 'settings', name: 'Settings', icon: '⚙️', description: 'Configuration' },
  { id: 'web', name: 'Web', icon: '🌐', description: 'Web browser' },
  { id: 'notes', name: 'Notes', icon: '📝', description: 'Quick notes' },
  { id: 'calendar', name: 'Calendar', icon: '📅', description: 'Schedule' },
  { id: 'mail', name: 'Mail', icon: '📧', description: 'Email client' },
];

// State
let chatVisible = true;
let appViewVisible = false;
let messageHistory = [];

// DOM Elements
const chatPanel = document.getElementById('chatPanel');
const chatToggle = document.getElementById('chatToggle');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const chatMessages = document.getElementById('chatMessages');
const creditsEl = document.getElementById('credits');
const appGrid = document.getElementById('appGrid');
const appView = document.getElementById('appView');
const appTitle = document.getElementById('appTitle');
const appContent = document.getElementById('appContent');
const backBtn = document.getElementById('backBtn');
const fullscreenBtn = document.getElementById('fullscreenBtn');
const appPanel = document.getElementById('appPanel');

// Initialize
async function init() {
  renderAppGrid();
  setupEventListeners();
  await loadCredits();
  addMessage('system', 'NexusOS is ready. Type a command or tap an app tile.');
}

function renderAppGrid() {
  appGrid.innerHTML = APPS.map(app => `
    <div class="app-tile" data-app="${app.id}">
      <span class="icon">${app.icon}</span>
      <span class="name">${app.name}</span>
    </div>
  `).join('');
  
  // Add click handlers
  document.querySelectorAll('.app-tile').forEach(tile => {
    tile.addEventListener('click', () => openApp(tile.dataset.app));
  });
}

function setupEventListeners() {
  // Chat toggle
  chatToggle.addEventListener('click', toggleChat);
  
  // Send message
  sendBtn.addEventListener('click', sendMessage);
  chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
  });
  
  // Fullscreen toggle
  fullscreenBtn.addEventListener('click', toggleFullscreen);
  
  // Back button
  backBtn.addEventListener('click', closeApp);
}

function toggleChat() {
  chatVisible = !chatVisible;
  chatPanel.classList.toggle('collapsed', !chatVisible);
  chatToggle.textContent = chatVisible ? '💬' : '👁️';
}

function toggleFullscreen() {
  appPanel.classList.toggle('fullscreen');
  fullscreenBtn.textContent = appPanel.classList.contains('fullscreen') ? '⛶' : '⛶';
}

async function sendMessage() {
  const message = chatInput.value.trim();
  if (!message) return;
  
  // Add user message
  addMessage('user', message);
  chatInput.value = '';
  
  // Show typing indicator
  const typingMsg = addMessage('system', 'Thinking...');
  
  try {
    // Send to Nexus server
    const response = await window.electronAPI.sendChat(message);
    
    // Remove typing indicator
    typingMsg.remove();
    
    if (response.content) {
      addMessage('system', response.content);
    } else if (response.error) {
      addMessage('error', `Error: ${response.error}`);
    }
  } catch (error) {
    typingMsg.remove();
    addMessage('error', `Connection error: ${error.message}`);
  }
}

function addMessage(role, content) {
  const div = document.createElement('div');
  div.className = `message ${role}`;
  div.innerHTML = `<span class="role">${role === 'user' ? 'You:' : 'NexusOS:'}</span><span class="content">${content}</span>`;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return div;
}

async function loadCredits() {
  try {
    const response = await window.electronAPI.getCredits();
    creditsEl.textContent = `Credits: ${response.credits || 0}`;
  } catch (error) {
    creditsEl.textContent = 'Credits: --';
  }
}

function openApp(appId) {
  const app = APPS.find(a => a.id === appId);
  if (!app) return;
  
  appTitle.textContent = app.name;
  appViewVisible = true;
  appView.style.display = 'flex';
  
  // Load app content
  loadAppContent(appId);
}

function closeApp() {
  appViewVisible = false;
  appView.style.display = 'none';
}

function loadAppContent(appId) {
  const contents = {
    chat: `
      <div style="padding: 20px;">
        <p>Chat is always available in the left panel!</p>
        <p style="margin-top: 20px; color: #888;">Toggle chat with the 💬 button.</p>
      </div>
    `,
    agents: `
      <div style="padding: 20px;">
        <h3>Your Agents</h3>
        <div style="margin-top: 20px; color: #888;">
          <p>🤖 Assistant - Always running</p>
          <p>🔍 Researcher - Idle</p>
          <p>✍️ Writer - Idle</p>
        </div>
      </div>
    `,
    settings: `
      <div style="padding: 20px;">
        <h3>Settings</h3>
        <div style="margin-top: 20px;">
          <label style="display: block; margin-bottom: 10px;">
            <input type="checkbox" checked> Auto-route to best model
          </label>
          <label style="display: block; margin-bottom: 10px;">
            <input type="checkbox"> Sound effects
          </label>
          <label style="display: block; margin-bottom: 10px;">
            <input type="checkbox" checked> Show system notifications
          </label>
        </div>
      </div>
    `,
    memory: `
      <div style="padding: 20px;">
        <h3>Memory System</h3>
        <p style="color: #888; margin-top: 10px;">Semantic memories: 127</p>
        <p style="color: #888;">Episodic memories: 342</p>
        <p style="color: #888;">Working context: Active</p>
      </div>
    `,
    terminal: `
      <div style="background: #000; padding: 20px; font-family: monospace; height: 100%;">
        <p style="color: #0f0;">nexusos@local:~$ <span style="color: #fff;">_</span></p>
      </div>
    `
  };
  
  appContent.innerHTML = contents[appId] || `
    <div style="padding: 20px;">
      <h3>${APPS.find(a => a.id === appId)?.name || 'App'}</h3>
      <p style="color: #888; margin-top: 10px;">Coming soon!</p>
    </div>
  `;
}

// Expose to window for IPC (works in Electron context)
const { ipcRenderer } = require('electron');
window.electronAPI = {
  sendChat: (message) => ipcRenderer.invoke('send-chat', message),
  getModels: () => ipcRenderer.invoke('get-models'),
  getCredits: () => ipcRenderer.invoke('get-credits')
};

// Wait for DOM
document.addEventListener('DOMContentLoaded', init);
