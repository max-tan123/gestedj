/**
 * @fileoverview Type definitions for GesteDJ Web UI
 *
 * This file contains all TypeScript type definitions used throughout the application.
 * It provides type safety and better IDE support for the entire frontend.
 *
 * @author GesteDJ Team
 * @version 1.0.0
 */

// ========================================
// WebSocket Message Types
// ========================================

export interface BaseMessage {
  type: string;
  timestamp?: number;
}

export interface LatencyTestMessage extends BaseMessage {
  type: 'latency_test';
  timestamp: number;
  test_data: string;
}

export interface VideoFrameMessage extends BaseMessage {
  type: 'frontend_video_frame';
  frame_data: string;
  client_timestamp: number;
  frame_number: number;
}

export interface VideoLatencyTestMessage extends BaseMessage {
  type: 'video_latency_test';
  frame_data: string;
  timestamp: number;
  test_id: string;
}

// ========================================
// WebSocket Response Types
// ========================================

export interface ConnectionEstablishedResponse extends BaseMessage {
  type: 'connection_established';
  message: string;
  mediapipe_available: boolean;
  midi_available: boolean;
  rtmidi_available: boolean;
  original_midi_available: boolean;
  server_timestamp: number;
}

export interface LatencyResponse extends BaseMessage {
  type: 'latency_response';
  client_timestamp: number;
  server_receive_time: number;
  server_send_time: number;
  round_trip_data: string;
}

export interface VideoFrameProcessedResponse extends BaseMessage {
  type: 'video_frame_processed';
  frame_number: number;
  client_timestamp: number;
  server_receive_time: number;
  server_send_time: number;
  processing_time: number;
  processed_frame: string;
  gesture_data: GestureData;
  stats: ProcessingStats;
}

export interface VideoLatencyResponse extends BaseMessage {
  type: 'video_latency_response';
  test_id: string;
  client_timestamp: number;
  server_receive_time: number;
  server_send_time: number;
  processing_time?: number;
}

// ========================================
// Gesture Recognition Types
// ========================================

export interface Landmark {
  x: number;
  y: number;
  z: number;
}

export interface HandLandmarks {
  hand_index: number;
  landmarks: Landmark[];
}

export interface GestureInfo {
  fingers_up: number;
  gesture_type: string;
}

export interface GestureData {
  hands_detected: number;
  landmarks: HandLandmarks[];
  gestures: Record<string, GestureInfo>;
  processing_time?: number;
}

// ========================================
// Statistics and Performance Types
// ========================================

export interface LatencyResults {
  min: number;
  max: number;
  avg: number;
  count: number;
}

export interface VideoStats {
  framesSent: number;
  backendResponses: number;
  currentFPS: number;
  dataSent: number;
}

export interface ProcessingStats {
  frames_processed: number;
  gestures_detected: number;
  detection_rate: number;
}

// ========================================
// Component State Types
// ========================================

export interface CameraState {
  stream: MediaStream | null;
  isActive: boolean;
  error: string | null;
}

export interface StreamingState {
  isActive: boolean;
  frameRate: number;
  quality: number;
}

export interface BackendState {
  status: string;
  isLoading: boolean;
  lastResponse: any;
}

export interface ConnectionState {
  isConnected: boolean;
  lastPing: number;
  error: string | null;
}

// ========================================
// Configuration Types
// ========================================

export interface VideoConfig {
  width: number;
  height: number;
  frameRate: number;
  quality: number;
}

export interface WebSocketConfig {
  url: string;
  reconnectAttempts: number;
  reconnectDelay: number;
}

export interface AppConfig {
  video: VideoConfig;
  websocket: WebSocketConfig;
  debug: boolean;
}

// ========================================
// Event Types
// ========================================

export interface VideoEvent {
  type: 'frame_captured' | 'stream_started' | 'stream_stopped' | 'error';
  data?: any;
  timestamp: number;
}

export interface WebSocketEvent {
  type: 'connected' | 'disconnected' | 'message' | 'error';
  data?: any;
  timestamp: number;
}

// ========================================
// Hook Return Types
// ========================================

export interface UseCameraReturn extends CameraState {
  startCamera: () => Promise<void>;
  stopCamera: () => void;
  captureFrame: () => string | null;
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  send: (message: any) => void;
  lastMessage: any;
  error: string | null;
  connect: () => void;
  disconnect: () => void;
}

export interface UseVideoStreamingReturn {
  isStreaming: boolean;
  stats: VideoStats;
  startStreaming: () => void;
  stopStreaming: () => void;
  processedFrame: string | null;
  gestureData: GestureData | null;
}

// ========================================
// Utility Types
// ========================================

export type MessageHandler<T = any> = (message: T) => void;
export type ErrorHandler = (error: Error) => void;
export type EventCallback = () => void;

// ========================================
// Enums
// ========================================

export enum GestureType {
  FIST = 'fist',
  FILTER_CONTROL = 'filter_control',
  LOW_EQ = 'low_eq',
  MID_EQ = 'mid_eq',
  HIGH_EQ = 'high_eq',
  OPEN_HAND = 'open_hand',
  UNKNOWN = 'unknown'
}

export enum ConnectionStatus {
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  ERROR = 'error'
}

export enum StreamingStatus {
  STOPPED = 'stopped',
  STARTING = 'starting',
  STREAMING = 'streaming',
  ERROR = 'error'
}