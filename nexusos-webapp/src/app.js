// NexusOS Webapp - Main Application

// Use the correct API endpoint
const API_URL = 'http://187.124.150.225:8080/api';
let currentUser = null;
let accessToken = localStorage.getItem('nexus_access_token') || '';

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
  if (accessToken) {
    try {
      const response = await fetch(`${API_URL}/usage`, {
        headers: { 'Authorization': `Bearer ${accessToken}` }
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
    
    if (data.access_token) {
      accessToken = data.access_token;
      localStorage.setItem('nexus_access_token', accessToken);
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
      body: JSON.stringify({ email, password, name: email.split('@')[0] })
    });
    
    const data = await response.json();
    
    if (data.access_token) {
      accessToken = data.access_token;
      localStorage.setItem('nexus_access_token', accessToken);
      alert('Account created!');
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
  // Not supported in this version - use email/password
  alert('Please use email and password to login');
}

function logout() {
  accessToken = '';
  localStorage.removeItem('nexus_access_token');
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
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify({ message })
    });
    
    const data = await response.json();
    typing.remove();
    
    if (data.response) {
      addMessage('system', data.response);
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
    // Load usage (includes cost info)
    const usageRes = await fetch(`${API_URL}/usage`, {
      headers: { 'Authorization': `Bearer ${accessToken}` }
    });
    const usageData = await usageRes.json();
    
    document.getElementById('navCredits').textContent = usageData.summary?.total_requests || '0';
    
    // Load agents
    const agentsRes = await fetch(`${API_URL}/agents`, {
      headers: { 'Authorization': `Bearer ${accessToken}` }
    });
    const agentsData = await agentsRes.json();
    
  } catch (e) {
    console.error('Error loading user data:', e);
  }
}

async function loadUsage() {
  try {
    const response = await fetch(`${API_URL}/usage`, {
      headers: { 'Authorization': `Bearer ${accessToken}` }
    });
    const data = await response.json();
    
    // Update summary
    document.getElementById('totalRequests').textContent = data.summary?.total_requests || 0;
    document.getElementById('totalTokens').textContent = (data.summary?.total_tokens || 0).toLocaleString();
    document.getElementById('totalCost').textContent = '$' + (data.summary?.total_cost_usd || 0).toFixed(4);
    
  } catch (e) {
    console.error('Error loading usage:', e);
  }
}

async function loadSettings() {
  document.getElementById('settingsEmail').textContent = document.getElementById('loginEmail').value || 'User';
  document.getElementById('settingsApiKey').textContent = accessToken.substring(0, 20) + '...';
}

function copyApiKey() {
  navigator.clipboard.writeText(accessToken);
  alert('Token copied!');
}

async function buyCredits() {
  alert('Credit purchase coming soon!');
}

console.log('NexusOS Webapp loaded');
