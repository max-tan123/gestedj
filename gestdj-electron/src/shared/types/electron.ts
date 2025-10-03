// Electron API types for renderer process
export interface ElectronAPI {
  // Python backend management
  startPythonBackend: () => Promise<{ success: boolean; message?: string; error?: string }>;
  stopPythonBackend: () => Promise<{ success: boolean; message?: string; error?: string }>;
  getPythonStatus: () => Promise<{ status: 'running' | 'stopped' }>;
  testWebSocketConnection: () => Promise<{ success: boolean; message?: string; error?: string }>;

  // Event listeners
  onPythonLog: (callback: (event: any, data: string) => void) => void;
  onPythonError: (callback: (event: any, data: string) => void) => void;
  onPythonStatus: (callback: (event: any, status: string) => void) => void;

  // Remove listeners
  removeAllListeners: (channel: string) => void;
}

export interface ElectronEnv {
  platform: string;
  arch: string;
  versions: NodeJS.ProcessVersions;
}

// Extend the global Window interface
declare global {
  interface Window {
    electronAPI: ElectronAPI;
    electronEnv: ElectronEnv;
  }
}