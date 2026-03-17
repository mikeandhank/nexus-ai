// NexusOS Webapp - Main Application

const API_URL = 'http://187.124.150.225:8080/api';
let currentUser = null;
let apiKey = localStorage.getItem('nexus_api_key') || '';

// DOM Elements
const loginScreen = document.getElementById('loginScreen');
const dashboardScreen = document.getElementById('dashboardScreen');
const pages = document.querySelectorAll('.page');
const navItems = document.querySelectorAll('.nav-item');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  checkAuth();
});

function initEventListeners() {
  // Login
  document.getElementById('loginBtn').addEventListener('click', login);
  document.getElementById('registerBtn').addEventListener('click', register);
  document.getElementById('apiKeyBtn').addEventListener('click', loginWithApiKey);
  
  // Chat
  document.getElementById('sendBtn').addEventListener('click', sendMessage);
  document.getElementById('chatInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
  });
  
  // Navigation
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const page = item.dataset.page;
      if (page) navigateTo(page);
    });
  });
  
  // Logout
  document.getElementById('logoutBtn').addEventListener('click', logout);
  
  // Settings
  document.getElementById('defaultModel').addEventListener('change', updateConfig);
  document.getElementById('autoRoute').addEventListener('change', updateConfig);
  document.getElementById('copyKeyBtn').addEventListener('click', copyApiKey);
  document.getElementById('buyCreditsBtn').addEventListener('click', buyCredits);
}

// Auth
async function checkAuth() {
  if (apiKey) {
    try {
      const response = await fetch(`${API_URL}/config`, {
        headers: { 'X-Nexus-Key': apiKey }
      });
      if (response.ok) {
        showDashboard();
        loadUserData();
      }
    } catch (e) {
      console.log('Auth check failed:', e);
    }
  }
}

async function login() {
  const email = document.getElementById('loginEmail').value;
  const password = document.getElementById('loginPassword').value;
  
  try {
    const response = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    
    const data = await response.json();
    
    if (data.api_key) {
      apiKey = data.api_key;
      localStorage.setItem('nexus_api_key', apiKey);
      showDashboard();
      loadUserData();
    } else {
      alert(data.error || 'Login failed');
    }
  } catch (e) {
    alert('Connection error: ' + e.message);
  }
}

async function register() {
  const email = document.getElementById('loginEmail').value;
  const password = document.getElementById('loginPassword').value;
  
  try {
    const response = await fetch(`${API_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    
    const data = await response.json();
    
    if (data.api_key) {
      apiKey = data.api_key;
      localStorage.setItem('nexus_api_key', apiKey);
      alert(`Account created! You have ${data.credits} free credits.`);
      showDashboard();
      loadUserData();
    } else {
      alert(data.error || 'Registration failed');
    }
  } catch (e) {
    alert('Connection error: ' + e.message);
  }
}

function loginWithApiKey() {
  const key = document.getElementById('apiKeyInput').value.trim();
  if (!key) return alert('Please enter an API key');
  
  apiKey = key;
  localStorage.setItem('nexus_api_key', apiKey);
  showDashboard();
  loadUserData();
}

function logout() {
  apiKey = '';
  localStorage.removeItem('nexus_api_key');
  loginScreen.classList.remove('hidden');
  dashboardScreen.classList.add('hidden');
}

function showDashboard() {
  loginScreen.classList.add('hidden');
  dashboardScreen.classList.remove('hidden');
  navigateTo('chat');
}

// Navigation
function navigateTo(page) {
  pages.forEach(p => p.classList.remove('active'));
  navItems.forEach(n => n.classList.remove('active'));
  
  document.getElementById(`${page}Page`).classList.add('active');
  document.querySelector(`[data-page="${page}"]`)?.classList.add('active');
  
  // Load page data
  if (page === 'usage') loadUsage();
  if (page === 'settings') loadSettings();
}

// Chat
async function sendMessage() {
  const input = document.getElementById('chatInput');
  const message = input.value.trim();
  if (!message) return;
  
  const quality = document.getElementById('modelSelect').value;
  
  // Add user message
  addMessage('user', message);
  input.value = '';
  
  // Show typing
  const typing = addMessage('system', 'Thinking...');
  
  try {
    const response = await fetch(`${API_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Nexus-Key': apiKey
      },
      body: JSON.stringify({ message, quality })
    });
    
    const data = await response.json();
    typing.remove();
    
    if (data.content) {
      addMessage('system', data.content);
    } else if (data.error) {
      addMessage('error', data.error);
    }
  } catch (e) {
    typing.remove();
    addMessage('error', 'Connection error: ' + e.message);
  }
}

function addMessage(role, content) {
  const container = document.getElementById('chatMessages');
  const div = document.createElement('div');
  div.className = `message ${role}`;
  div.innerHTML = `<span class="role">${role === 'user' ? 'You:' : 'NexusOS:'}</span><span class="content">${content}</span>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

// User Data
async function loadUserData() {
  try {
    // Load credits
    const creditsRes = await fetch(`${API_URL}/credits`, {
      headers: { 'X-Nexus-Key': apiKey }
    });
    const creditsData = await creditsRes.json();
    document.getElementById('navCredits').textContent = creditsData.credits?.toFixed(2) || '0';
    
    // Load config
    const configRes = await fetch(`${API_URL}/config`, {
      headers: { 'X-Nexus-Key': apiKey }
    });
    const configData = await configRes.json();
    
    document.getElementById('defaultModel').value = configData.quality_preference || 'balanced';
    document.getElementById('autoRoute').checked = configData.auto_route !== false;
    
  } catch (e) {
    console.error('Error loading user data:', e);
  }
}

async function loadUsage() {
  try {
    const response = await fetch(`${API_URL}/usage?days=30`, {
      headers: { 'X-Nexus-Key': apiKey }
    });
    const data = await response.json();
    
    // Update summary
    document.getElementById('totalRequests').textContent = data.usage?.length || 0;
    
    let totalTokens = 0;
    let totalCost = 0;
    
    if (data.usage) {
      data.usage.forEach(u => {
        totalTokens += (u.input_tokens || 0) + (u.output_tokens || 0);
        totalCost += u.cost || 0;
      });
    }
    
    document.getElementById('totalTokens').textContent = totalTokens.toLocaleString();
    document.getElementById('totalCost').textContent = '$' + totalCost.toFixed(2);
    
    // Update table
    const tbody = document.getElementById('usageTableBody');
    tbody.innerHTML = '';
    
    if (data.usage) {
      data.usage.slice(0, 20).forEach(u => {
        const row = document.createElement('tr');
        row.innerHTML = `
          <td>${new Date(u.created_at).toLocaleDateString()}</td>
          <td>${u.model}</td>
          <td>${u.provider}</td>
          <td>${(u.input_tokens || 0) + (u.output_tokens || 0)}</td>
          <td>$${(u.cost || 0).toFixed(4)}</td>
        `;
        tbody.appendChild(row);
      });
    }
  } catch (e) {
    console.error('Error loading usage:', e);
  }
}

async function loadSettings() {
  document.getElementById('settingsApiKey').textContent = apiKey.substring(0, 20) + '...';
}

async function updateConfig() {
  const quality = document.getElementById('defaultModel').value;
  const autoRoute = document.getElementById('autoRoute').checked;
  
  try {
    await fetch(`${API_URL}/config`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-Nexus-Key': apiKey
      },
      body: JSON.stringify({
        quality_preference: quality,
        auto_route: autoRoute
      })
    });
  } catch (e) {
    console.error('Error updating config:', e);
  }
}

function copyApiKey() {
  navigator.clipboard.writeText(apiKey);
  alert('API key copied!');
}

async function buyCredits() {
  const amount = prompt('Enter amount to spend (minimum $5):', '10');
  if (!amount || parseFloat(amount) < 5) return;
  
  try {
    const response = await fetch(`${API_URL}/credits/purchase`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Nexus-Key': apiKey
      },
      body: JSON.stringify({ amount: parseFloat(amount) })
    });
    
    const data = await response.json();
    
    if (data.new_balance !== undefined) {
      alert(`Purchased $${data.credits_added.toFixed(2)} credits! New balance: ${data.new_balance.toFixed(2)}`);
      loadUserData();
    } else {
      alert(data.error || 'Purchase failed');
    }
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

console.log('NexusOS Webapp loaded');
