"""
Data models for gesture recognition

This module defines the data structures used throughout the GesteDJ backend
for representing gesture recognition results and related data.

Author: GesteDJ Team
Version: 1.0.0
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class GestureType(Enum):
    """Enumeration of supported gesture types"""
    FIST = "fist"
    FILTER_CONTROL = "filter_control"
    LOW_EQ = "low_eq"
    MID_EQ = "mid_eq"
    HIGH_EQ = "high_eq"
    OPEN_HAND = "open_hand"
    THUMBS_UP = "thumbs_up"
    PINCH = "pinch"
    UNKNOWN = "unknown"


@dataclass
class Landmark:
    """Single hand landmark point"""
    x: float
    y: float
    z: float

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary representation"""
        return {"x": self.x, "y": self.y, "z": self.z}

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'Landmark':
        """Create from dictionary representation"""
        return cls(x=data["x"], y=data["y"], z=data["z"])


@dataclass
class HandLandmarks:
    """Collection of landmarks for a single hand"""
    hand_index: int
    landmarks: List[Dict[str, float]]
    confidence: float = 1.0
    handedness: Optional[str] = None  # "Left" or "Right"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "hand_index": self.hand_index,
            "landmarks": self.landmarks,
            "confidence": self.confidence,
            "handedness": self.handedness
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HandLandmarks':
        """Create from dictionary representation"""
        return cls(
            hand_index=data["hand_index"],
            landmarks=data["landmarks"],
            confidence=data.get("confidence", 1.0),
            handedness=data.get("handedness")
        )


@dataclass
class GestureInfo:
    """Information about a recognized gesture"""
    fingers_up: int
    gesture_type: str
    confidence: float = 1.0
    angle: Optional[float] = None  # For rotational gestures
    distance: Optional[float] = None  # For pinch/distance gestures
    velocity: Optional[float] = None  # For movement gestures

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        result = {
            "fingers_up": self.fingers_up,
            "gesture_type": self.gesture_type,
            "confidence": self.confidence
        }

        if self.angle is not None:
            result["angle"] = self.angle
        if self.distance is not None:
            result["distance"] = self.distance
        if self.velocity is not None:
            result["velocity"] = self.velocity

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GestureInfo':
        """Create from dictionary representation"""
        return cls(
            fingers_up=data["fingers_up"],
            gesture_type=data["gesture_type"],
            confidence=data.get("confidence", 1.0),
            angle=data.get("angle"),
            distance=data.get("distance"),
            velocity=data.get("velocity")
        )


@dataclass
class GestureData:
    """Complete gesture recognition result"""
    hands_detected: int = 0
    landmarks: List[HandLandmarks] = field(default_factory=list)
    gestures: Dict[str, GestureInfo] = field(default_factory=dict)
    processing_time: Optional[float] = None
    timestamp: Optional[float] = None
    frame_number: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "hands_detected": self.hands_detected,
            "landmarks": [hand.to_dict() for hand in self.landmarks],
            "gestures": {key: gesture.to_dict() for key, gesture in self.gestures.items()},
            "processing_time": self.processing_time,
            "timestamp": self.timestamp,
            "frame_number": self.frame_number
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GestureData':
        """Create from dictionary representation"""
        landmarks = [HandLandmarks.from_dict(hand_data) for hand_data in data.get("landmarks", [])]
        gestures = {key: GestureInfo.from_dict(gesture_data)
                   for key, gesture_data in data.get("gestures", {}).items()}

        return cls(
            hands_detected=data.get("hands_detected", 0),
            landmarks=landmarks,
            gestures=gestures,
            processing_time=data.get("processing_time"),
            timestamp=data.get("timestamp"),
            frame_number=data.get("frame_number")
        )

    def get_primary_gesture(self) -> Optional[GestureInfo]:
        """Get the primary (first detected) gesture"""
        if not self.gestures:
            return None
        return next(iter(self.gestures.values()))

    def has_gesture_type(self, gesture_type: str) -> bool:
        """Check if any hand has the specified gesture type"""
        return any(gesture.gesture_type == gesture_type for gesture in self.gestures.values())

    def get_gestures_by_type(self, gesture_type: str) -> List[GestureInfo]:
        """Get all gestures of a specific type"""
        return [gesture for gesture in self.gestures.values()
                if gesture.gesture_type == gesture_type]


@dataclass
class ProcessingStats:
    """Statistics about gesture processing performance"""
    frames_processed: int = 0
    gestures_detected: int = 0
    detection_rate: float = 0.0
    avg_processing_time: float = 0.0
    min_processing_time: float = 0.0
    max_processing_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "frames_processed": self.frames_processed,
            "gestures_detected": self.gestures_detected,
            "detection_rate": self.detection_rate,
            "avg_processing_time": self.avg_processing_time,
            "min_processing_time": self.min_processing_time,
            "max_processing_time": self.max_processing_time
        }


@dataclass
class FrameData:
    """Data structure for video frame processing"""
    frame_number: int
    timestamp: float
    frame_data: bytes
    client_timestamp: Optional[float] = None
    processing_start_time: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation (excluding binary data)"""
        return {
            "frame_number": self.frame_number,
            "timestamp": self.timestamp,
            "frame_size": len(self.frame_data),
            "client_timestamp": self.client_timestamp,
            "processing_start_time": self.processing_start_time
        }


@dataclass
class ClientMessage:
    """Base structure for client WebSocket messages"""
    message_type: str
    timestamp: float
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "type": self.message_type,
            "timestamp": self.timestamp,
            **self.data
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClientMessage':
        """Create from dictionary representation"""
        message_data = data.copy()
        message_type = message_data.pop("type")
        timestamp = message_data.pop("timestamp", 0.0)

        return cls(
            message_type=message_type,
            timestamp=timestamp,
            data=message_data
        )


@dataclass
class ServerResponse:
    """Base structure for server WebSocket responses"""
    response_type: str
    timestamp: float
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "type": self.response_type,
            "timestamp": self.timestamp,
            **self.data
        }


# Convenience functions for common operations

def create_empty_gesture_data() -> GestureData:
    """Create an empty GestureData instance"""
    return GestureData()


def create_landmark_from_mediapipe(mp_landmark) -> Landmark:
    """Create Landmark from MediaPipe landmark object"""
    return Landmark(x=mp_landmark.x, y=mp_landmark.y, z=mp_landmark.z)


def create_hand_landmarks_from_mediapipe(hand_idx: int, mp_landmarks, confidence: float = 1.0) -> HandLandmarks:
    """Create HandLandmarks from MediaPipe results"""
    landmarks = []
    for landmark in mp_landmarks.landmark:
        landmarks.append({
            "x": landmark.x,
            "y": landmark.y,
            "z": landmark.z
        })

    return HandLandmarks(
        hand_index=hand_idx,
        landmarks=landmarks,
        confidence=confidence
    )