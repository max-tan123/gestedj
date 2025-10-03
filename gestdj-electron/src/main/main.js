const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const { join } = require('path');
const WebSocket = require('ws');

// Keep a global reference of the window object
let mainWindow;
let pythonProcess = null;
let wsServer = null;

// Python backend management
class PythonBackend {
  constructor() {
    this.process = null;
    this.isRunning = false;
  }

  async start() {
    if (this.isRunning) {
      return 'Backend already running';
    }

    try {
      // Look for Python backend in parent directory
      const pythonScript = join(__dirname, '../../../gestdj-web-ui/app.py');

      this.process = spawn('python3', [pythonScript], {
        stdio: ['ignore', 'pipe', 'pipe'],
        cwd: join(__dirname, '../../../gestdj-web-ui')
      });

      this.process.stdout.on('data', (data) => {
        console.log('Python stdout:', data.toString());
        // Send updates to renderer
        if (mainWindow) {
          mainWindow.webContents.send('python-log', data.toString());
        }
      });

      this.process.stderr.on('data', (data) => {
        console.error('Python stderr:', data.toString());
        if (mainWindow) {
          mainWindow.webContents.send('python-error', data.toString());
        }
      });

      this.process.on('close', (code) => {
        console.log(`Python process exited with code ${code}`);
        this.isRunning = false;
        if (mainWindow) {
          mainWindow.webContents.send('python-status', 'stopped');
        }
      });

      this.isRunning = true;
      return 'Python backend started successfully';
    } catch (error) {
      console.error('Failed to start Python backend:', error);
      throw new Error(`Failed to start Python backend: ${error.message}`);
    }
  }

  stop() {
    if (this.process && this.isRunning) {
      this.process.kill('SIGTERM');
      this.isRunning = false;
      return 'Python backend stopped';
    }
    return 'Backend was not running';
  }

  getStatus() {
    return this.isRunning ? 'running' : 'stopped';
  }
}

const pythonBackend = new PythonBackend();

function createWindow() {
  // Create the browser window
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: join(__dirname, 'preload.js')
    },
    titleBarStyle: 'hiddenInset',
    show: false, // Don't show until ready
  });

  // Load the app
  const isDev = process.env.NODE_ENV === 'development';

  if (isDev) {
    mainWindow.loadURL('http://localhost:3000');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(join(__dirname, '../../build/renderer/index.html'));
  }

  // Show window when ready to prevent visual flash
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// App event handlers
app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  // Stop Python backend when app closes
  pythonBackend.stop();

  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

// IPC handlers
ipcMain.handle('start-python-backend', async () => {
  try {
    const result = await pythonBackend.start();
    return { success: true, message: result };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

ipcMain.handle('stop-python-backend', () => {
  const result = pythonBackend.stop();
  return { success: true, message: result };
});

ipcMain.handle('get-python-status', () => {
  return { status: pythonBackend.getStatus() };
});

ipcMain.handle('test-websocket-connection', async () => {
  return new Promise((resolve) => {
    try {
      const ws = new WebSocket('ws://localhost:8765');

      ws.on('open', () => {
        ws.close();
        resolve({ success: true, message: 'WebSocket connection successful' });
      });

      ws.on('error', (error) => {
        resolve({ success: false, error: error.message });
      });

      // Timeout after 5 seconds
      setTimeout(() => {
        if (ws.readyState === WebSocket.CONNECTING) {
          ws.terminate();
          resolve({ success: false, error: 'Connection timeout' });
        }
      }, 5000);
    } catch (error) {
      resolve({ success: false, error: error.message });
    }
  });
});

// Handle app shutdown
process.on('SIGINT', () => {
  pythonBackend.stop();
  app.quit();
});

process.on('SIGTERM', () => {
  pythonBackend.stop();
  app.quit();
});