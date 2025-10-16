const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // Python backend management
  startPythonBackend: () => ipcRenderer.invoke('start-python-backend'),
  stopPythonBackend: () => ipcRenderer.invoke('stop-python-backend'),
  getPythonStatus: () => ipcRenderer.invoke('get-python-status'),
  testWebSocketConnection: () => ipcRenderer.invoke('test-websocket-connection'),

  // Landmark communication
  sendLandmarks: (landmarkData) => ipcRenderer.send('landmarks', landmarkData),

  // Event listeners
  onPythonLog: (callback) => ipcRenderer.on('python-log', callback),
  onPythonError: (callback) => ipcRenderer.on('python-error', callback),
  onPythonStatus: (callback) => ipcRenderer.on('python-status', callback),
  onGestureUpdate: (callback) => ipcRenderer.on('gesture-update', callback),

  // Remove listeners
  removeAllListeners: (channel) => ipcRenderer.removeAllListeners(channel),
});

// Expose environment info
contextBridge.exposeInMainWorld('electronEnv', {
  platform: process.platform,
  arch: process.arch,
  versions: process.versions,
});