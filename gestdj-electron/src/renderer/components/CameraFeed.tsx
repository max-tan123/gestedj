import React, { useRef, useEffect, useState } from 'react';
import { HandLandmarker, FilesetResolver, HandLandmarkerResult } from '@mediapipe/tasks-vision';
import '../styles/CameraFeed.css';

interface CameraFeedProps {
  onLandmarks?: (landmarks: HandLandmarkerResult) => void;
}

const CameraFeed: React.FC<CameraFeedProps> = ({ onLandmarks }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fps, setFps] = useState(0);
  const [handLandmarker, setHandLandmarker] = useState<HandLandmarker | null>(null);
  const [mediapipeReady, setMediapipeReady] = useState(false);
  const [handsDetected, setHandsDetected] = useState(0);
  const animationFrameRef = useRef<number>();
  const lastFrameTimeRef = useRef<number>(0);
  const fpsCounterRef = useRef<number[]>([]);

  // Initialize MediaPipe
  useEffect(() => {
    async function initMediaPipe() {
      try {
        const vision = await FilesetResolver.forVisionTasks(
          "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm"
        );

        const landmarker = await HandLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath: "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
            delegate: "GPU"
          },
          runningMode: "VIDEO",
          numHands: 2,
          minHandDetectionConfidence: 0.5,
          minHandPresenceConfidence: 0.5,
          minTrackingConfidence: 0.5
        });

        setHandLandmarker(landmarker);
        setMediapipeReady(true);
        console.log('✅ MediaPipe HandLandmarker initialized');
      } catch (err) {
        console.error('MediaPipe initialization error:', err);
        setError('Failed to initialize MediaPipe: ' + (err instanceof Error ? err.message : 'Unknown error'));
      }
    }

    initMediaPipe();
  }, []);

  // Start camera
  useEffect(() => {
    let stream: MediaStream | null = null;

    async function startCamera() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 640 },
            height: { ideal: 480 },
            frameRate: { ideal: 30 }
          }
        });

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          setIsStreaming(true);
          setError(null);
        }
      } catch (err) {
        console.error('Camera access error:', err);
        setError(err instanceof Error ? err.message : 'Failed to access camera');
        setIsStreaming(false);
      }
    }

    startCamera();

    // Cleanup
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  // Process frames
  useEffect(() => {
    if (!isStreaming || !videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    if (!ctx) return;

    // Set canvas size to match video
    video.addEventListener('loadedmetadata', () => {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
    });

    // Frame processing loop
    function processFrame() {
      if (!video || !canvas || !ctx) return;

      // Calculate FPS
      const now = performance.now();
      const delta = now - lastFrameTimeRef.current;
      if (delta > 0) {
        fpsCounterRef.current.push(1000 / delta);
        if (fpsCounterRef.current.length > 30) {
          fpsCounterRef.current.shift();
        }
        const avgFps = fpsCounterRef.current.reduce((a, b) => a + b, 0) / fpsCounterRef.current.length;
        setFps(Math.round(avgFps));
      }
      lastFrameTimeRef.current = now;

      // Draw video frame to canvas
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      // Run MediaPipe hand detection
      if (handLandmarker && mediapipeReady) {
        const results = handLandmarker.detectForVideo(video, now);

        // Update hands detected count
        setHandsDetected(results.landmarks.length);

        // Draw landmarks on canvas
        if (results.landmarks.length > 0) {
          drawLandmarks(ctx, results);
        }

        // Send to parent component
        if (onLandmarks && results.landmarks.length > 0) {
          onLandmarks(results);
        }
      }

      // Continue loop
      animationFrameRef.current = requestAnimationFrame(processFrame);
    }

    // Draw hand landmarks on canvas
    function drawLandmarks(ctx: CanvasRenderingContext2D, results: HandLandmarkerResult) {
      const width = canvas.width;
      const height = canvas.height;

      // Draw each hand
      for (let i = 0; i < results.landmarks.length; i++) {
        const landmarks = results.landmarks[i];
        const handedness = results.handedness[i][0].categoryName;

        // Choose color based on handedness (Left = Blue, Right = Red)
        const color = handedness === 'Left' ? '#4CAF50' : '#FF5722';

        // Draw connections
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;

        // Hand connections (MediaPipe hand model)
        const connections = [
          [0, 1], [1, 2], [2, 3], [3, 4],      // Thumb
          [0, 5], [5, 6], [6, 7], [7, 8],      // Index
          [0, 9], [9, 10], [10, 11], [11, 12], // Middle
          [0, 13], [13, 14], [14, 15], [15, 16], // Ring
          [0, 17], [17, 18], [18, 19], [19, 20], // Pinky
          [5, 9], [9, 13], [13, 17]            // Palm
        ];

        connections.forEach(([start, end]) => {
          const startPoint = landmarks[start];
          const endPoint = landmarks[end];
          ctx.beginPath();
          ctx.moveTo(startPoint.x * width, startPoint.y * height);
          ctx.lineTo(endPoint.x * width, endPoint.y * height);
          ctx.stroke();
        });

        // Draw landmark points
        ctx.fillStyle = color;
        landmarks.forEach((landmark, idx) => {
          const x = landmark.x * width;
          const y = landmark.y * height;
          ctx.beginPath();
          ctx.arc(x, y, idx === 0 ? 6 : 3, 0, 2 * Math.PI); // Wrist is larger
          ctx.fill();
        });

        // Draw hand label
        const wrist = landmarks[0];
        ctx.fillStyle = color;
        ctx.font = 'bold 16px monospace';
        ctx.fillText(handedness, wrist.x * width + 10, wrist.y * height - 10);
      }
    }

    // Wait for video to be ready
    if (video.readyState >= video.HAVE_ENOUGH_DATA) {
      processFrame();
    } else {
      video.addEventListener('canplay', processFrame, { once: true });
    }

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isStreaming, onLandmarks, handLandmarker, mediapipeReady]);

  return (
    <div className="camera-feed">
      <div className="camera-container">
        {error && (
          <div className="camera-error">
            <p>❌ {error}</p>
            <p className="error-hint">
              Make sure camera permissions are granted and no other app is using the camera.
            </p>
          </div>
        )}

        {!error && !isStreaming && (
          <div className="camera-loading">
            <p>📷 Initializing camera...</p>
          </div>
        )}

        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          style={{ display: 'none' }}
        />

        <canvas
          ref={canvasRef}
          className="camera-canvas"
          style={{ display: isStreaming ? 'block' : 'none' }}
        />

        {isStreaming && (
          <div className="camera-overlay">
            <div className="fps-counter">
              {fps} FPS
            </div>
            <div className="mediapipe-status">
              {mediapipeReady ? '✅ MediaPipe Ready' : '⏳ Loading MediaPipe...'}
            </div>
            {mediapipeReady && (
              <div className="hands-counter">
                🖐️ {handsDetected} hand{handsDetected !== 1 ? 's' : ''}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default CameraFeed;
