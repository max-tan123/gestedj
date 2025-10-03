/**
 * @fileoverview WebSocket Service for GesteDJ Backend Communication
 *
 * This service handles all WebSocket communication with the GesteDJ backend,
 * including connection management, message routing, and error handling.
 *
 * @author GesteDJ Team
 * @version 1.0.0
 */

import {
  BaseMessage,
  MessageHandler,
  ErrorHandler,
  WebSocketConfig,
  ConnectionEstablishedResponse,
  LatencyResponse,
  VideoFrameProcessedResponse,
  VideoLatencyResponse
} from '../types';

/**
 * WebSocket service for real-time communication with GesteDJ backend
 */
export class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private messageHandlers = new Map<string, MessageHandler[]>();
  private isConnecting = false;

  constructor(private config: WebSocketConfig) {}

  /**
   * Establish WebSocket connection to backend
   */
  async connect(): Promise<void> {
    if (this.isConnecting || this.isConnected()) {
      return;
    }

    this.isConnecting = true;

    try {
      this.ws = new WebSocket(this.config.url);
      this.setupEventHandlers();

      // Wait for connection to open
      await new Promise<void>((resolve, reject) => {
        if (!this.ws) {
          reject(new Error('WebSocket not initialized'));
          return;
        }

        this.ws.onopen = () => {
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          this.emit('connected', null);
          resolve();
        };

        this.ws.onerror = (error) => {
          this.isConnecting = false;
          reject(new Error('WebSocket connection failed'));
        };
      });
    } catch (error) {
      this.isConnecting = false;
      throw error;
    }
  }

  /**
   * Close WebSocket connection
   */
  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.isConnecting = false;
    this.emit('disconnected', null);
  }

  /**
   * Send message to backend
   */
  send(message: BaseMessage): void {
    if (!this.isConnected()) {
      throw new Error('WebSocket not connected');
    }

    const messageStr = JSON.stringify({
      ...message,
      timestamp: message.timestamp || Date.now()
    });

    this.ws!.send(messageStr);
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Register message handler for specific message type
   */
  on<T = any>(messageType: string, handler: MessageHandler<T>): void {
    if (!this.messageHandlers.has(messageType)) {
      this.messageHandlers.set(messageType, []);
    }
    this.messageHandlers.get(messageType)!.push(handler);
  }

  /**
   * Unregister message handler
   */
  off(messageType: string, handler: MessageHandler): void {
    const handlers = this.messageHandlers.get(messageType);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    }
  }

  /**
   * Send latency test message
   */
  async testLatency(): Promise<number> {
    const startTime = performance.now();
    const testId = `test_${Date.now()}`;

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.off('latency_response', handleResponse);
        reject(new Error('Latency test timeout'));
      }, 5000);

      const handleResponse = (response: LatencyResponse) => {
        clearTimeout(timeout);
        this.off('latency_response', handleResponse);
        const latency = performance.now() - startTime;
        resolve(latency);
      };

      this.on('latency_response', handleResponse);

      this.send({
        type: 'latency_test',
        timestamp: startTime,
        test_data: testId
      });
    });
  }

  /**
   * Send video frame for processing
   */
  sendVideoFrame(frameData: string, frameNumber: number): void {
    this.send({
      type: 'frontend_video_frame',
      frame_data: frameData,
      client_timestamp: performance.now(),
      frame_number: frameNumber
    });
  }

  /**
   * Send video latency test
   */
  async testVideoLatency(frameData: string): Promise<number> {
    const startTime = performance.now();
    const testId = `video_test_${Date.now()}`;

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.off('video_latency_response', handleResponse);
        reject(new Error('Video latency test timeout'));
      }, 10000);

      const handleResponse = (response: VideoLatencyResponse) => {
        if (response.test_id === testId) {
          clearTimeout(timeout);
          this.off('video_latency_response', handleResponse);
          const latency = performance.now() - startTime;
          resolve(latency);
        }
      };

      this.on('video_latency_response', handleResponse);

      this.send({
        type: 'video_latency_test',
        frame_data: frameData,
        timestamp: startTime,
        test_id: testId
      });
    });
  }

  /**
   * Setup WebSocket event handlers
   */
  private setupEventHandlers(): void {
    if (!this.ws) return;

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        this.emit(message.type, message);
        this.emit('message', message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
        this.emit('error', new Error('Invalid message format'));
      }
    };

    this.ws.onclose = (event) => {
      this.ws = null;
      this.emit('disconnected', event);

      // Auto-reconnect if not a clean close
      if (!event.wasClean && this.reconnectAttempts < this.config.reconnectAttempts) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.emit('error', new Error('WebSocket connection error'));
    };
  }

  /**
   * Schedule reconnection attempt
   */
  private scheduleReconnect(): void {
    this.reconnectTimeout = setTimeout(() => {
      this.reconnectAttempts++;
      console.log(`Reconnect attempt ${this.reconnectAttempts}/${this.config.reconnectAttempts}`);
      this.connect().catch((error) => {
        console.error('Reconnection failed:', error);

        if (this.reconnectAttempts < this.config.reconnectAttempts) {
          this.scheduleReconnect();
        } else {
          this.emit('error', new Error('Max reconnection attempts reached'));
        }
      });
    }, this.config.reconnectDelay);
  }

  /**
   * Emit event to registered handlers
   */
  private emit(eventType: string, data: any): void {
    const handlers = this.messageHandlers.get(eventType);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error(`Error in ${eventType} handler:`, error);
        }
      });
    }
  }
}

/**
 * Create a configured WebSocket service instance
 */
export function createWebSocketService(config: Partial<WebSocketConfig> = {}): WebSocketService {
  const defaultConfig: WebSocketConfig = {
    url: 'ws://localhost:8765',
    reconnectAttempts: 5,
    reconnectDelay: 2000,
    ...config
  };

  return new WebSocketService(defaultConfig);
}