# Real-Time Hand Landmark Detection

This project implements real-time hand landmark detection using Google's MediaPipe library with OpenCV for video processing.

## Features

- **Real-time hand detection** with up to 2 hands simultaneously
- **21 hand landmarks** per hand with MediaPipe's hand landmark model
- **Optimized performance** with minimal lag
- **Live coordinate display** showing x, y, z positions of key landmarks
- **FPS monitoring** and performance metrics
- **Interactive controls** for customization

## Files

- `hand_detection.py` - Basic implementation with full features
- `hand_detection_optimized.py` - Performance-optimized version with controls
- `requirements.txt` - Python dependencies

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Run the hand detection:
```bash
# Basic version
python hand_detection.py

# Optimized version (recommended)
python hand_detection_optimized.py
```

## Controls (Optimized Version)

- **'q'** - Quit the application
- **'c'** - Toggle console output of landmark coordinates
- **'a'** - Toggle display of all 21 landmarks vs key landmarks only
- **'s'** - Save current frame as image

## Key Landmarks Tracked

The system tracks these important hand landmarks:

1. **Wrist (0)** - Base of the hand
2. **Thumb Tip (4)** - Tip of the thumb
3. **Index Tip (8)** - Tip of the index finger
4. **Middle Tip (12)** - Tip of the middle finger
5. **Ring Tip (16)** - Tip of the ring finger
6. **Pinky Tip (20)** - Tip of the pinky finger

## Performance Optimizations

- **Model complexity**: Uses lightweight model (complexity=0)
- **Camera settings**: Optimized resolution, FPS, and buffer size
- **Frame processing**: Efficient landmark extraction and display
- **Selective rendering**: Option to show only key landmarks
- **FPS averaging**: Smooth performance metrics

## MediaPipe Hand Landmark Model

This implementation uses Google's MediaPipe hand landmark detection which provides:
- 21 3D hand landmarks per hand
- Real-time performance on standard hardware
- Robust tracking across various lighting conditions
- Palm detection and hand landmark localization

## Coordinate System

- **x, y**: Pixel coordinates in the video frame
- **z**: Relative depth (negative values closer to camera)
- **Normalized coordinates**: Available in range [0, 1] relative to image dimensions

## Troubleshooting

- **Camera not found**: Ensure your webcam is connected and not used by other applications
- **Poor performance**: Try the optimized version or reduce video resolution
- **Detection issues**: Ensure good lighting and clear hand visibility
- **Import errors**: Make sure all dependencies are installed correctly

## References

- [MediaPipe Hand Landmark Documentation](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker)
- [MediaPipe Hand Detection Paper](https://arxiv.org/pdf/2006.10214)
- [MediaPipe GitHub Repository](https://github.com/google-ai-edge/mediapipe)

