/**
 * @fileoverview React Hook for WebSocket Communication
 *
 * This hook provides a React-friendly interface to the WebSocket service,
 * managing connection state and providing easy message handling.
 *
 * @author GesteDJ Team
 * @version 1.0.0
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { WebSocketService, createWebSocketService } from '../services/websocket';
import {
  UseWebSocketReturn,
  WebSocketConfig,
  ConnectionEstablishedResponse,
  LatencyResults
} from '../types';

/**
 * React hook for WebSocket communication with GesteDJ backend
 */
export function useWebSocket(config?: Partial<WebSocketConfig>): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const wsService = useRef<WebSocketService | null>(null);

  // Initialize WebSocket service
  useEffect(() => {
    wsService.current = createWebSocketService(config);

    // Setup event handlers
    wsService.current.on('connected', () => {
      setIsConnected(true);
      setError(null);
    });

    wsService.current.on('disconnected', () => {
      setIsConnected(false);
    });

    wsService.current.on('error', (err: Error) => {
      setError(err.message);
    });

    wsService.current.on('message', (message: any) => {
      setLastMessage(message);
    });

    return () => {
      if (wsService.current) {
        wsService.current.disconnect();
      }
    };
  }, []);

  const connect = useCallback(async () => {
    if (wsService.current) {
      try {
        await wsService.current.connect();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Connection failed');
      }
    }
  }, []);

  const disconnect = useCallback(() => {
    if (wsService.current) {
      wsService.current.disconnect();
    }
  }, []);

  const send = useCallback((message: any) => {
    if (wsService.current && isConnected) {
      try {
        wsService.current.send(message);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Send failed');
      }
    }
  }, [isConnected]);

  return {
    isConnected,
    send,
    lastMessage,
    error,
    connect,
    disconnect
  };
}

/**
 * Hook for testing WebSocket latency
 */
export function useLatencyTest() {
  const [results, setResults] = useState<LatencyResults>({ min: 0, max: 0, avg: 0, count: 0 });
  const [isTesting, setIstesting] = useState(false);

  const wsService = useRef<WebSocketService | null>(null);

  useEffect(() => {
    wsService.current = createWebSocketService();
    return () => {
      if (wsService.current) {
        wsService.current.disconnect();
      }
    };
  }, []);

  const runLatencyTest = useCallback(async (testCount: number = 20) => {
    if (!wsService.current || isTesting) return;

    setIsesting(true);
    const latencies: number[] = [];

    try {
      // Ensure connection
      if (!wsService.current.isConnected()) {
        await wsService.current.connect();
      }

      // Run multiple latency tests
      for (let i = 0; i < testCount; i++) {
        const latency = await wsService.current.testLatency();
        latencies.push(latency);

        // Small delay between tests
        await new Promise(resolve => setTimeout(resolve, 50));
      }

      // Calculate results
      const min = Math.min(...latencies);
      const max = Math.max(...latencies);
      const avg = latencies.reduce((a, b) => a + b, 0) / latencies.length;

      setResults({
        min: Math.round(min * 100) / 100,
        max: Math.round(max * 100) / 100,
        avg: Math.round(avg * 100) / 100,
        count: testCount
      });

    } catch (error) {
      console.error('Latency test failed:', error);
    } finally {
      setIsesting(false);
    }
  }, [isesting]);

  return {
    results,
    isesting,
    runLatencyTest
  };
}

/**
 * Hook for backend connection management
 */
export function useBackendConnection() {
  const [status, setStatus] = useState<string>('Not connected');
  const [capabilities, setCapabilities] = useState<{
    mediapipe: boolean;
    midi: boolean;
    rtmidi: boolean;
    originalMidi: boolean;
  }>({
    mediapipe: false,
    midi: false,
    rtmidi: false,
    originalMidi: false
  });

  const wsService = useRef<WebSocketService | null>(null);

  useEffect(() => {
    wsService.current = createWebSocketService();

    // Listen for connection established message
    wsService.current.on('connection_established', (response: ConnectionEstablishedResponse) => {
      setStatus('✅ Connected to backend');
      setCapabilities({
        mediapipe: response.mediapipe_available,
        midi: response.midi_available,
        rtmidi: response.rtmidi_available,
        originalMidi: response.original_midi_available
      });
    });

    wsService.current.on('disconnected', () => {
      setStatus('❌ Disconnected');
      setCapabilities({
        mediapipe: false,
        midi: false,
        rtmidi: false,
        originalMidi: false
      });
    });

    wsService.current.on('error', (error: Error) => {
      setStatus(`❌ Error: ${error.message}`);
    });

    return () => {
      if (wsService.current) {
        wsService.current.disconnect();
      }
    };
  }, []);

  const testConnection = useCallback(async () => {
    if (wsService.current) {
      setStatus('Testing connection...');
      try {
        await wsService.current.connect();
      } catch (error) {
        setStatus('❌ Connection failed');
      }
    }
  }, []);

  return {
    status,
    capabilities,
    testConnection
  };
}