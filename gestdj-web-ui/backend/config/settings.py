"""
Configuration settings for GesteDJ Web Backend

This module contains all configuration settings for the GesteDJ backend,
including server settings, MediaPipe configuration, and MIDI device settings.

Author: GesteDJ Team
Version: 1.0.0
"""

import os
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class ServerConfig:
    """WebSocket server configuration"""
    host: str = "localhost"
    port: int = 8765
    max_connections: int = 10
    ping_interval: Optional[float] = None
    ping_timeout: Optional[float] = None


@dataclass
class MediaPipeConfig:
    """MediaPipe hands detection configuration"""
    static_image_mode: bool = False
    max_num_hands: int = 2
    min_detection_confidence: float = 0.7
    min_tracking_confidence: float = 0.5
    model_complexity: int = 1


@dataclass
class VideoConfig:
    """Video processing configuration"""
    max_frame_size: int = 1024 * 1024  # 1MB
    supported_formats: list = None
    jpeg_quality: int = 80
    processing_timeout: float = 5.0  # seconds

    def __post_init__(self):
        if self.supported_formats is None:
            self.supported_formats = ['jpeg', 'jpg', 'png']


@dataclass
class MIDIConfig:
    """MIDI device configuration"""
    device_name: str = "AI_DJ_Gestures"
    enable_original_device: bool = True
    enable_simulation: bool = True
    output_channel_1: int = 0
    output_channel_2: int = 1


@dataclass
class GestureConfig:
    """Gesture recognition configuration"""
    finger_curl_threshold: float = 35.0  # degrees
    gesture_smoothing_frames: int = 3
    confidence_threshold: float = 0.8
    max_processing_time: float = 50.0  # milliseconds


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_to_file: bool = False
    log_file_path: str = "gestdj_backend.log"
    max_log_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


@dataclass
class PerformanceConfig:
    """Performance and monitoring configuration"""
    stats_reporting_interval: float = 15.0  # seconds
    max_frame_queue_size: int = 100
    enable_performance_monitoring: bool = True
    frame_processing_timeout: float = 100.0  # milliseconds


class AppConfig:
    """Main application configuration"""

    def __init__(self):
        self.server = ServerConfig()
        self.mediapipe = MediaPipeConfig()
        self.video = VideoConfig()
        self.midi = MIDIConfig()
        self.gesture = GestureConfig()
        self.logging = LoggingConfig()
        self.performance = PerformanceConfig()

        # Load environment overrides
        self._load_environment_overrides()

    def _load_environment_overrides(self):
        """Load configuration overrides from environment variables"""

        # Server configuration
        if os.getenv('GESTDJ_HOST'):
            self.server.host = os.getenv('GESTDJ_HOST')
        if os.getenv('GESTDJ_PORT'):
            self.server.port = int(os.getenv('GESTDJ_PORT'))

        # MediaPipe configuration
        if os.getenv('GESTDJ_MAX_HANDS'):
            self.mediapipe.max_num_hands = int(os.getenv('GESTDJ_MAX_HANDS'))
        if os.getenv('GESTDJ_DETECTION_CONFIDENCE'):
            self.mediapipe.min_detection_confidence = float(os.getenv('GESTDJ_DETECTION_CONFIDENCE'))

        # Logging configuration
        if os.getenv('GESTDJ_LOG_LEVEL'):
            self.logging.level = os.getenv('GESTDJ_LOG_LEVEL')
        if os.getenv('GESTDJ_LOG_TO_FILE'):
            self.logging.log_to_file = os.getenv('GESTDJ_LOG_TO_FILE').lower() == 'true'

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'server': self.server.__dict__,
            'mediapipe': self.mediapipe.__dict__,
            'video': self.video.__dict__,
            'midi': self.midi.__dict__,
            'gesture': self.gesture.__dict__,
            'logging': self.logging.__dict__,
            'performance': self.performance.__dict__
        }

    def validate(self) -> bool:
        """Validate configuration settings"""
        try:
            # Validate server settings
            assert 1 <= self.server.port <= 65535, "Port must be between 1 and 65535"
            assert self.server.max_connections > 0, "Max connections must be positive"

            # Validate MediaPipe settings
            assert 1 <= self.mediapipe.max_num_hands <= 4, "Max hands must be between 1 and 4"
            assert 0.0 <= self.mediapipe.min_detection_confidence <= 1.0, "Detection confidence must be between 0 and 1"
            assert 0.0 <= self.mediapipe.min_tracking_confidence <= 1.0, "Tracking confidence must be between 0 and 1"

            # Validate video settings
            assert self.video.max_frame_size > 0, "Max frame size must be positive"
            assert 1 <= self.video.jpeg_quality <= 100, "JPEG quality must be between 1 and 100"

            # Validate gesture settings
            assert 0.0 <= self.gesture.finger_curl_threshold <= 180.0, "Finger curl threshold must be between 0 and 180 degrees"
            assert self.gesture.gesture_smoothing_frames > 0, "Gesture smoothing frames must be positive"

            return True

        except AssertionError as e:
            print(f"Configuration validation failed: {e}")
            return False


# Global configuration instance
config = AppConfig()


def get_config() -> AppConfig:
    """Get the global configuration instance"""
    return config


def reload_config():
    """Reload configuration from environment"""
    global config
    config = AppConfig()


# Configuration presets for different environments
def apply_development_config():
    """Apply development environment configuration"""
    config.logging.level = "DEBUG"
    config.performance.enable_performance_monitoring = True
    config.server.host = "localhost"


def apply_production_config():
    """Apply production environment configuration"""
    config.logging.level = "WARNING"
    config.logging.log_to_file = True
    config.performance.enable_performance_monitoring = False
    config.server.host = "0.0.0.0"


def apply_testing_config():
    """Apply testing environment configuration"""
    config.logging.level = "ERROR"
    config.server.port = 8766  # Different port for testing
    config.performance.enable_performance_monitoring = False