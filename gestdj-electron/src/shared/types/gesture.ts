// Gesture recognition types (based on Python backend models)

export interface Landmark {
  x: number;
  y: number;
  z: number;
}

export interface HandLandmarks {
  hand_index: number;
  landmarks: Landmark[];
  confidence: number;
  handedness?: 'Left' | 'Right';
}

export interface GestureInfo {
  fingers_up: number;
  gesture_type: string;
  confidence: number;
  angle?: number; // For rotational gestures
  distance?: number; // For pinch/distance gestures
  velocity?: number; // For movement gestures
}

export interface GestureData {
  hands_detected: number;
  landmarks: HandLandmarks[];
  gestures: Record<string, GestureInfo>;
  processing_time?: number;
  timestamp?: number;
  frame_number?: number;
}

export interface ProcessingStats {
  frames_processed: number;
  gestures_detected: number;
  detection_rate: number;
  avg_processing_time: number;
  min_processing_time: number;
  max_processing_time: number;
}

// WebSocket message types
export interface VideoFrameMessage {
  type: 'frontend_video_frame';
  frame_data: string; // base64 encoded
  client_timestamp: number;
  frame_number: number;
}

export interface VideoFrameResponse {
  type: 'video_frame_processed';
  processed_frame?: string; // base64 encoded with overlays
  gesture_data?: GestureData;
  server_timestamp: number;
  processing_time: number;
}

export interface LatencyTestMessage {
  type: 'latency_test';
  timestamp: number;
  test_data: string;
}

export interface LatencyTestResponse {
  type: 'latency_response';
  client_timestamp: number;
  server_timestamp: number;
}

export type WebSocketMessage = VideoFrameMessage | LatencyTestMessage;
export type WebSocketResponse = VideoFrameResponse | LatencyTestResponse;