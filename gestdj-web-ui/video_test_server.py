#!/usr/bin/env python3
"""
Enhanced WebSocket server with live camera feed for realistic latency testing
This simulates the actual video streaming we'll need for the UI
"""

import asyncio
import websockets
import json
import logging
import time
import cv2
import base64
import threading
from typing import Set, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoStreamServer:
    def __init__(self, host="localhost", port=8765, camera_id=0):
        self.host = host
        self.port = port
        self.camera_id = camera_id
        self.clients: Set = set()
        self.running = False

        # Camera setup
        self.cap = None
        self.video_thread = None
        self.frame_lock = threading.Lock()
        self.current_frame = None
        self.frame_timestamp = 0

        # Performance tracking
        self.frames_sent = 0
        self.start_time = time.time()

    def init_camera(self):
        """Initialize camera capture"""
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            if not self.cap.isOpened():
                logger.error(f"Failed to open camera {self.camera_id}")
                return False

            # Set camera properties for better performance
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)

            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.cap.get(cv2.CAP_PROP_FPS)

            logger.info(f"✅ Camera initialized: {width}x{height} @ {fps}fps")
            return True

        except Exception as e:
            logger.error(f"Camera initialization failed: {e}")
            return False

    def capture_frames(self):
        """Capture frames in a separate thread"""
        logger.info("📹 Starting camera capture thread")
        frame_count = 0

        while self.running:
            if self.cap is None:
                break

            ret, frame = self.cap.read()
            if not ret:
                logger.warning("Failed to read frame from camera")
                continue

            # Resize frame for better WebSocket performance
            frame_resized = cv2.resize(frame, (320, 240))

            # Encode frame as JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
            _, buffer = cv2.imencode('.jpg', frame_resized, encode_param)

            # Convert to base64
            frame_b64 = base64.b64encode(buffer).decode('utf-8')

            # Update current frame (thread-safe)
            with self.frame_lock:
                self.current_frame = frame_b64
                self.frame_timestamp = time.time() * 1000  # milliseconds

            frame_count += 1
            if frame_count % 30 == 0:  # Log every 30 frames
                logger.info(f"📹 Captured {frame_count} frames, current frame size: {len(frame_b64)} chars")

            time.sleep(1/30)  # ~30 FPS

    async def register_client(self, websocket):
        """Handle new client connections"""
        self.clients.add(websocket)
        client_addr = websocket.remote_address
        logger.info(f"📱 Client connected from {client_addr}")

        try:
            # Send welcome message
            welcome_msg = {
                "type": "connection_established",
                "message": "Connected to GesteDJ Video Test Server",
                "server_timestamp": time.time() * 1000,
                "video_enabled": self.cap is not None
            }
            await websocket.send(json.dumps(welcome_msg))

            # Listen for messages from client
            async for message in websocket:
                try:
                    receive_time = time.time() * 1000
                    data = json.loads(message)

                    # Handle different message types
                    if data.get("type") == "latency_test":
                        response = {
                            "type": "latency_response",
                            "client_timestamp": data.get("timestamp", 0),
                            "server_receive_time": receive_time,
                            "server_send_time": time.time() * 1000,
                            "round_trip_data": data.get("test_data", "")
                        }
                        await websocket.send(json.dumps(response))

                    elif data.get("type") == "request_frame":
                        # Send current video frame
                        with self.frame_lock:
                            if self.current_frame:
                                frame_response = {
                                    "type": "video_frame",
                                    "frame_data": self.current_frame,
                                    "frame_timestamp": self.frame_timestamp,
                                    "server_send_time": time.time() * 1000
                                }
                                await websocket.send(json.dumps(frame_response))
                                self.frames_sent += 1

                    elif data.get("type") == "start_video_stream":
                        # Start continuous video streaming
                        logger.info(f"Starting video stream for client {client_addr}")
                        # Start streaming in background task instead of blocking
                        asyncio.create_task(self.stream_video_to_client(websocket))

                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received: {message}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"📱 Client {client_addr} disconnected")
        except Exception as e:
            logger.error(f"Client handling error: {e}")
        finally:
            self.clients.discard(websocket)

    async def stream_video_to_client(self, websocket):
        """Stream video frames continuously to a client"""
        logger.info(f"📺 Starting video stream to client {websocket.remote_address}")
        frames_streamed = 0

        try:
            while websocket in self.clients:
                with self.frame_lock:
                    if self.current_frame:
                        frame_data = {
                            "type": "video_stream",
                            "frame_data": self.current_frame,
                            "frame_timestamp": self.frame_timestamp,
                            "server_send_time": time.time() * 1000,
                            "frame_number": self.frames_sent
                        }
                        await websocket.send(json.dumps(frame_data))
                        self.frames_sent += 1
                        frames_streamed += 1

                        if frames_streamed % 15 == 0:  # Log every 15 frames
                            logger.info(f"📺 Streamed {frames_streamed} frames to client")

                await asyncio.sleep(1/15)  # Stream at 15fps to reduce bandwidth

        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Video streaming error: {e}")

    async def start_server(self):
        """Start the WebSocket server"""
        logger.info(f"Starting video streaming server on {self.host}:{self.port}")

        # Initialize camera
        if not self.init_camera():
            logger.warning("⚠️ Camera initialization failed - continuing without video")
        else:
            # Start video capture thread
            self.running = True
            self.video_thread = threading.Thread(target=self.capture_frames, daemon=True)
            self.video_thread.start()

        # Start WebSocket server
        async with websockets.serve(self.register_client, self.host, self.port):
            logger.info("✅ Video WebSocket server started successfully")
            logger.info("📹 Camera feed ready for streaming")
            logger.info("Waiting for frontend connections...")

            # Performance monitoring
            asyncio.create_task(self.monitor_performance())

            # Keep server running
            await asyncio.Future()

    async def monitor_performance(self):
        """Monitor and log performance statistics"""
        while True:
            await asyncio.sleep(10)  # Log every 10 seconds

            if self.frames_sent > 0:
                elapsed = time.time() - self.start_time
                fps = self.frames_sent / elapsed
                logger.info(f"📊 Performance: {fps:.1f} fps average, {len(self.clients)} clients, {self.frames_sent} frames sent")

    def cleanup(self):
        """Clean up resources"""
        self.running = False

        if self.cap:
            self.cap.release()
            logger.info("Camera released")

        if self.video_thread and self.video_thread.is_alive():
            self.video_thread.join(timeout=2.0)

async def main():
    """Main function to run the video test server"""
    server = VideoStreamServer()

    try:
        await server.start_server()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
    finally:
        server.cleanup()

if __name__ == "__main__":
    try:
        print("🚀 Starting GesteDJ Video Streaming Test Server")
        print("This server captures live camera feed and streams via WebSocket")
        print("Camera will be used for realistic latency testing")
        print("Press Ctrl+C to stop")
        print("-" * 60)

        asyncio.run(main())

    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")