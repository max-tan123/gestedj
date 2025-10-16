// Type definitions for Electron IPC API

interface LandmarkData {
  type: 'landmarks';
  timestamp: number;
  hands: {
    Left?: Array<{ x: number; y: number; z: number }>;
    Right?: Array<{ x: number; y: number; z: number }>;
  };
}

interface GestureUpdate {
  type: 'gesture_update';
  deck: number;
  fingers: number;
  gesture: string;
  value: number;
  angle?: number;
}

interface ElectronAPI {
  // Python backend management
  startPythonBackend: () => Promise<{ success: boolean; message?: string; error?: string }>;
  stopPythonBackend: () => Promise<{ success: boolean; message?: string; error?: string }>;
  getPythonStatus: () => Promise<{ status: 'running' | 'stopped' | 'unknown' }>;
  testWebSocketConnection: () => Promise<{ success: boolean; message?: string; error?: string }>;

  // Landmark communication
  sendLandmarks: (landmarkData: LandmarkData) => void;

  // Event listeners
  onPythonLog: (callback: (event: any, data: string) => void) => void;
  onPythonError: (callback: (event: any, data: string) => void) => void;
  onPythonStatus: (callback: (event: any, status: string) => void) => void;
  onGestureUpdate: (callback: (event: any, data: GestureUpdate) => void) => void;

  // Remove listeners
  removeAllListeners: (channel: string) => void;
}

interface ElectronEnv {
  platform: string;
  arch: string;
  versions: any;
}

declare global {
  interface Window {
    electronAPI: ElectronAPI;
    electronEnv: ElectronEnv;
  }
}

export {};
