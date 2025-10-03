/**
 * @fileoverview Camera Service for Video Capture
 *
 * This service handles camera access, video stream management, and frame capture
 * for the GesteDJ gesture recognition system.
 *
 * @author GesteDJ Team
 * @version 1.0.0
 */

import { VideoConfig, EventCallback } from '../types';

/**
 * Camera service for video capture and frame processing
 */
export class CameraService {
  private stream: MediaStream | null = null;
  private videoElement: HTMLVideoElement | null = null;
  private canvasElement: HTMLCanvasElement | null = null;
  private context: CanvasRenderingContext2D | null = null;
  private eventListeners = new Map<string, EventCallback[]>();

  constructor(private config: VideoConfig) {
    this.setupCanvas();
  }

  /**
   * Initialize camera and start video stream
   */
  async startCamera(): Promise<MediaStream> {
    try {
      // Stop existing stream if any
      this.stopCamera();

      // Request camera access
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: this.config.width },
          height: { ideal: this.config.height },
          frameRate: { ideal: this.config.frameRate }
        },
        audio: false
      });

      // Setup video element
      this.videoElement = document.createElement('video');
      this.videoElement.srcObject = this.stream;
      this.videoElement.autoplay = true;
      this.videoElement.muted = true;

      // Wait for video to be ready
      await new Promise<void>((resolve, reject) => {
        if (!this.videoElement) {
          reject(new Error('Video element not initialized'));
          return;
        }

        this.videoElement.onloadedmetadata = () => resolve();
        this.videoElement.onerror = () => reject(new Error('Video load failed'));
      });

      this.emit('camera_started', null);
      return this.stream;

    } catch (error) {
      this.emit('camera_error', error);
      throw new Error(`Camera access failed: ${error}`);
    }
  }

  /**
   * Stop camera and release resources
   */
  stopCamera(): void {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }

    if (this.videoElement) {
      this.videoElement.srcObject = null;
      this.videoElement = null;
    }

    this.emit('camera_stopped', null);
  }

  /**
   * Capture current frame as base64 JPEG
   */
  captureFrame(): string | null {
    if (!this.isActive() || !this.videoElement || !this.context) {
      return null;
    }

    try {
      // Draw video frame to canvas
      this.context.drawImage(
        this.videoElement,
        0, 0,
        this.config.width,
        this.config.height
      );

      // Convert to base64 JPEG
      const dataUrl = this.canvasElement!.toDataURL('image/jpeg', this.config.quality);
      const base64Data = dataUrl.split(',')[1];

      this.emit('frame_captured', { size: base64Data.length });
      return base64Data;

    } catch (error) {
      this.emit('capture_error', error);
      console.error('Frame capture failed:', error);
      return null;
    }
  }

  /**
   * Get video element for display
   */
  getVideoElement(): HTMLVideoElement | null {
    return this.videoElement;
  }

  /**
   * Get current video stream
   */
  getStream(): MediaStream | null {
    return this.stream;
  }

  /**
   * Check if camera is active
   */
  isActive(): boolean {
    return this.stream !== null && this.videoElement !== null;
  }

  /**
   * Get video dimensions
   */
  getDimensions(): { width: number; height: number } {
    return {
      width: this.config.width,
      height: this.config.height
    };
  }

  /**
   * Update video configuration
   */
  updateConfig(newConfig: Partial<VideoConfig>): void {
    this.config = { ...this.config, ...newConfig };

    // Update canvas if dimensions changed
    if (newConfig.width || newConfig.height) {
      this.setupCanvas();
    }
  }

  /**
   * Get available camera devices
   */
  async getAvailableDevices(): Promise<MediaDeviceInfo[]> {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      return devices.filter(device => device.kind === 'videoinput');
    } catch (error) {
      console.error('Failed to enumerate devices:', error);
      return [];
    }
  }

  /**
   * Switch to specific camera device
   */
  async switchCamera(deviceId: string): Promise<void> {
    const wasActive = this.isActive();

    if (wasActive) {
      this.stopCamera();
    }

    // Update constraints to use specific device
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        deviceId: { exact: deviceId },
        width: { ideal: this.config.width },
        height: { ideal: this.config.height },
        frameRate: { ideal: this.config.frameRate }
      },
      audio: false
    });

    this.stream = stream;

    if (this.videoElement) {
      this.videoElement.srcObject = stream;
    }

    this.emit('camera_switched', { deviceId });
  }

  /**
   * Register event listener
   */
  on(eventType: string, callback: EventCallback): void {
    if (!this.eventListeners.has(eventType)) {
      this.eventListeners.set(eventType, []);
    }
    this.eventListeners.get(eventType)!.push(callback);
  }

  /**
   * Unregister event listener
   */
  off(eventType: string, callback: EventCallback): void {
    const listeners = this.eventListeners.get(eventType);
    if (listeners) {
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  /**
   * Setup canvas for frame capture
   */
  private setupCanvas(): void {
    this.canvasElement = document.createElement('canvas');
    this.canvasElement.width = this.config.width;
    this.canvasElement.height = this.config.height;
    this.context = this.canvasElement.getContext('2d');

    if (!this.context) {
      throw new Error('Failed to get canvas 2D context');
    }
  }

  /**
   * Emit event to listeners
   */
  private emit(eventType: string, data: any): void {
    const listeners = this.eventListeners.get(eventType);
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback();
        } catch (error) {
          console.error(`Error in ${eventType} listener:`, error);
        }
      });
    }
  }
}

/**
 * Create a configured camera service instance
 */
export function createCameraService(config: Partial<VideoConfig> = {}): CameraService {
  const defaultConfig: VideoConfig = {
    width: 320,
    height: 240,
    frameRate: 15,
    quality: 0.7,
    ...config
  };

  return new CameraService(defaultConfig);
}