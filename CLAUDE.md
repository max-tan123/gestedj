# GesteDJ - Codebase Analysis

## Project Overview

GesteDJ is a **gesture-controlled virtual instrument** that integrates hand gesture recognition with the Mixxx DJ software. The system uses Google's MediaPipe for hand landmark detection and translates hand gestures into MIDI messages that control DJ parameters like EQ, filters, volume, and playback controls.

## Architecture

The system follows a **three-layer architecture**:

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   Computer Vision   │───▶│   MIDI Translation  │───▶│   Mixxx Integration │
│   (Hand Detection)  │    │   (Virtual Device)  │    │   (DJ Software)     │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

## Core Components

### 1. Main Application (`app.py`)

**Purpose**: Real-time hand gesture detection and processing with visual feedback

**Key Classes**:
- `HandDetectorWithMIDI`: Main orchestrator class that handles the entire gesture-to-MIDI pipeline

**Key Technologies**:
- **MediaPipe**: Hand landmark detection (21 points per hand, up to 2 hands)
- **OpenCV**: Camera capture, image processing, and always-on-top UI window
- **Threading**: Background MIDI message sending at controlled 30Hz rate

**Gesture Recognition Logic**:
- **Finger Counting**: Uses curvature analysis and radial distance tests to determine extended fingers
- **Angle Calculation**: Calculates rotation angle between wrist (landmark 0) and index finger tip (landmark 8)
- **Hand Assignment**: Maps raw MediaPipe labels to decks (raw 'Left' → Deck 1, raw 'Right' → Deck 2)

**Supported Gestures**:
1. **EQ/Filter Control**: 1-4 extended fingers select control type, hand rotation adjusts values
   - 1 finger (index only): Filter control
   - 2 fingers (index+middle): Low EQ
   - 3 fingers (index+middle+ring): Mid EQ
   - 4 fingers (all): High EQ
2. **Volume Control**: Pinch gesture (thumb-index) with middle+ring+pinky extended, vertical movement adjusts volume
3. **Play/Pause**: Thumbs-up gesture toggles playback
4. **Effect Toggle**: "Rockstar" gesture (index+pinky only) toggles Effect Unit 1

### 2. MIDI Virtual Device (`utils/midi_virtual_device.py`)

**Purpose**: Creates system-level virtual MIDI device and handles bidirectional MIDI communication

**Key Features**:
- **Virtual MIDI Port**: Creates `AI_DJ_Gestures` device visible to Mixxx
- **Dual-Deck Support**: Independent control for Deck 1 (MIDI Channel 0) and Deck 2 (MIDI Channel 1)
- **Value Smoothing**: Exponential smoothing to reduce gesture jitter
- **Smart Throttling**: Only sends MIDI when values change by >2 to prevent message spam
- **Bidirectional Communication**: Receives feedback from Mixxx for "soft takeover" functionality

**MIDI Mapping Configuration**:
```python
# Control Change mappings per deck
'filter': {'cc1': 1, 'cc2': 5}    # Linear 0.0-1.0
'low':    {'cc1': 2, 'cc2': 6}    # Non-linear 0.0-4.0 (EQ)
'mid':    {'cc1': 3, 'cc2': 7}    # Non-linear 0.0-4.0 (EQ)
'high':   {'cc1': 4, 'cc2': 8}    # Non-linear 0.0-4.0 (EQ)
'volume': {'cc1': 9, 'cc2': 10}   # Linear 0.0-1.0

# Toggle mappings per deck
'play':     {'cc1': 0x12, 'cc2': 0x13}  # Play/Pause
'effect1':  {'cc1': 0x16, 'cc2': 0x17}  # Effect Unit enable
```

### 3. Mixxx Integration (`mixxx_utils/AI_DJ_Gestures.midi.xml`)

**Purpose**: XML configuration file that defines MIDI mappings for Mixxx

**Key Features**:
- **Dual-Deck Mapping**: Separate controls for Channel 1 and Channel 2
- **EQ Integration**: Maps to `EqualizerRack1_[ChannelN]_Effect1` parameters
- **Filter Integration**: Maps to `QuickEffectRack1_[ChannelN]` super1 parameter
- **Effect Routing**: Controls `EffectRack1_EffectUnitN` enable states
- **Bidirectional Feedback**: Sends current values back to Python app on MIDI Channel 2

## Technical Implementation Details

### Hand Gesture Recognition Algorithm

**Finger Detection**:
1. **Curvature Analysis**: Calculates bend angles between finger segments (MCP-PIP-DIP-TIP)
2. **Radial Monotonicity**: Ensures finger landmarks are progressively farther from wrist
3. **Thresholds**: Fingers with <35° total curvature and proper radial ordering are considered extended

**Angle Calculation**:
- Uses `math.atan2(-dx, dy)` between wrist and index finger tip
- Maps to -135° to +135° range for knob control
- Handles angle wraparound for smooth rotation

**Volume Gesture Detection**:
- Detects pinch: thumb-index distance < 40px with middle+ring+pinky extended
- Tracks vertical movement of pinch midpoint
- Sensitivity: -0.0035 per pixel (upward movement increases volume)

### Performance Optimizations

**Frame Processing**:
- Resizes input to max 1280px width for faster processing
- Limits MediaPipe hands to max 2 hands with optimized confidence thresholds
- Uses deque for rolling FPS calculation (30 frame history)

**MIDI Rate Limiting**:
- Background thread sends MIDI updates at controlled 30Hz
- Only sends when values change by >2 MIDI units
- Prioritizes active knob updates over inactive ones

### State Management

**Per-Deck State Isolation**:
- Independent gesture tracking for left/right hands
- Separate smoothing buffers per deck to prevent cross-talk
- Deck-specific last-sent value tracking

**Gesture State Machine**:
- `gesture_active`: True when valid finger count + pointer up detected
- `knob_locked`: Prevents value changes when pointer finger goes down
- `active_knob`: Currently selected control based on finger count

## File Structure

```
/
├── app.py                           # Main standalone application (1,551 lines)
├── utils/
│   ├── midi_virtual_device.py      # Virtual MIDI device (488 lines)
│   └── make_macos_icon.py          # Build utility
├── mixxx_utils/
│   └── AI_DJ_Gestures.midi.xml     # Mixxx MIDI mapping (345 lines)
├── gestdj-web-ui/                   # Browser-based UI implementation
│   ├── backend/                    # Python WebSocket server
│   ├── src/                        # React frontend
│   ├── gestdj_backend_integration.py  # MediaPipe + WebSocket bridge
│   └── requirements.txt            # Web-specific Python deps
├── gestdj-electron/                 # Electron desktop app
│   ├── src/main/                   # Electron main process (Node.js)
│   ├── src/renderer/               # React frontend
│   ├── package.json                # Node dependencies
│   └── CLAUDE.md                   # Electron-specific architecture docs
├── build_specs/                     # PyInstaller build configurations
├── dist/                           # Built macOS app (gitignored)
├── images/                         # Logo assets
├── tests/                          # Test utilities
├── requirements.txt                # Python dependencies for standalone app
└── documentation files
```

## Project Variants

This project has **three implementations** of the same core gesture recognition system:

### 1. Standalone Python App (`app.py`)
- **Purpose**: Original macOS desktop application
- **Tech**: Pure Python with MediaPipe, OpenCV, rtmidi
- **UI**: OpenCV window (always-on-top)
- **Distribution**: PyInstaller builds macOS `.app` bundle
- **Use Case**: Minimal dependencies, fastest to run

### 2. Web UI (`gestdj-web-ui/`)
- **Purpose**: Browser-based interface with Python backend
- **Tech**: React frontend + Python WebSocket backend
- **Communication**: WebSocket on port 8765 for gesture data streaming
- **Features**: Web-based UI, remote access capability
- **Use Case**: Platform-independent, can run on remote server

### 3. Electron Desktop App (`gestdj-electron/`)
- **Purpose**: Modern desktop app with native integration
- **Tech**: Electron + React + TypeScript + Python subprocess
- **Architecture**: Node.js main process manages Python backend, React frontend displays UI
- **Communication**: IPC bridge + WebSocket for gesture data
- **Distribution**: Cross-platform installers (macOS DMG, Windows NSIS, Linux AppImage)
- **Use Case**: Professional desktop experience with modern UI

All three share the same core MediaPipe gesture recognition and MIDI device integration.

## Dependencies

**Core Libraries**:
- `mediapipe==0.10.21`: Hand landmark detection
- `opencv-python==4.11.0.86`: Computer vision and UI
- `python-rtmidi==1.5.8`: MIDI device creation
- `numpy==1.26.4`: Numerical computations

**Supporting Libraries**:
- `matplotlib`, `scipy`: Visualization and signal processing
- `mido`: Alternative MIDI handling
- Build tools: `attrs`, `packaging`, `pillow`

## Setup and Usage Workflow

1. **Install Dependencies**: `pip install -r requirements.txt`
2. **Start GesteDJ**: `python app.py` creates virtual MIDI device
3. **Configure Mixxx**: Add `AI_DJ_Gestures` device in Preferences → Controllers
4. **Load Mapping**: Copy `AI_DJ_Gestures.midi.xml` to Mixxx user mapping folder
5. **Perform Gestures**: Use documented hand gestures to control DJ parameters

## Key Design Decisions

**Gesture-First Design**: Each gesture maps to a specific DJ function rather than generic MIDI controls
**Always-on-Top UI**: OpenCV window uses `WND_PROP_TOPMOST` for overlay functionality
**Dual-Deck Architecture**: Independent left/right hand control prevents gesture conflicts
**Non-Linear EQ Mapping**: Proper dB scaling for EQ controls (0.0-4.0 range with 1.0 = 0dB)
**Robust State Management**: Handles hand detection loss gracefully with state resets

## Performance Characteristics

- **Frame Rate**: ~30 FPS with gesture processing
- **MIDI Rate**: 30 Hz controlled output rate
- **Latency**: <50ms gesture-to-MIDI response time
- **Memory**: Efficient MediaPipe processing with frame resizing
- **CPU**: Moderate usage due to optimized MediaPipe settings

This codebase represents a well-architected computer vision application that successfully bridges the gap between hand gesture recognition and professional DJ software control through a clean MIDI abstraction layer.