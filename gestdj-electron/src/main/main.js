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
      // Look for Python backend in gestdj-electron/python-backend/
      const pythonScript = join(__dirname, '../../python-backend/gesture_processor.py');
      const pythonCwd = join(__dirname, '../../python-backend');

      // Use bundled venv Python (for development)
      // TODO: Switch to PyInstaller binary for production builds
      const pythonExecutable = join(__dirname, '../../python-backend/venv/bin/python3');

      console.log('Starting Python backend:', pythonScript);
      console.log('Python executable:', pythonExecutable);
      console.log('Working directory:', pythonCwd);

      this.process = spawn(pythonExecutable, [pythonScript], {
        stdio: ['pipe', 'pipe', 'pipe'],  // Enable stdin piping
        cwd: pythonCwd
      });

      this.process.stdout.on('data', (data) => {
        const output = data.toString();
        console.log('Python stdout:', output);

        // Try to parse as JSON for gesture updates
        const lines = output.split('\n');
        lines.forEach(line => {
          if (line.trim()) {
            try {
              const parsed = JSON.parse(line);
              if (parsed.type === 'gesture_update') {
                // Send gesture update to renderer
                if (mainWindow) {
                  mainWindow.webContents.send('gesture-update', parsed);
                }
              }
            } catch (e) {
              // Not JSON, send as regular log
              if (mainWindow) {
                mainWindow.webContents.send('python-log', line);
              }
            }
          }
        });
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

// Handle landmark data from renderer
ipcMain.on('landmarks', (event, landmarkData) => {
  // Send to Python stdin
  if (pythonBackend.process && pythonBackend.isRunning) {
    try {
      pythonBackend.process.stdin.write(JSON.stringify(landmarkData) + '\n');
    } catch (error) {
      console.error('Failed to write to Python stdin:', error);
    }
  }
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