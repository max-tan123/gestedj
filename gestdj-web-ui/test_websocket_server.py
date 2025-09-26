#!/usr/bin/env python3
"""
Minimal WebSocket server for testing Tauri + Python connection
This is a separate test script that doesn't modify the original app.py
"""

import asyncio
import websockets
import json
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GesteDJTestServer:
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.clients = set()

    async def register_client(self, websocket):
        """Handle new client connections"""
        self.clients.add(websocket)
        logger.info(f"Client connected from {websocket.remote_address}")

        try:
            # Send welcome message with server timestamp
            welcome_msg = {
                "type": "connection_established",
                "message": "Connected to GesteDJ Test Server",
                "server_timestamp": time.time() * 1000  # milliseconds
            }
            await websocket.send(json.dumps(welcome_msg))

            # Listen for messages from client
            async for message in websocket:
                try:
                    receive_time = time.time() * 1000  # milliseconds
                    data = json.loads(message)
                    logger.info(f"Received message: {data}")

                    # Handle latency test messages
                    if data.get("type") == "latency_test":
                        response = {
                            "type": "latency_response",
                            "client_timestamp": data.get("timestamp", 0),
                            "server_receive_time": receive_time,
                            "server_send_time": time.time() * 1000,
                            "round_trip_data": data.get("test_data", "")
                        }
                    else:
                        # Echo back for testing
                        response = {
                            "type": "echo",
                            "original_message": data,
                            "server_response": "Message received successfully",
                            "server_timestamp": time.time() * 1000
                        }
                    await websocket.send(json.dumps(response))

                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received: {message}")

        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected")
        finally:
            self.clients.remove(websocket)

    async def start_server(self):
        """Start the WebSocket server"""
        logger.info(f"Starting GesteDJ test server on {self.host}:{self.port}")

        async with websockets.serve(self.register_client, self.host, self.port):
            logger.info("✅ WebSocket server started successfully")
            logger.info("Waiting for frontend connections...")
            # Keep server running
            await asyncio.Future()  # Run forever

    async def simulate_gesture_data(self):
        """Simulate sending gesture data to connected clients"""
        while True:
            if self.clients:
                # Simulate hand landmark data
                gesture_data = {
                    "type": "gesture_update",
                    "landmarks": [
                        {"x": 100, "y": 200, "z": 0.1, "name": "wrist"},
                        {"x": 120, "y": 180, "z": 0.1, "name": "index_tip"}
                    ],
                    "gestures": {
                        "finger_count": 1,
                        "active_knob": "filter",
                        "knob_angle": 45.0
                    },
                    "controls": {
                        "filter": 0.6,
                        "low": 1.0,
                        "mid": 1.2,
                        "high": 0.8
                    },
                    "timestamp": asyncio.get_event_loop().time()
                }

                # Send to all connected clients
                disconnected = []
                for client in self.clients:
                    try:
                        await client.send(json.dumps(gesture_data))
                    except websockets.exceptions.ConnectionClosed:
                        disconnected.append(client)

                # Remove disconnected clients
                for client in disconnected:
                    self.clients.discard(client)

            await asyncio.sleep(0.1)  # Send at ~10 FPS for testing

async def main():
    """Main function to run the test server"""
    server = GesteDJTestServer()

    # Start server (it will run forever)
    await server.start_server()

if __name__ == "__main__":
    try:
        print("🚀 Starting GesteDJ WebSocket Test Server")
        print("This server simulates the Python backend for testing the Tauri frontend")
        print("Press Ctrl+C to stop")
        print("-" * 50)

        asyncio.run(main())

    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")