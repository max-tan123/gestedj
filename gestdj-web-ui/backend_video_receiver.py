#!/usr/bin/env python3
"""
Backend server that receives video frames from frontend
This simulates the real GesteDJ backend receiving video for MediaPipe processing
"""

import asyncio
import websockets
import json
import logging
import time
import base64
import cv2
import numpy as np
from typing import Set

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoReceiver:
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.clients: Set = set()

        # Statistics tracking
        self.frames_received = 0
        self.total_data_received = 0  # bytes
        self.start_time = time.time()
        self.last_frame_time = 0

        # Processing simulation
        self.process_frames = True
        self.show_preview = False  # Set to True to see received frames

    async def handle_client(self, websocket):
        """Handle a client connection and process video frames"""
        self.clients.add(websocket)
        client_addr = websocket.remote_address
        logger.info(f"📱 Client connected: {client_addr}")

        try:
            # Send welcome message
            welcome_msg = {
                "type": "connection_established",
                "message": "Connected to Video Receiver Backend",
                "server_timestamp": time.time() * 1000,
                "ready_for_video": True
            }
            await websocket.send(json.dumps(welcome_msg))

            # Listen for video frames
            async for message in websocket:
                try:
                    receive_time = time.time() * 1000
                    data = json.loads(message)

                    if data.get("type") == "frontend_video_frame":
                        await self.process_video_frame(websocket, data, receive_time)

                    elif data.get("type") == "video_latency_test":
                        await self.handle_latency_test(websocket, data, receive_time)

                    elif data.get("type") == "latency_test":
                        # Handle regular latency tests too
                        response = {
                            "type": "latency_response",
                            "client_timestamp": data.get("timestamp", 0),
                            "server_receive_time": receive_time,
                            "server_send_time": time.time() * 1000,
                            "round_trip_data": data.get("test_data", "")
                        }
                        await websocket.send(json.dumps(response))

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"📱 Client {client_addr} disconnected")
        except Exception as e:
            logger.error(f"Client handling error: {e}")
        finally:
            self.clients.discard(websocket)

    async def process_video_frame(self, websocket, frame_data, receive_time):
        """Process a received video frame (simulates MediaPipe processing)"""
        try:
            # Decode base64 frame
            frame_bytes = base64.b64decode(frame_data["frame_data"])
            self.total_data_received += len(frame_bytes)
            self.frames_received += 1

            # Simulate MediaPipe processing time
            processing_start = time.time()

            if self.process_frames:
                # Convert to OpenCV format
                nparr = np.frombuffer(frame_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if frame is not None:
                    # Simulate MediaPipe hand detection processing
                    # (In real app, this would be MediaPipe hand landmark detection)
                    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                    # Add some processing delay to simulate MediaPipe
                    await asyncio.sleep(0.001)  # 1ms simulated processing time

                    # Optional: Show preview window (for debugging)
                    if self.show_preview:
                        cv2.imshow("Backend Received Frame", frame)
                        cv2.waitKey(1)

            processing_time = (time.time() - processing_start) * 1000  # ms

            # Send acknowledgment back to frontend
            response = {
                "type": "video_frame_received",
                "frame_number": frame_data.get("frame_number", 0),
                "client_timestamp": frame_data.get("client_timestamp"),
                "server_receive_time": receive_time,
                "server_send_time": time.time() * 1000,
                "processing_time": processing_time,
                "frame_size_bytes": len(frame_bytes)
            }

            await websocket.send(json.dumps(response))

            # Log statistics periodically
            if self.frames_received % 30 == 0:  # Every 30 frames
                elapsed = time.time() - self.start_time
                fps = self.frames_received / elapsed if elapsed > 0 else 0
                data_rate = (self.total_data_received / 1024) / elapsed if elapsed > 0 else 0  # KB/s

                logger.info(
                    f"📊 Received {self.frames_received} frames | "
                    f"{fps:.1f} FPS | "
                    f"{data_rate:.1f} KB/s | "
                    f"Processing: {processing_time:.1f}ms"
                )

        except Exception as e:
            logger.error(f"Error processing video frame: {e}")

    async def handle_latency_test(self, websocket, test_data, receive_time):
        """Handle video latency test with frame processing"""
        try:
            processing_start = time.time()

            # Decode and process the test frame
            if self.process_frames and test_data.get("frame_data"):
                frame_bytes = base64.b64decode(test_data["frame_data"])
                nparr = np.frombuffer(frame_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if frame is not None:
                    # Simulate MediaPipe processing
                    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    await asyncio.sleep(0.002)  # 2ms processing simulation

            processing_time = (time.time() - processing_start) * 1000

            # Send latency test response
            response = {
                "type": "video_latency_response",
                "test_id": test_data.get("test_id"),
                "client_timestamp": test_data.get("timestamp"),
                "server_receive_time": receive_time,
                "server_send_time": time.time() * 1000,
                "processing_time": processing_time
            }

            await websocket.send(json.dumps(response))
            logger.info(f"🧪 Latency test processed: {processing_time:.1f}ms processing time")

        except Exception as e:
            logger.error(f"Error handling latency test: {e}")

    async def start_server(self):
        """Start the video receiver server"""
        logger.info(f"Starting video receiver backend on {self.host}:{self.port}")
        logger.info("Ready to receive video frames from frontend")

        async with websockets.serve(self.handle_client, self.host, self.port):
            logger.info("✅ Video receiver server started successfully")
            logger.info("🎥 Waiting for frontend video streams...")

            # Performance monitoring
            asyncio.create_task(self.monitor_performance())

            # Keep server running
            await asyncio.Future()

    async def monitor_performance(self):
        """Monitor and log performance statistics"""
        while True:
            await asyncio.sleep(15)  # Log every 15 seconds

            if self.frames_received > 0:
                elapsed = time.time() - self.start_time
                fps = self.frames_received / elapsed if elapsed > 0 else 0
                data_rate = (self.total_data_received / 1024) / elapsed if elapsed > 0 else 0
                data_total_mb = self.total_data_received / (1024 * 1024)

                logger.info(
                    f"📈 Performance Summary: "
                    f"{self.frames_received} frames | "
                    f"{fps:.1f} FPS avg | "
                    f"{data_rate:.1f} KB/s | "
                    f"{data_total_mb:.2f} MB total | "
                    f"{len(self.clients)} clients"
                )

    def cleanup(self):
        """Clean up resources"""
        if self.show_preview:
            cv2.destroyAllWindows()

async def main():
    """Main function to run the video receiver"""
    receiver = VideoReceiver()

    try:
        await receiver.start_server()
    except KeyboardInterrupt:
        logger.info("Shutting down video receiver...")
    finally:
        receiver.cleanup()

if __name__ == "__main__":
    try:
        print("🚀 Starting GesteDJ Video Receiver Backend")
        print("This backend receives video frames from frontend for processing")
        print("Simulates MediaPipe processing pipeline")
        print("Press Ctrl+C to stop")
        print("-" * 60)

        asyncio.run(main())

    except KeyboardInterrupt:
        print("\n👋 Video receiver stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")