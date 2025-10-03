"""
Gesture Recognition Service

This module handles MediaPipe-based hand gesture recognition and classification
for the GesteDJ system.

Author: GesteDJ Team
Version: 1.0.0
"""

import cv2
import numpy as np
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

from ..config.settings import get_config
from ..models.gesture_data import GestureData, HandLandmarks, GestureInfo


@dataclass
class ProcessingResult:
    """Result of gesture processing"""
    success: bool
    gesture_data: Optional[GestureData]
    processing_time: float
    error_message: Optional[str] = None


class GestureProcessor:
    """
    MediaPipe-based gesture recognition processor

    This class handles the core gesture recognition logic, including:
    - Hand landmark detection
    - Finger counting and classification
    - Gesture type identification
    - Performance monitoring
    """

    def __init__(self):
        self.config = get_config()
        self.mp_hands = None
        self.hands = None
        self.is_initialized = False

        # Performance tracking
        self.frames_processed = 0
        self.total_processing_time = 0.0
        self.gestures_detected = 0

        # Initialize MediaPipe if available
        if MEDIAPIPE_AVAILABLE:
            self._initialize_mediapipe()

    def _initialize_mediapipe(self) -> bool:
        """Initialize MediaPipe hands detection"""
        try:
            self.mp_hands = mp.solutions.hands
            self.hands = self.mp_hands.Hands(
                static_image_mode=self.config.mediapipe.static_image_mode,
                max_num_hands=self.config.mediapipe.max_num_hands,
                min_detection_confidence=self.config.mediapipe.min_detection_confidence,
                min_tracking_confidence=self.config.mediapipe.min_tracking_confidence,
                model_complexity=self.config.mediapipe.model_complexity
            )
            self.is_initialized = True
            return True

        except Exception as e:
            print(f"Failed to initialize MediaPipe: {e}")
            return False

    def process_frame(self, frame: np.ndarray) -> ProcessingResult:
        """
        Process a video frame and extract gesture data

        Args:
            frame: Input video frame (BGR format)

        Returns:
            ProcessingResult with gesture data and metadata
        """
        start_time = time.time()

        if not self.is_initialized or not MEDIAPIPE_AVAILABLE:
            return ProcessingResult(
                success=False,
                gesture_data=None,
                processing_time=0.0,
                error_message="MediaPipe not available"
            )

        try:
            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)

            # Create gesture data
            gesture_data = self._create_gesture_data(results, frame.shape)

            # Update statistics
            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            self.frames_processed += 1
            self.total_processing_time += processing_time

            if gesture_data.hands_detected > 0:
                self.gestures_detected += 1

            return ProcessingResult(
                success=True,
                gesture_data=gesture_data,
                processing_time=processing_time
            )

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return ProcessingResult(
                success=False,
                gesture_data=None,
                processing_time=processing_time,
                error_message=str(e)
            )

    def _create_gesture_data(self, results, frame_shape: Tuple[int, int, int]) -> GestureData:
        """Create GestureData from MediaPipe results"""
        gesture_data = GestureData()

        if not results.multi_hand_landmarks:
            return gesture_data

        height, width = frame_shape[:2]
        gesture_data.hands_detected = len(results.multi_hand_landmarks)

        for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
            # Convert landmarks to our format
            landmarks = []
            for landmark in hand_landmarks.landmark:
                landmarks.append({
                    "x": landmark.x,
                    "y": landmark.y,
                    "z": landmark.z
                })

            hand_landmarks_obj = HandLandmarks(
                hand_index=hand_idx,
                landmarks=landmarks
            )
            gesture_data.landmarks.append(hand_landmarks_obj)

            # Perform gesture recognition
            fingers_up = self._count_fingers(landmarks)
            gesture_type = self._classify_gesture(fingers_up, landmarks)

            gesture_info = GestureInfo(
                fingers_up=fingers_up,
                gesture_type=gesture_type
            )
            gesture_data.gestures[f"hand_{hand_idx}"] = gesture_info

        return gesture_data

    def _count_fingers(self, landmarks: List[Dict[str, float]]) -> int:
        """
        Count the number of extended fingers

        Args:
            landmarks: List of hand landmarks

        Returns:
            Number of extended fingers (0-5)
        """
        if len(landmarks) < 21:
            return 0

        # Finger tip and pip landmarks indices
        tip_ids = [4, 8, 12, 16, 20]  # Thumb, Index, Middle, Ring, Pinky tips
        pip_ids = [3, 6, 10, 14, 18]  # Corresponding PIP joints

        fingers = []

        # Thumb (special case - check x coordinate)
        # Thumb is extended if tip is further from wrist than pip
        if landmarks[tip_ids[0]]["x"] > landmarks[pip_ids[0]]["x"]:
            fingers.append(1)
        else:
            fingers.append(0)

        # Other fingers (check y coordinate)
        # Finger is extended if tip is higher than pip
        for i in range(1, 5):
            if landmarks[tip_ids[i]]["y"] < landmarks[pip_ids[i]]["y"]:
                fingers.append(1)
            else:
                fingers.append(0)

        return sum(fingers)

    def _classify_gesture(self, fingers_up: int, landmarks: List[Dict[str, float]]) -> str:
        """
        Classify gesture based on finger configuration

        Args:
            fingers_up: Number of extended fingers
            landmarks: Hand landmarks for additional analysis

        Returns:
            Gesture type string
        """
        # Basic gesture classification based on finger count
        gesture_map = {
            0: "fist",
            1: "filter_control",
            2: "low_eq",
            3: "mid_eq",
            4: "high_eq",
            5: "open_hand"
        }

        base_gesture = gesture_map.get(fingers_up, "unknown")

        # Advanced gesture recognition could be added here
        # For example: detecting specific finger combinations,
        # hand orientation, movement patterns, etc.

        return base_gesture

    def _detect_special_gestures(self, landmarks: List[Dict[str, float]]) -> Optional[str]:
        """
        Detect special gestures like thumbs up, pinch, etc.

        Args:
            landmarks: Hand landmarks

        Returns:
            Special gesture name or None
        """
        # Thumbs up detection
        thumb_tip = landmarks[4]
        thumb_ip = landmarks[3]
        index_mcp = landmarks[5]

        # Thumb is up if tip is significantly higher than other fingers
        if (thumb_tip["y"] < thumb_ip["y"] and
            thumb_tip["y"] < index_mcp["y"] - 0.1):
            return "thumbs_up"

        # Pinch detection (thumb and index finger close)
        index_tip = landmarks[8]
        thumb_index_distance = np.sqrt(
            (thumb_tip["x"] - index_tip["x"])**2 +
            (thumb_tip["y"] - index_tip["y"])**2
        )

        if thumb_index_distance < 0.05:  # Threshold for pinch
            return "pinch"

        return None

    def draw_landmarks_on_frame(self, frame: np.ndarray, gesture_data: GestureData) -> np.ndarray:
        """
        Draw hand landmarks and gesture info on frame

        Args:
            frame: Input frame
            gesture_data: Gesture data to visualize

        Returns:
            Frame with landmarks drawn
        """
        if not gesture_data.landmarks:
            return frame

        height, width = frame.shape[:2]

        for hand_data in gesture_data.landmarks:
            landmarks = hand_data.landmarks

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
            hand_idx = hand_data.hand_index
            if f"hand_{hand_idx}" in gesture_data.gestures:
                gesture_info = gesture_data.gestures[f"hand_{hand_idx}"]
                text = f"Hand {hand_idx}: {gesture_info.fingers_up} fingers ({gesture_info.gesture_type})"
                cv2.putText(frame, text, (10, 30 + hand_idx * 30),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        return frame

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get processing performance statistics"""
        if self.frames_processed == 0:
            return {
                "frames_processed": 0,
                "gestures_detected": 0,
                "avg_processing_time": 0.0,
                "detection_rate": 0.0
            }

        return {
            "frames_processed": self.frames_processed,
            "gestures_detected": self.gestures_detected,
            "avg_processing_time": self.total_processing_time / self.frames_processed,
            "detection_rate": self.gestures_detected / self.frames_processed
        }

    def reset_stats(self):
        """Reset performance statistics"""
        self.frames_processed = 0
        self.total_processing_time = 0.0
        self.gestures_detected = 0


def create_gesture_processor() -> GestureProcessor:
    """Factory function to create a gesture processor"""
    return GestureProcessor()