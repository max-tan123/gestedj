/**
 * @fileoverview Optimized Video Processor for Low-Latency Gesture Recognition
 *
 * This component implements several optimizations to reduce latency:
 * - Adaptive FPS based on gesture detection
 * - Smaller frame sizes for processing
 * - Frontend-only visualization (no round-trip for landmarks)
 * - Smart frame skipping when hands not detected
 *
 * @author GesteDJ Team
 * @version 1.0.0
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { WebSocketService } from '../services/websocket';
import { GestureData, VideoStats } from '../types';

interface OptimizedVideoProcessorProps {
  webSocketService: WebSocketService;
  onStatsUpdate?: (stats: VideoStats) => void;
  onGestureUpdate?: (gesture: GestureData) => void;
}

export const OptimizedVideoProcessor: React.FC<OptimizedVideoProcessorProps> = ({
  webSocketService,
  onStatsUpdate,
  onGestureUpdate
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const displayCanvasRef = useRef<HTMLCanvasElement>(null);

  const [isStreaming, setIsStreaming] = useState(false);
  const [stats, setStats] = useState<VideoStats>({
    fps: 0,
    latency: 0,
    framesProcessed: 0,
    gesturesDetected: 0,
    dataRate: 0
  });

  // Adaptive settings for latency optimization
  const [adaptiveSettings, setAdaptiveSettings] = useState({
    targetFPS: 15, // Start lower
    frameSize: { width: 160, height: 120 }, // Smaller initial size
    jpegQuality: 0.5, // Lower quality for speed
    skipFrames: 0 // Skip frames when no hands detected
  });

  const streamIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const statsRef = useRef({
    framesSent: 0,
    framesProcessed: 0,
    totalLatency: 0,
    gesturesDetected: 0,
    lastStatsUpdate: Date.now(),
    dataSize: 0
  });

  /**
   * Start camera with optimized settings
   */
  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 320 },
          height: { ideal: 240 },
          frameRate: { ideal: 30 } // Camera captures at 30, we'll subsample
        },
        audio: false
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }

      return true;
    } catch (error) {
      console.error('Camera access failed:', error);
      return false;
    }
  }, []);

  /**
   * Optimized frame capture with adaptive sizing
   */
  const captureOptimizedFrame = useCallback((): string | null => {
    const video = videoRef.current;
    const canvas = canvasRef.current;

    if (!video || !canvas) return null;

    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    const { width, height } = adaptiveSettings.frameSize;

    // Set canvas size to adaptive settings
    canvas.width = width;
    canvas.height = height;

    // Draw and compress
    ctx.drawImage(video, 0, 0, width, height);

    // Use adaptive JPEG quality
    const dataURL = canvas.toDataURL('image/jpeg', adaptiveSettings.jpegQuality);
    return dataURL.split(',')[1]; // Return base64 only
  }, [adaptiveSettings]);

  /**
   * Draw gesture landmarks on display canvas (frontend-only)
   */
  const drawGestureLandmarks = useCallback((gestureData: GestureData) => {
    const displayCanvas = displayCanvasRef.current;
    const video = videoRef.current;

    if (!displayCanvas || !video) return;

    const ctx = displayCanvas.getContext('2d');
    if (!ctx) return;

    // Set display canvas to match video size
    displayCanvas.width = video.videoWidth || 320;
    displayCanvas.height = video.videoHeight || 240;

    // Draw video frame
    ctx.drawImage(video, 0, 0, displayCanvas.width, displayCanvas.height);

    // Draw landmarks if available
    if (gestureData.landmarks && gestureData.landmarks.length > 0) {
      ctx.strokeStyle = '#00ff00';
      ctx.fillStyle = '#ff0000';
      ctx.lineWidth = 2;

      gestureData.landmarks.forEach((hand, handIndex) => {
        // Draw hand landmarks
        hand.landmarks.forEach((landmark, i) => {
          const x = landmark.x * displayCanvas.width;
          const y = landmark.y * displayCanvas.height;

          // Draw landmark point
          ctx.beginPath();
          ctx.arc(x, y, 3, 0, 2 * Math.PI);
          ctx.fill();

          // Draw landmark number for key points
          if ([0, 4, 8, 12, 16, 20].includes(i)) {
            ctx.fillStyle = '#ffffff';
            ctx.font = '10px Arial';
            ctx.fillText(i.toString(), x + 5, y - 5);
            ctx.fillStyle = '#ff0000';
          }
        });

        // Draw gesture info
        ctx.fillStyle = '#00ff00';
        ctx.font = '14px Arial';
        const gestureInfo = gestureData.gestures[`hand_${handIndex}`];
        if (gestureInfo) {
          ctx.fillText(
            `Hand ${handIndex}: ${gestureInfo.fingers_up} fingers (${gestureInfo.gesture_type})`,
            10,
            30 + handIndex * 25
          );
        }
      });
    }

    // Draw performance info
    ctx.fillStyle = '#ffff00';
    ctx.font = '12px Arial';
    ctx.fillText(`FPS: ${stats.fps} | Latency: ${stats.latency.toFixed(1)}ms`, 10, displayCanvas.height - 10);
  }, [stats]);

  /**
   * Process single frame with adaptive optimization
   */
  const processFrame = useCallback(async () => {
    if (!webSocketService.isConnected()) return;

    // Check if we should skip this frame
    if (adaptiveSettings.skipFrames > 0) {
      setAdaptiveSettings(prev => ({
        ...prev,
        skipFrames: prev.skipFrames - 1
      }));
      return;
    }

    const frameData = captureOptimizedFrame();
    if (!frameData) return;

    const startTime = performance.now();
    const frameNumber = statsRef.current.framesSent;

    try {
      // Send frame for processing
      webSocketService.sendVideoFrame(frameData, frameNumber);

      statsRef.current.framesSent++;
      statsRef.current.dataSize += frameData.length;

      // Update display immediately (don't wait for response)
      if (displayCanvasRef.current && videoRef.current) {
        const ctx = displayCanvasRef.current.getContext('2d');
        if (ctx) {
          displayCanvasRef.current.width = videoRef.current.videoWidth || 320;
          displayCanvasRef.current.height = videoRef.current.videoHeight || 240;
          ctx.drawImage(videoRef.current, 0, 0, displayCanvasRef.current.width, displayCanvasRef.current.height);
        }
      }

    } catch (error) {
      console.error('Frame processing error:', error);
    }
  }, [webSocketService, captureOptimizedFrame, adaptiveSettings.skipFrames]);

  /**
   * Handle processed frame response from backend
   */
  const handleFrameResponse = useCallback((response: any) => {
    if (response.type !== 'video_frame_processed') return;

    const latency = performance.now() - response.client_timestamp;

    statsRef.current.framesProcessed++;
    statsRef.current.totalLatency += latency;

    if (response.gesture_data) {
      // Draw landmarks on frontend
      drawGestureLandmarks(response.gesture_data);

      // Update gesture detection count
      if (response.gesture_data.hands_detected > 0) {
        statsRef.current.gesturesDetected++;

        // Reset skip frames when hands detected
        setAdaptiveSettings(prev => ({ ...prev, skipFrames: 0 }));
      } else {
        // Start skipping frames when no hands detected
        setAdaptiveSettings(prev => ({
          ...prev,
          skipFrames: Math.min(prev.skipFrames + 1, 3) // Skip up to 3 frames
        }));
      }

      onGestureUpdate?.(response.gesture_data);
    }

    // Adaptive FPS adjustment based on latency
    if (latency > 100 && adaptiveSettings.targetFPS > 10) {
      setAdaptiveSettings(prev => ({
        ...prev,
        targetFPS: Math.max(prev.targetFPS - 2, 10),
        jpegQuality: Math.max(prev.jpegQuality - 0.1, 0.3)
      }));
    } else if (latency < 50 && adaptiveSettings.targetFPS < 20) {
      setAdaptiveSettings(prev => ({
        ...prev,
        targetFPS: Math.min(prev.targetFPS + 1, 20),
        jpegQuality: Math.min(prev.jpegQuality + 0.05, 0.7)
      }));
    }

    updateStats();
  }, [drawGestureLandmarks, onGestureUpdate, adaptiveSettings]);

  /**
   * Update performance statistics
   */
  const updateStats = useCallback(() => {
    const now = Date.now();
    const timeDiff = now - statsRef.current.lastStatsUpdate;

    if (timeDiff >= 1000) { // Update every second
      const current = statsRef.current;
      const fps = (current.framesSent * 1000) / timeDiff;
      const avgLatency = current.framesProcessed > 0 ?
        current.totalLatency / current.framesProcessed : 0;
      const dataRate = (current.dataSize / 1024) / (timeDiff / 1000); // KB/s

      const newStats: VideoStats = {
        fps: Math.round(fps * 10) / 10,
        latency: avgLatency,
        framesProcessed: current.framesProcessed,
        gesturesDetected: current.gesturesDetected,
        dataRate: Math.round(dataRate * 10) / 10
      };

      setStats(newStats);
      onStatsUpdate?.(newStats);

      // Reset counters
      statsRef.current.framesSent = 0;
      statsRef.current.dataSize = 0;
      statsRef.current.lastStatsUpdate = now;
    }
  }, [onStatsUpdate]);

  /**
   * Start optimized streaming
   */
  const startStreaming = useCallback(async () => {
    if (isStreaming) return;

    const cameraStarted = await startCamera();
    if (!cameraStarted) return;

    setIsStreaming(true);

    // Start frame processing loop with adaptive FPS
    const frameInterval = 1000 / adaptiveSettings.targetFPS;
    streamIntervalRef.current = setInterval(processFrame, frameInterval);

    console.log(`🚀 Optimized streaming started at ${adaptiveSettings.targetFPS} FPS`);
  }, [isStreaming, startCamera, processFrame, adaptiveSettings.targetFPS]);

  /**
   * Stop streaming
   */
  const stopStreaming = useCallback(() => {
    setIsStreaming(false);

    if (streamIntervalRef.current) {
      clearInterval(streamIntervalRef.current);
      streamIntervalRef.current = null;
    }

    // Stop camera
    if (videoRef.current?.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach(track => track.stop());
      videoRef.current.srcObject = null;
    }

    console.log('⏹️ Optimized streaming stopped');
  }, []);

  // Setup WebSocket message handler
  useEffect(() => {
    webSocketService.on('video_frame_processed', handleFrameResponse);

    return () => {
      webSocketService.off('video_frame_processed', handleFrameResponse);
    };
  }, [webSocketService, handleFrameResponse]);

  // Update streaming interval when FPS changes
  useEffect(() => {
    if (isStreaming && streamIntervalRef.current) {
      clearInterval(streamIntervalRef.current);
      const frameInterval = 1000 / adaptiveSettings.targetFPS;
      streamIntervalRef.current = setInterval(processFrame, frameInterval);
    }
  }, [adaptiveSettings.targetFPS, isStreaming, processFrame]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopStreaming();
    };
  }, [stopStreaming]);

  return (
    <div className="optimized-video-processor">
      <div className="video-controls">
        <button
          onClick={startStreaming}
          disabled={isStreaming}
          className="btn-start"
        >
          Start Optimized Streaming
        </button>
        <button
          onClick={stopStreaming}
          disabled={!isStreaming}
          className="btn-stop"
        >
          Stop Streaming
        </button>
      </div>

      <div className="video-display">
        <div className="video-section">
          <h3>📹 Camera Feed (Hidden)</h3>
          <video
            ref={videoRef}
            autoPlay
            muted
            style={{ display: 'none' }} // Hidden - used for capture only
          />
          <canvas
            ref={canvasRef}
            style={{ display: 'none' }} // Hidden - used for processing only
          />
        </div>

        <div className="video-section">
          <h3>🧠 Gesture Recognition (Optimized)</h3>
          <canvas
            ref={displayCanvasRef}
            width={320}
            height={240}
            style={{
              border: '2px solid #444',
              borderRadius: '8px',
              background: '#111'
            }}
          />
          <p>Real-time landmarks drawn on frontend (no round-trip latency)</p>
        </div>
      </div>

      <div className="optimization-stats">
        <h4>🚀 Optimization Settings</h4>
        <div className="stats-grid">
          <div>Target FPS: {adaptiveSettings.targetFPS}</div>
          <div>Frame Size: {adaptiveSettings.frameSize.width}x{adaptiveSettings.frameSize.height}</div>
          <div>JPEG Quality: {(adaptiveSettings.jpegQuality * 100).toFixed(0)}%</div>
          <div>Skip Frames: {adaptiveSettings.skipFrames}</div>
          <div>Current FPS: {stats.fps}</div>
          <div>Avg Latency: {stats.latency.toFixed(1)}ms</div>
          <div>Gestures: {stats.gesturesDetected}</div>
          <div>Data Rate: {stats.dataRate} KB/s</div>
        </div>
      </div>
    </div>
  );
};

export default OptimizedVideoProcessor;