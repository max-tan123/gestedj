#!/usr/bin/env python3
"""
GesteDJ Backend Integration - Phase 2
Connects the web UI to actual MediaPipe gesture processing
This serves as a bridge between the original app.py logic and the new web interface
"""

import asyncio
import websockets
import json
import logging
import time
import base64
import cv2
import numpy as np
from typing import Set, Optional
import sys
import os

# Add the parent directory to path to import from the original codebase
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# First, test MediaPipe and MIDI imports separately
try:
    import mediapipe as mp
    HAS_MEDIAPIPE = True
    print("✅ MediaPipe available")
except ImportError as e:
    print(f"⚠️ MediaPipe not available: {e}")
    HAS_MEDIAPIPE = False

try:
    import rtmidi
    HAS_RTMIDI = True
    print("✅ python-rtmidi available")
except ImportError as e:
    print(f"⚠️ python-rtmidi not available: {e}")
    HAS_RTMIDI = False

# Try to import from the original GesteDJ codebase
try:
    from utils.midi_virtual_device import MIDIVirtualDevice
    HAS_ORIGINAL_MIDI = True
    print("✅ Original MIDI virtual device available")
except ImportError as e:
    print(f"⚠️ Original MIDI virtual device not available: {e}")
    print("Will create a simple MIDI device simulation")
    HAS_ORIGINAL_MIDI = False

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GesteDJWebBackend:
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.clients: Set = set()

        # Statistics tracking
        self.frames_processed = 0
        self.gestures_detected = 0
        self.start_time = time.time()

        # MediaPipe setup (if available)
        self.mp_hands = None
        self.hands = None
        self.midi_device = None

        if HAS_MEDIAPIPE:
            self.setup_mediapipe()

        if HAS_ORIGINAL_MIDI or HAS_RTMIDI:
            self.setup_midi()

        # Gesture state tracking
        self.current_gesture_data = {
            "left_hand": {"active": False, "landmarks": [], "gesture": "none"},
            "right_hand": {"active": False, "landmarks": [], "gesture": "none"},
            "controls": {"filter": 0.5, "low": 1.0, "mid": 1.0, "high": 1.0, "volume": 0.8}
        }

    def setup_mediapipe(self):
        """Initialize MediaPipe hands detection"""
        try:
            self.mp_hands = mp.solutions.hands
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.5
            )
            logger.info("✅ MediaPipe hands initialized")
        except Exception as e:
            logger.error(f"Failed to initialize MediaPipe: {e}")
            self.mp_hands = None
            self.hands = None

    def setup_midi(self):
        """Initialize MIDI virtual device"""
        try:
            if HAS_ORIGINAL_MIDI:
                self.midi_device = MIDIVirtualDevice()
                logger.info("✅ Original MIDI virtual device initialized")
            elif HAS_RTMIDI:
                # Create a simple MIDI device simulation
                logger.info("✅ MIDI simulation mode (rtmidi available)")
                self.midi_device = "simulated"
            else:
                logger.info("ℹ️ No MIDI device available")
                self.midi_device = None
        except Exception as e:
            logger.error(f"Failed to initialize MIDI device: {e}")
            self.midi_device = None

    def process_frame_with_mediapipe(self, frame):
        """Process frame with MediaPipe and return gesture data"""
        if not self.hands:
            return None

        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)

        gesture_data = {
            "hands_detected": 0,
            "landmarks": [],
            "gestures": {},
            "processing_time": 0
        }

        if results.multi_hand_landmarks:
            gesture_data["hands_detected"] = len(results.multi_hand_landmarks)

            for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                # Convert landmarks to list format
                landmarks_list = []
                for landmark in hand_landmarks.landmark:
                    landmarks_list.append({
                        "x": landmark.x,
                        "y": landmark.y,
                        "z": landmark.z
                    })

                gesture_data["landmarks"].append({
                    "hand_index": hand_idx,
                    "landmarks": landmarks_list
                })

                # Simple gesture recognition (finger counting)
                fingers_up = self.count_fingers(landmarks_list)
                gesture_data["gestures"][f"hand_{hand_idx}"] = {
                    "fingers_up": fingers_up,
                    "gesture_type": self.classify_gesture(fingers_up, landmarks_list)
                }

        return gesture_data

    def count_fingers(self, landmarks):
        """Count extended fingers from landmarks"""
        if len(landmarks) < 21:
            return 0

        # Finger tip and pip landmarks
        tip_ids = [4, 8, 12, 16, 20]  # Thumb, Index, Middle, Ring, Pinky tips
        pip_ids = [3, 6, 10, 14, 18]  # Corresponding PIP joints

        fingers = []

        # Thumb (special case - check x coordinate)
        if landmarks[tip_ids[0]]["x"] > landmarks[pip_ids[0]]["x"]:
            fingers.append(1)
        else:
            fingers.append(0)

        # Other fingers (check y coordinate)
        for i in range(1, 5):
            if landmarks[tip_ids[i]]["y"] < landmarks[pip_ids[i]]["y"]:
                fingers.append(1)
            else:
                fingers.append(0)

        return sum(fingers)

    def classify_gesture(self, fingers_up, landmarks):
        """Classify gesture based on finger count and positions"""
        if fingers_up == 0:
            return "fist"
        elif fingers_up == 1:
            return "filter_control"
        elif fingers_up == 2:
            return "low_eq"
        elif fingers_up == 3:
            return "mid_eq"
        elif fingers_up == 4:
            return "high_eq"
        elif fingers_up == 5:
            return "open_hand"
        else:
            return "unknown"

    async def handle_client(self, websocket):
        """Handle a client connection"""
        self.clients.add(websocket)
        client_addr = websocket.remote_address
        logger.info(f"📱 Client connected: {client_addr}")

        try:
            # Send welcome message
            welcome_msg = {
                "type": "connection_established",
                "message": "Connected to GesteDJ Backend",
                "mediapipe_available": HAS_MEDIAPIPE,
                "midi_available": self.midi_device is not None,
                "rtmidi_available": HAS_RTMIDI,
                "original_midi_available": HAS_ORIGINAL_MIDI,
                "server_timestamp": time.time() * 1000
            }
            await websocket.send(json.dumps(welcome_msg))

            # Listen for messages
            async for message in websocket:
                try:
                    receive_time = time.time() * 1000
                    data = json.loads(message)

                    if data.get("type") == "frontend_video_frame":
                        await self.process_video_frame(websocket, data, receive_time)
                    elif data.get("type") == "video_latency_test":
                        await self.handle_latency_test(websocket, data, receive_time)
                    elif data.get("type") == "latency_test":
                        await self.handle_simple_latency_test(websocket, data, receive_time)

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"📱 Client {client_addr} disconnected")
        except Exception as e:
            logger.error(f"Client handling error: {e}")
        finally:
            self.clients.discard(websocket)

    async def process_video_frame(self, websocket, frame_data, receive_time):
        """Process video frame and return results with overlays"""
        try:
            processing_start = time.time()

            # Decode frame
            frame_bytes = base64.b64decode(frame_data["frame_data"])
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                raise ValueError("Failed to decode frame")

            # Process with MediaPipe (if available)
            gesture_data = None
            processed_frame = frame.copy()

            if HAS_MEDIAPIPE and self.hands:
                gesture_data = self.process_frame_with_mediapipe(frame)

                # Draw landmarks and gestures on frame
                if gesture_data and gesture_data["landmarks"]:
                    processed_frame = self.draw_landmarks_on_frame(processed_frame, gesture_data)

            self.frames_processed += 1
            if gesture_data and gesture_data.get("hands_detected", 0) > 0:
                self.gestures_detected += 1

            # Encode processed frame back to base64
            _, buffer = cv2.imencode('.jpg', processed_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            processed_frame_b64 = base64.b64encode(buffer).decode('utf-8')

            processing_time = (time.time() - processing_start) * 1000

            # Send response with processed frame and gesture data
            response = {
                "type": "video_frame_processed",
                "frame_number": frame_data.get("frame_number", 0),
                "client_timestamp": frame_data.get("client_timestamp"),
                "server_receive_time": receive_time,
                "server_send_time": time.time() * 1000,
                "processing_time": processing_time,
                "processed_frame": processed_frame_b64,
                "gesture_data": gesture_data,
                "stats": {
                    "frames_processed": self.frames_processed,
                    "gestures_detected": self.gestures_detected,
                    "detection_rate": self.gestures_detected / max(self.frames_processed, 1)
                }
            }

            await websocket.send(json.dumps(response))

            # Log statistics
            if self.frames_processed % 30 == 0:
                elapsed = time.time() - self.start_time
                fps = self.frames_processed / elapsed if elapsed > 0 else 0
                logger.info(
                    f"📊 Processed {self.frames_processed} frames | "
                    f"{fps:.1f} FPS | "
                    f"{self.gestures_detected} gestures | "
                    f"Processing: {processing_time:.1f}ms"
                )

        except Exception as e:
            logger.error(f"Error processing video frame: {e}")

    def draw_landmarks_on_frame(self, frame, gesture_data):
        """Draw hand landmarks and gesture info on frame"""
        if not gesture_data or not gesture_data["landmarks"]:
            return frame

        height, width = frame.shape[:2]

        for hand_data in gesture_data["landmarks"]:
            hand_idx = hand_data["hand_index"]
            landmarks = hand_data["landmarks"]

            # Draw landmarks
            for i, landmark in enumerate(landmarks):
                x = int(landmark["x"] * width)
                y = int(landmark["y"] * height)

                # Draw landmark point
                cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)

                # Draw landmark number for key points
                if i in [0, 4, 8, 12, 16, 20]:  # Wrist and fingertips
                    cv2.putText(frame, str(i), (x + 5, y - 5),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)

            # Draw connections between landmarks
            connections = [
                (0, 1), (1, 2), (2, 3), (3, 4),  # Thumb
                (0, 5), (5, 6), (6, 7), (7, 8),  # Index
                (0, 9), (9, 10), (10, 11), (11, 12),  # Middle
                (0, 13), (13, 14), (14, 15), (15, 16),  # Ring
                (0, 17), (17, 18), (18, 19), (19, 20),  # Pinky
                (5, 9), (9, 13), (13, 17)  # Palm connections
            ]

            for start_idx, end_idx in connections:
                if start_idx < len(landmarks) and end_idx < len(landmarks):
                    start_point = (
                        int(landmarks[start_idx]["x"] * width),
                        int(landmarks[start_idx]["y"] * height)
                    )
                    end_point = (
                        int(landmarks[end_idx]["x"] * width),
                        int(landmarks[end_idx]["y"] * height)
                    )
                    cv2.line(frame, start_point, end_point, (0, 255, 0), 1)

            # Draw gesture info
            if f"hand_{hand_idx}" in gesture_data["gestures"]:
                gesture_info = gesture_data["gestures"][f"hand_{hand_idx}"]
                text = f"Hand {hand_idx}: {gesture_info['fingers_up']} fingers ({gesture_info['gesture_type']})"
                cv2.putText(frame, text, (10, 30 + hand_idx * 30),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        return frame

    async def handle_latency_test(self, websocket, test_data, receive_time):
        """Handle video latency test"""
        try:
            response = {
                "type": "video_latency_response",
                "test_id": test_data.get("test_id"),
                "client_timestamp": test_data.get("timestamp"),
                "server_receive_time": receive_time,
                "server_send_time": time.time() * 1000
            }
            await websocket.send(json.dumps(response))
        except Exception as e:
            logger.error(f"Error handling latency test: {e}")

    async def handle_simple_latency_test(self, websocket, test_data, receive_time):
        """Handle simple latency test"""
        try:
            response = {
                "type": "latency_response",
                "client_timestamp": test_data.get("timestamp", 0),
                "server_receive_time": receive_time,
                "server_send_time": time.time() * 1000,
                "round_trip_data": test_data.get("test_data", "")
            }
            await websocket.send(json.dumps(response))
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected during latency test")
        except Exception as e:
            logger.error(f"Error handling simple latency test: {e}")

    async def start_server(self):
        """Start the WebSocket server"""
        logger.info(f"Starting GesteDJ backend on {self.host}:{self.port}")
        logger.info(f"MediaPipe available: {HAS_MEDIAPIPE}")
        logger.info(f"RTMIDI available: {HAS_RTMIDI}")
        logger.info(f"Original MIDI device available: {HAS_ORIGINAL_MIDI}")
        logger.info(f"MIDI device initialized: {self.midi_device is not None}")

        async with websockets.serve(self.handle_client, self.host, self.port):
            logger.info("✅ GesteDJ backend server started successfully")
            logger.info("🎥 Ready for video processing and gesture recognition...")

            # Keep server running
            await asyncio.Future()

async def main():
    """Main function to run the GesteDJ backend"""
    backend = GesteDJWebBackend()
    await backend.start_server()

if __name__ == "__main__":
    try:
        print("🚀 Starting GesteDJ Web Backend (MediaPipe Integration)")
        print("This server processes video frames with real gesture recognition")
        print("Connects web UI to original GesteDJ functionality")
        print("Press Ctrl+C to stop")
        print("-" * 60)

        asyncio.run(main())

    except KeyboardInterrupt:
        print("\n👋 GesteDJ backend stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")