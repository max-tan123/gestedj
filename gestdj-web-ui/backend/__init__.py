"""
GesteDJ Web Backend

This package provides a modular backend for the GesteDJ web interface,
handling gesture recognition, MIDI output, and WebSocket communication.

Author: GesteDJ Team
Version: 1.0.0
"""

# Version information
__version__ = "1.0.0"
__author__ = "GesteDJ Team"
__email__ = "team@gestdj.com"
__description__ = "Web backend for GesteDJ gesture-controlled DJ software"

# ========================================
# Core Imports
# ========================================

# Configuration
from .config.settings import (
    AppConfig,
    get_config,
    reload_config,
    apply_development_config,
    apply_production_config,
    apply_testing_config
)

# Models
from .models.gesture_data import (
    GestureData,
    HandLandmarks,
    GestureInfo,
    Landmark,
    ProcessingStats,
    FrameData,
    ClientMessage,
    ServerResponse,
    GestureType,
    create_empty_gesture_data,
    create_landmark_from_mediapipe,
    create_hand_landmarks_from_mediapipe
)

# Services
from .services.gesture_processor import (
    GestureProcessor,
    ProcessingResult,
    create_gesture_processor
)

# ========================================
# Public API
# ========================================

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__email__",
    "__description__",

    # Configuration
    "AppConfig",
    "get_config",
    "reload_config",
    "apply_development_config",
    "apply_production_config",
    "apply_testing_config",

    # Models
    "GestureData",
    "HandLandmarks",
    "GestureInfo",
    "Landmark",
    "ProcessingStats",
    "FrameData",
    "ClientMessage",
    "ServerResponse",
    "GestureType",
    "create_empty_gesture_data",
    "create_landmark_from_mediapipe",
    "create_hand_landmarks_from_mediapipe",

    # Services
    "GestureProcessor",
    "ProcessingResult",
    "create_gesture_processor",
]

# ========================================
# Module Documentation
# ========================================

def get_module_info():
    """
    Get information about all available modules in the backend

    Returns:
        dict: Module information including descriptions and dependencies
    """
    return {
        "config": {
            "description": "Configuration management for the backend",
            "modules": ["settings"],
            "dependencies": ["dataclasses", "os"]
        },
        "models": {
            "description": "Data models for gesture recognition and communication",
            "modules": ["gesture_data"],
            "dependencies": ["dataclasses", "enum", "typing"]
        },
        "services": {
            "description": "Core business logic services",
            "modules": ["gesture_processor"],
            "dependencies": ["mediapipe", "opencv-python", "numpy"]
        },
        "handlers": {
            "description": "WebSocket message handlers",
            "modules": ["websocket_handler"],
            "dependencies": ["websockets", "asyncio"]
        },
        "utils": {
            "description": "Utility functions and helpers",
            "modules": ["logging", "performance"],
            "dependencies": ["logging", "time"]
        }
    }

def check_dependencies():
    """
    Check if all required dependencies are available

    Returns:
        dict: Status of each dependency
    """
    dependencies = {
        "mediapipe": False,
        "opencv-python": False,
        "numpy": False,
        "websockets": False,
        "rtmidi": False
    }

    try:
        import mediapipe
        dependencies["mediapipe"] = True
    except ImportError:
        pass

    try:
        import cv2
        dependencies["opencv-python"] = True
    except ImportError:
        pass

    try:
        import numpy
        dependencies["numpy"] = True
    except ImportError:
        pass

    try:
        import websockets
        dependencies["websockets"] = True
    except ImportError:
        pass

    try:
        import rtmidi
        dependencies["rtmidi"] = True
    except ImportError:
        pass

    return dependencies

def get_system_info():
    """
    Get comprehensive system information for debugging

    Returns:
        dict: System information including dependencies and configuration
    """
    import sys
    import platform

    return {
        "version": __version__,
        "python_version": sys.version,
        "platform": platform.platform(),
        "dependencies": check_dependencies(),
        "modules": get_module_info(),
        "config_valid": get_config().validate()
    }

# ========================================
# Initialization
# ========================================

def initialize_backend(environment: str = "development"):
    """
    Initialize the backend with appropriate configuration

    Args:
        environment: Environment name ("development", "production", "testing")

    Returns:
        bool: True if initialization successful
    """
    try:
        # Apply environment-specific configuration
        if environment == "development":
            apply_development_config()
        elif environment == "production":
            apply_production_config()
        elif environment == "testing":
            apply_testing_config()
        else:
            raise ValueError(f"Unknown environment: {environment}")

        # Validate configuration
        config = get_config()
        if not config.validate():
            raise ValueError("Configuration validation failed")

        # Check critical dependencies
        deps = check_dependencies()
        if not deps["websockets"]:
            raise ImportError("websockets library is required")

        print(f"✅ GesteDJ Backend v{__version__} initialized successfully")
        print(f"Environment: {environment}")
        print(f"MediaPipe available: {deps['mediapipe']}")
        print(f"RTMIDI available: {deps['rtmidi']}")

        return True

    except Exception as e:
        print(f"❌ Backend initialization failed: {e}")
        return False

# ========================================
# Logging Setup
# ========================================

def setup_logging():
    """Set up logging configuration"""
    import logging
    import sys

    config = get_config()

    # Create formatter
    formatter = logging.Formatter(config.logging.format)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.logging.level))
    root_logger.addHandler(console_handler)

    # Add file handler if enabled
    if config.logging.log_to_file:
        file_handler = logging.FileHandler(config.logging.log_file_path)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

# Initialize logging when module is imported
setup_logging()