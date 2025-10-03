/**
 * @fileoverview Main Module Index for GesteDJ Web UI
 *
 * This file provides centralized exports for all modules in the frontend,
 * making it easy to import components, services, and utilities throughout
 * the application.
 *
 * @author GesteDJ Team
 * @version 1.0.0
 */

// ========================================
// Type Definitions
// ========================================
export * from './types';

// ========================================
// Services
// ========================================
export { WebSocketService, createWebSocketService } from './services/websocket';
export { CameraService, createCameraService } from './services/camera';

// ========================================
// React Hooks
// ========================================
export {
  useWebSocket,
  useLatencyTest,
  useBackendConnection
} from './hooks/useWebSocket';

export {
  useCamera,
  useVideoCapture
} from './hooks/useCamera';

// ========================================
// React Components
// ========================================
export {
  VideoDisplay,
  VideoComparison
} from './components/VideoDisplay';

export {
  ConnectionStatus,
  ConnectionIndicator
} from './components/ConnectionStatus';

// ========================================
// Utility Functions
// ========================================

/**
 * Convert base64 string to Uint8Array
 */
export function base64ToUint8Array(base64: string): Uint8Array {
  const binaryString = window.atob(base64);
  const len = binaryString.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes;
}

/**
 * Convert Uint8Array to base64 string
 */
export function uint8ArrayToBase64(uint8Array: Uint8Array): string {
  let binaryString = '';
  const len = uint8Array.byteLength;
  for (let i = 0; i < len; i++) {
    binaryString += String.fromCharCode(uint8Array[i]);
  }
  return window.btoa(binaryString);
}

/**
 * Format latency value with appropriate color coding
 */
export function formatLatency(latency: number): {
  value: string;
  color: string;
  emoji: string;
} {
  const value = `${latency.toFixed(1)}ms`;

  if (latency < 20) {
    return { value, color: '#4CAF50', emoji: '🟢' };
  } else if (latency < 30) {
    return { value, color: '#FF9800', emoji: '🟡' };
  } else {
    return { value, color: '#f44336', emoji: '🔴' };
  }
}

/**
 * Generate unique ID for components
 */
export function generateId(prefix: string = 'gestdj'): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Throttle function calls
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: NodeJS.Timeout | null = null;
  let lastExecTime = 0;

  return (...args: Parameters<T>) => {
    const currentTime = Date.now();

    if (currentTime - lastExecTime > delay) {
      func(...args);
      lastExecTime = currentTime;
    } else {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }

      timeoutId = setTimeout(() => {
        func(...args);
        lastExecTime = Date.now();
        timeoutId = null;
      }, delay - (currentTime - lastExecTime));
    }
  };
}

/**
 * Debounce function calls
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: NodeJS.Timeout | null = null;

  return (...args: Parameters<T>) => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }

    timeoutId = setTimeout(() => {
      func(...args);
      timeoutId = null;
    }, delay);
  };
}

// ========================================
// Constants
// ========================================

export const DEFAULT_CONFIG = {
  video: {
    width: 320,
    height: 240,
    frameRate: 15,
    quality: 0.7
  },
  websocket: {
    url: 'ws://localhost:8765',
    reconnectAttempts: 5,
    reconnectDelay: 2000
  },
  performance: {
    targetFPS: 15,
    maxLatency: 100, // ms
    statsUpdateInterval: 1000 // ms
  }
};

export const GESTURE_TYPES = {
  FIST: 'fist',
  FILTER_CONTROL: 'filter_control',
  LOW_EQ: 'low_eq',
  MID_EQ: 'mid_eq',
  HIGH_EQ: 'high_eq',
  OPEN_HAND: 'open_hand',
  THUMBS_UP: 'thumbs_up',
  PINCH: 'pinch',
  UNKNOWN: 'unknown'
} as const;

export const CONNECTION_STATES = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  ERROR: 'error'
} as const;

// ========================================
// Version Information
// ========================================

export const VERSION = '1.0.0';
export const BUILD_DATE = new Date().toISOString();

/**
 * Get application information
 */
export function getAppInfo() {
  return {
    name: 'GesteDJ Web UI',
    version: VERSION,
    buildDate: BUILD_DATE,
    description: 'Modern web interface for GesteDJ gesture-controlled DJ software'
  };
}