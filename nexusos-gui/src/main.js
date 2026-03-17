const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    frame: true,
    backgroundColor: '#0a0a0a',
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  mainWindow.loadFile(path.join(__dirname, 'src', 'index.html'));

  // Open DevTools in development
  if (process.argv.includes('--dev')) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

// IPC handlers for chat
ipcMain.handle('send-chat', async (event, message) => {
  // This will connect to the Nexus server
  const serverUrl = 'http://localhost:8080';
  const apiKey = 'sk-nexus--Fa54P_TP2h6q0oRiIu3qB9PVqZrZEyjGQ_E_KDglKs';
  
  try {
    const response = await fetch(`${serverUrl}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Nexus-Key': apiKey
      },
      body: JSON.stringify({ message })
    });
    return await response.json();
  } catch (error) {
    return { error: error.message };
  }
});

ipcMain.handle('get-models', async () => {
  const serverUrl = 'http://localhost:8080';
  const apiKey = 'sk-nexus--Fa54P_TP2h6q0oRiIu3qB9PVqZrZEyjGQ_E_KDglKs';
  
  try {
    const response = await fetch(`${serverUrl}/api/models`, {
      headers: { 'X-Nexus-Key': apiKey }
    });
    return await response.json();
  } catch (error) {
    return { error: error.message };
  }
});

ipcMain.handle('get-credits', async () => {
  const serverUrl = 'http://localhost:8080';
  const apiKey = 'sk-nexus--Fa54P_TP2h6q0oRiIu3qB9PVqZrZEyjGQ_E_KDglKs';
  
  try {
    const response = await fetch(`${serverUrl}/api/credits`, {
      headers: { 'X-Nexus-Key': apiKey }
    });
    return await response.json();
  } catch (error) {
    return { error: error.message };
  }
});

console.log('NexusOS GUI starting...');
