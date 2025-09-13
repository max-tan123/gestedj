# AI DJ Hand Gesture Control System Overview

## Project Overview

The AI DJ Hand Gesture Control System is an innovative real-time gesture recognition system that allows DJs to control Mixxx DJ software using hand movements detected through computer vision. Built for HackMIT 2025, this system combines machine learning, computer vision, and MIDI technology to create an intuitive, touchless DJ interface.

## System Architecture

The system consists of three main components that work together to translate hand gestures into DJ controls:
 
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Hand Detection │───▶│ MIDI Translation│───▶│   Mixxx DJ      │
│     Module      │    │     Module      │    │   Software      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Core Components

### 1. Hand Detection Module (`app.py`)

**Purpose**: Real-time hand gesture recognition and tracking using computer vision

**Key Features**:
- **MediaPipe Integration**: Uses Google's MediaPipe library for robust hand landmark detection
- **Gesture Recognition**: Interprets finger counts and hand rotation to control DJ parameters.
- **Real-Time UI**: An OpenCV window provides real-time visual feedback on gestures, MIDI status, and Mixxx controller state.

**Technical Implementation**:
- **Computer Vision Pipeline**:
  - Camera input capture via OpenCV
  - MediaPipe hand landmark detection
- **Gesture Analysis**:
  - Finger counting to select the active DJ control.
  - Calculation of hand rotation angle to modify the control's value.
  - State synchronization with Mixxx to ensure smooth "soft takeover".

### 2. MIDI Translation Module (`utils/midi_virtual_device.py`)

**Purpose**: Converts gesture data into MIDI messages and handles feedback from Mixxx.

**Key Features**:
- **Virtual MIDI Device**: Creates a system-level MIDI input/output device that Mixxx can connect to.
- **Bi-directional Communication**: Sends control messages to Mixxx and receives state feedback from Mixxx.
- **Value Smoothing**: Applies smoothing algorithms to prevent jittery controls.
- **Non-Linear Value Mapping**: Correctly translates linear hand rotation into the non-linear response curves for Mixxx's EQs.

**MIDI Configuration**:
```python
midi_config = {
    # Knobs are controlled on Channel 1 (0)
    'filter': {'channel': 0, 'cc': 1, 'min_value': 0.0, 'max_value': 1.0, 'default': 0.5},
    'low':    {'channel': 0, 'cc': 2, 'min_value': 0.0, 'max_value': 4.0, 'default': 1.0},
    'mid':    {'channel': 0, 'cc': 3, 'min_value': 0.0, 'max_value': 4.0, 'default': 1.0},
    'high':   {'channel': 0, 'cc': 4, 'min_value': 0.0, 'max_value': 4.0, 'default': 1.0},
    # Toggles are on CC 16 & 17
    'toggle_filter': {'channel': 0, 'cc': 16},
    'toggle_eq':     {'channel': 0, 'cc': 17},
}
# Feedback is received on Channel 2 (1)
```

### 3. Mixxx Integration (`mixxx_utils/AI_DJ_Gestures.midi.xml`)

**Purpose**: Maps MIDI messages to specific DJ controls in Mixxx software.

**Key Features**:
- **Custom MIDI Mapping**: XML configuration file that defines all input controls and output feedback.
- **EQ & Filter Mapping**: Maps incoming MIDI CC messages to the correct effect parameters.
- **Effect Toggle Mapping**: Maps a dedicated MIDI message to enabling/disabling the effect racks.
- **MIDI Feedback**: Configured to send MIDI messages back to the Python app when controls are changed in the Mixxx UI.

## Data Flow

The data flow is a complete loop:

1.  **Input (Python -> Mixxx)**:
    `Camera -> OpenCV -> MediaPipe -> Gesture Analysis -> MIDI CC Message -> Virtual MIDI Device -> Mixxx`
2.  **Feedback (Mixxx -> Python)**:
    `Mixxx Control Change -> XML Output Mapping -> MIDI CC Message -> Virtual MIDI Device -> Python UI`

## Gesture Control Mapping

The gesture system is based on the number of fingers being held up. Once a control is selected, rotating your hand modifies the value.

-   **0 Fingers (Fist)**: Toggles the Filter and EQ effect racks on or off. You must enable the effects before the other controls will work.
-   **1 Finger**: Selects the **Filter**. Rotate your hand to control the high/low-pass filter.
-   **2 Fingers**: Selects the **Low EQ**. Rotate your hand to control the bass frequencies.
-   **3 Fingers**: Selects the **Mid EQ**. Rotate your hand to control the midrange frequencies.
-   **4 Fingers**: Selects the **High EQ**. Rotate your hand to control the treble frequencies.

## File Structure

```
/
├── app.py                            # Main hand detection and UI application
├── utils/
│   └── midi_virtual_device.py      # Virtual MIDI device implementation
├── mixxx_utils/
│   └── AI_DJ_Gestures.midi.xml     # Mixxx MIDI mapping configuration
├── tests/
│   └── quick_test.py               # System testing utilities
├── requirements.txt                  # Python dependencies
├── README.md                         # Project documentation
├── SETUP_INSTRUCTIONS.md            # Installation and setup guide
└── SYSTEM_OVERVIEW.md               # This system overview document
```

## Development Notes

This system was developed for HackMIT 2025 as a proof-of-concept for gesture-based DJ control. The architecture is designed for extensibility and real-world performance, with careful attention to latency, accuracy, and user experience.

The codebase demonstrates advanced integration of computer vision, real-time audio processing, and human-computer interaction principles, making it suitable for both educational study and practical DJ applications.
