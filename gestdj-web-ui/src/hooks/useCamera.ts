/**
 * @fileoverview React Hook for Camera Management
 *
 * This hook provides a React-friendly interface to camera operations,
 * managing camera state and providing video capture functionality.
 *
 * @author GesteDJ Team
 * @version 1.0.0
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { CameraService, createCameraService } from '../services/camera';
import { UseCameraReturn, VideoConfig } from '../types';

/**
 * React hook for camera management and video capture
 */
export function useCamera(config?: Partial<VideoConfig>): UseCameraReturn {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isActive, setIsActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cameraService = useRef<CameraService | null>(null);

  useEffect(() => {
    cameraService.current = createCameraService(config);

    // Setup event handlers
    cameraService.current.on('camera_started', () => {
      setIsActive(true);
      setError(null);
      setStream(cameraService.current!.getStream());
    });

    cameraService.current.on('camera_stopped', () => {
      setIsActive(false);
      setStream(null);
    });

    cameraService.current.on('camera_error', () => {
      setError('Camera access failed');
      setIsActive(false);
      setStream(null);
    });

    return () => {
      if (cameraService.current) {
        cameraService.current.stopCamera();
      }
    };
  }, []);

  const startCamera = useCallback(async () => {
    if (cameraService.current) {
      try {
        await cameraService.current.startCamera();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Camera start failed');
      }
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (cameraService.current) {
      cameraService.current.stopCamera();
    }
  }, []);

  const captureFrame = useCallback(() => {
    if (cameraService.current) {
      return cameraService.current.captureFrame();
    }
    return null;
  }, []);

  return {
    stream,
    isActive,
    error,
    startCamera,
    stopCamera,
    captureFrame
  };
}

/**
 * Hook for video frame capture and streaming
 */
export function useVideoCapture(frameRate: number = 15) {
  const [isCapturing, setIsCapturing] = useState(false);
  const [frameCount, setFrameCount] = useState(0);

  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const cameraService = useRef<CameraService | null>(null);
  const onFrameCapturedRef = useRef<((frame: string) => void) | null>(null);

  useEffect(() => {
    cameraService.current = createCameraService();

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      if (cameraService.current) {
        cameraService.current.stopCamera();
      }
    };
  }, []);

  const startCapture = useCallback((onFrameCaptured?: (frame: string) => void) => {
    if (isCapturing || !cameraService.current?.isActive()) {
      return;
    }

    onFrameCapturedRef.current = onFrameCaptured || null;
    setIsCapturing(true);
    setFrameCount(0);

    intervalRef.current = setInterval(() => {
      if (cameraService.current) {
        const frame = cameraService.current.captureFrame();
        if (frame && onFrameCapturedRef.current) {
          onFrameCapturedRef.current(frame);
          setFrameCount(prev => prev + 1);
        }
      }
    }, 1000 / frameRate);
  }, [isCapturing, frameRate]);

  const stopCapture = useCallback(() => {
    setIsCapturing(false);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    onFrameCapturedRef.current = null;
  }, []);

  return {
    isCapturing,
    frameCount,
    startCapture,
    stopCapture
  };
}