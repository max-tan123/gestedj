# GesteDJ System Overview

GesteDJ lets you control Mixxx with hand gestures. MediaPipe detects landmarks, OpenCV renders a live preview, and a virtual MIDI device (`AI_DJ_Gestures`) bridges to Mixxx.

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

**Purpose**: Real-time gesture recognition and on-top preview window

**Key Features**:
- **MediaPipe Integration**: Uses Google's MediaPipe library for robust hand landmark detection
- **Gesture Recognition**: Interprets finger counts and hand rotation to control DJ parameters.
- **Always-on-top UI**: OpenCV window named `GesteDJ` is created with `WND_PROP_TOPMOST` so you can keep Mixxx in view while adjusting.

**Technical Implementation**:
- **Computer Vision Pipeline**:
  - Camera input capture via OpenCV
  - MediaPipe hand landmark detection
- **Gesture Analysis**:
  - Finger counting to select the active DJ control.
  - Calculation of hand rotation angle to modify the control's value.
  - State synchronization with Mixxx to ensure smooth "soft takeover".

### 2. MIDI Translation Module (`utils/midi_virtual_device.py`)

**Purpose**: Creates and manages the virtual instrument `AI_DJ_Gestures`, translating gestures to MIDI and accepting feedback.

**Key Features**:
- **Virtual MIDI Device**: Creates a system-level MIDI input/output device that Mixxx can connect to.
- **Bi-directional Communication**: Sends control messages to Mixxx and receives state feedback from Mixxx.
- **Value Smoothing**: Applies smoothing algorithms to prevent jittery controls.
- **Non-Linear Value Mapping**: Correctly translates linear hand rotation into the non-linear response curves for Mixxx's EQs.

**MIDI Configuration**:
```python
midi_control_config = {
    'filter': {'cc1': 1, 'cc2': 5, 'min_value': 0.0, 'max_value': 1.0, 'default': 0.5},
    'low':    {'cc1': 2, 'cc2': 6, 'min_value': 0.0, 'max_value': 4.0, 'default': 1.0},
    'mid':    {'cc1': 3, 'cc2': 7, 'min_value': 0.0, 'max_value': 4.0, 'default': 1.0},
    'high':   {'cc1': 4, 'cc2': 8, 'min_value': 0.0, 'max_value': 4.0, 'default': 1.0},
    # New volume control (linear 0..1)
    'volume': {'cc1': 9, 'cc2': 10, 'min_value': 0.0, 'max_value': 1.0, 'default': 0.5},
    # # Effect routing (binary normal CC to keep group_[ChannelN]_enable ON)
}
midi_toggle_config = {
    'play':   {'cc1': 0x12, 'cc2': 0x13, 'toggle_value': 127},
    # Effect enabled toggle (EffectUnitN_Effect1.enabled)
    'effect1': {'cc1': 0x16, 'cc2': 0x17, 'toggle_value': 127},
}
# Feedback is received on Channel 2 (1)
```

### 3. Mixxx Integration (`mixxx_utils/AI_DJ_Gestures.midi.xml`)

**Purpose**: Provides the mapping Mixxx loads to bind controls to our MIDI messages.

**Key Features**:
- **Custom MIDI Mapping**: XML configuration file that defines all input controls and output feedback.
- **EQ & Filter Mapping**: Maps incoming MIDI CC messages to the correct effect parameters.
- **Effect Toggle Mapping**: Maps a dedicated MIDI message to enabling/disabling the effect racks.
- **MIDI Feedback**: Configured to send MIDI messages back to the Python app when controls are changed in the Mixxx UI.

## Data Flow

The data flow is a complete loop:

1.  Input (Python → Mixxx): `Camera → MediaPipe → Gesture Analysis → MIDI CC → AI_DJ_Gestures → Mixxx`
2.  Feedback (Mixxx → Python): `Mixxx → XML mapping → MIDI CC → AI_DJ_Gestures → UI overlay`

## Gesture Control Mapping (from code and XML)

The gesture system is based on the number of fingers being held up. Once a control is selected, rotating your hand modifies the value.

-   1 finger (index only): Filter → `QuickEffectRack1_*:super1` (CC 1 / CC 5)
-   2 fingers (index+middle): Low EQ → `EqualizerRack1_*_Effect1:parameter1` (CC 2 / CC 6)
-   3 fingers (index+middle+ring): Mid EQ → `EqualizerRack1_*_Effect1:parameter2` (CC 3 / CC 7)
-   4 fingers (index+middle+ring+pinky): High EQ → `EqualizerRack1_*_Effect1:parameter3` (CC 4 / CC 8)
-   Pinch (thumb–index) with middle+ring+pinky extended: Channel Volume (CC 9 / CC 10)
-   Rockstar (index + pinky only): Enable Effect 1 (CC 0x16 / 0x17)
-   Thumbs up: Play/Pause toggle (CC 0x12 / 0x13)

## File Structure

```
/
├── app.py                            # Main detection + UI (always-on-top)
├── utils/
│   └── midi_virtual_device.py      # Virtual MIDI device implementation
├── mixxx_utils/
│   └── AI_DJ_Gestures.midi.xml     # Mixxx MIDI mapping
├── tests/
│   └── quick_test.py               # System testing utilities
├── requirements.txt                  # Python dependencies
├── README.md                         # Project documentation
├── SETUP_INSTRUCTIONS.md            # Installation and setup guide
└── SYSTEM_OVERVIEW.md               # This system overview document
```

## Using with Mixxx (first time)
1. Start GesteDJ to create `AI_DJ_Gestures`.
2. Open Mixxx → Preferences → Controllers and verify the device is visible and enabled.
3. Use **Learning Wizard** to map at least one control by performing the matching gesture.
4. Open the **User Mapping Folder** and copy `mixxx_utils/AI_DJ_Gestures.midi.xml` there.
5. Restart Mixxx.
