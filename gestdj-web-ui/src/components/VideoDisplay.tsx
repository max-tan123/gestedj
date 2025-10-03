/**
 * @fileoverview Video Display Component
 *
 * This component handles video display, including both raw camera feed
 * and processed video frames with gesture overlays.
 *
 * @author GesteDJ Team
 * @version 1.0.0
 */

import React, { useEffect, useRef } from 'react';
import { GestureData } from '../types';

interface VideoDisplayProps {
  /** Video stream from camera */
  stream: MediaStream | null;
  /** Processed frame data (base64 image) */
  processedFrame?: string | null;
  /** Gesture recognition data */
  gestureData?: GestureData | null;
  /** Video display width */
  width?: number;
  /** Video display height */
  height?: number;
  /** Show processed frame instead of raw stream */
  showProcessed?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Video display component with gesture overlay support
 */
export function VideoDisplay({
  stream,
  processedFrame,
  gestureData,
  width = 320,
  height = 240,
  showProcessed = false,
  className = ''
}: VideoDisplayProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  // Setup video stream
  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    };
  }, []);

  const baseStyles = {
    width: `${width}px`,
    height: `${height}px`,
    border: '2px solid #444',
    borderRadius: '8px',
    backgroundColor: '#111'
  };

  if (showProcessed && processedFrame) {
    return (
      <div className={`video-display processed ${className}`}>
        <img
          src={`data:image/jpeg;base64,${processedFrame}`}
          alt="Processed video frame"
          style={{
            ...baseStyles,
            borderColor: '#0f0' // Green border for processed frames
          }}
        />
        {gestureData && (
          <div className="gesture-overlay">
            <GestureDataDisplay gestureData={gestureData} />
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`video-display raw ${className}`}>
      <video
        ref={videoRef}
        width={width}
        height={height}
        autoPlay
        muted
        playsInline
        style={baseStyles}
      />
      {!stream && (
        <div
          style={{
            ...baseStyles,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#666',
            fontSize: '14px'
          }}
        >
          No video stream
        </div>
      )}
    </div>
  );
}

interface GestureDataDisplayProps {
  gestureData: GestureData;
}

/**
 * Component to display gesture recognition data
 */
function GestureDataDisplay({ gestureData }: GestureDataDisplayProps) {
  return (
    <div style={{
      marginTop: '10px',
      padding: '10px',
      backgroundColor: '#1a1a1a',
      borderRadius: '8px',
      fontSize: '12px',
      fontFamily: 'monospace',
      color: '#fff'
    }}>
      <div><strong>Gesture Data:</strong></div>
      <div>Hands detected: {gestureData.hands_detected || 0}</div>

      {gestureData.gestures && Object.entries(gestureData.gestures).map(([hand, data]) => (
        <div key={hand}>
          {hand}: {data.fingers_up} fingers ({data.gesture_type})
        </div>
      ))}

      {gestureData.processing_time && (
        <div>Processing: {gestureData.processing_time.toFixed(1)}ms</div>
      )}
    </div>
  );
}

/**
 * Component for side-by-side video comparison
 */
interface VideoComparisonProps {
  rawStream: MediaStream | null;
  processedFrame: string | null;
  gestureData: GestureData | null;
  width?: number;
  height?: number;
}

export function VideoComparison({
  rawStream,
  processedFrame,
  gestureData,
  width = 320,
  height = 240
}: VideoComparisonProps) {
  return (
    <div style={{ display: 'flex', gap: '20px', alignItems: 'flex-start' }}>
      <div style={{ flex: 1, textAlign: 'center' }}>
        <h4>📹 Raw Camera Feed</h4>
        <VideoDisplay
          stream={rawStream}
          width={width}
          height={height}
        />
        <p style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
          Direct browser camera input
        </p>
      </div>

      <div style={{ flex: 1, textAlign: 'center' }}>
        <h4>🧠 Processed Feed</h4>
        <VideoDisplay
          stream={null}
          processedFrame={processedFrame}
          gestureData={gestureData}
          width={width}
          height={height}
          showProcessed={true}
        />
        <p style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
          Camera → WebSocket → Backend → MediaPipe → Overlay
        </p>
      </div>
    </div>
  );
}