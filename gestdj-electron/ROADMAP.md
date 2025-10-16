# GesteDJ Electron - Implementation Roadmap

## Architecture Decision

**Hybrid JavaScript/Python Model** ✅ **FINALIZED (2025-10-16)**

### Data Flow: Camera → MediaPipe (JS) → Gestures (Python) → MIDI → Mixxx

**Why Hybrid?**
- ✅ **Minimal data transfer**: Landmarks only (~500 bytes @ 30fps vs 50KB frames)
- ✅ **MIDI virtual device**: Python's `rtmidi` creates true system devices (Web MIDI can't)
- ✅ **Rich visualization**: JavaScript handles camera + canvas rendering
- ✅ **Reuse proven code**: 1,551 lines of gesture logic untouched
- ✅ **Low latency**: ~41ms end-to-end (comparable to pure Python)

**JavaScript Handles:**
- Camera capture (HTML5 `getUserMedia`)
- MediaPipe hand detection (`@mediapipe/tasks-vision`)
- Landmark visualization (Canvas API)
- Gesture status UI overlay

**Python Handles:**
- Gesture recognition logic (finger counting, angle calculation)
- MIDI virtual device creation (`python-rtmidi`)
- MIDI message output (30Hz throttled)
- Direct connection to Mixxx

**Communication:**
- Electron Renderer → Main: IPC (`sendLandmarks`)
- Main → Python: stdin (JSON lines)
- Python → Main: stdout (gesture state JSON)
- Main → Renderer: IPC (gesture updates)

## Phase 1: Get Basic Electron App Running ✅ COMPLETE
**Goal**: Launch Electron, spawn Python backend, create MIDI device

**Tasks**:
- [x] Install npm dependencies (596 packages installed)
- [x] Create `gestdj-electron/python-backend/` with symlinks to `app.py`
- [x] Include MIDI virtual device utilities (symlinked `utils/`)
- [x] Update `main.js` to spawn new backend location
- [x] Test Electron launches successfully
- [x] Verify backend path configuration correct
- [x] Test UI renders with backend control buttons

**Deliverable**: ✅ Working Electron app configured to spawn Python backend

**Notes**:
- Python dependencies (mediapipe, python-rtmidi) need to be installed by user: `pip install -r requirements.txt`
- Backend start/stop controls present in UI, ready for testing once Python deps installed
- MIDI device verification requires Python dependencies to be installed first

---

## Phase 2: MediaPipe in JavaScript + Gesture Processing in Python 🔄 IN PROGRESS
**Goal**: Camera → MediaPipe (JS) → Landmarks → Gesture Logic (Python) → MIDI

### Frontend Tasks (JavaScript)
- [x] Install `@mediapipe/tasks-vision` npm package
- [x] Create `CameraFeed.tsx` component:
  - HTML5 camera access (`getUserMedia`)
  - Initialize MediaPipe `HandLandmarker` with GPU delegate
  - Process video frames at 30 FPS
  - Draw hand landmarks on canvas overlay
- [x] Add IPC bridge in `preload.js`:
  - `sendLandmarks(landmarkData)` method
  - `onGestureUpdate(callback)` event listener
- [ ] Gesture status overlay UI:
  - Finger count visualization (1-5 per hand)
  - Active knob indicator (Filter/Low/Mid/High/Volume)
  - Deck assignment (Left → Deck 1, Right → Deck 2)
  - Hand presence indicators

### Backend Tasks (Python)
- [x] Create `gesture_processor.py`:
  - Read landmark JSON from stdin
  - Extract gesture recognition logic from `app.py`
  - Keep all finger counting, angle calculation logic
  - Maintain `VirtualMIDIDevice` integration
- [x] Update `main.js`:
  - Pipe landmark JSON to Python stdin
  - Parse gesture state JSON from Python stdout
  - Forward gesture updates to renderer via IPC

### Status: Ready for Testing & Debugging
- ✅ Complete data flow implemented
- ⏳ Needs end-to-end testing
- ⏳ IPC communication debugging required

### Data Format
**Landmarks (JS → Python):**
```json
{
  "type": "landmarks",
  "hands": ["Left", "Right"],
  "landmarks": [
    [{"x": 0.5, "y": 0.6, "z": -0.02}, ...],  // 21 points per hand
    [{"x": 0.52, "y": 0.58, "z": -0.01}, ...]
  ]
}
```

**Gesture State (Python → JS):**
```json
{
  "type": "gesture_update",
  "deck": 1,
  "fingers": 2,
  "gesture": "low",
  "knob_value": 0.75,
  "midi_cc": 2,
  "midi_value": 95
}
```

**Deliverable**: Camera feed with MediaPipe in JS, MIDI output from Python

---

## Phase 3: Add DJ Control Interface
**Goal**: Visual representation of MIDI output values

**Tasks**:
- Create `DJControls.tsx` component with virtual controls:
  - **Deck 1 & Deck 2 panels** (side-by-side)
  - **EQ Knobs**: Low/Mid/High (visual rotation, read-only)
  - **Filter Knob**: Visual rotation (read-only)
  - **Volume Slider**: Vertical slider (read-only)
  - **Status Indicators**: Play/Pause, Effect 1 enabled
- Parse gesture values from Python stdout
- Update UI controls to mirror MIDI output in real-time
- Add deck labels and color coding (Deck 1: Blue, Deck 2: Red)
- Show "knob locked" indicator when pointer finger is down

**Design Note**: Controls are **read-only visualizations** - gestures drive MIDI, UI reflects state

**Deliverable**: Full DJ interface showing real-time MIDI output values

---

## Phase 4: Polish & Distribution
**Goal**: Production-ready desktop app

**Tasks**:
- **Settings Panel**:
  - Camera selection
  - Gesture sensitivity adjustments
  - MIDI device name configuration
  - Show/hide camera feed option
- **UX Polish**:
  - Dark theme refinement
  - Smooth animations for knob rotations
  - Status notifications (MIDI device connected, errors)
  - Keyboard shortcuts (Space: start/stop, Esc: quit)
- **Error Handling**:
  - Camera permission denied → show helpful message
  - MIDI device creation failed → troubleshooting guide
  - Python backend crash → auto-restart option
- **Build & Distribution**:
  - Test `npm run dist` for macOS DMG
  - Code signing for macOS Gatekeeper
  - Create Windows NSIS installer
  - Test on clean systems
- **Documentation**:
  - Update README with installation instructions
  - Add screenshots/GIFs of UI
  - Mixxx integration guide

**Deliverable**: Shippable installers for macOS/Windows/Linux

---

## Future Enhancements (Post-MVP)

### Advanced Visualization
- WebSocket bridge for processed video frames with hand landmarks drawn
- Real-time hand skeleton overlay
- Gesture trail visualization (motion history)

### Custom Gesture Mapping
- UI for defining custom gestures
- Map gestures to arbitrary MIDI CC values
- Save/load gesture profiles

### Performance Analytics
- Latency monitoring dashboard
- Gesture recognition accuracy metrics
- Frame rate and CPU usage graphs

### Multi-Camera Support
- Switch between multiple cameras
- Picture-in-picture mode

### Cloud Features
- Sync settings across devices
- Share gesture mappings with community
- Remote monitoring via web interface

---

## Technical Notes

### Communication Flow
```
Camera (JS) → MediaPipe (JS) → Landmarks JSON → Python → MIDI → Mixxx
                               ↓
                          Gesture UI (React)
```

### File Structure
```
gestdj-electron/
└── python-backend/
    ├── gesture_processor.py       # Processes landmarks, outputs MIDI
    ├── utils/ → ../../utils/      # Symlink (MIDI device)
    └── requirements.txt           # python-rtmidi, numpy
```

---

## Current Status

- **Phase 1**: ✅ Complete (2025-10-13)
- **Phase 2**: 🔄 In Progress (2025-10-16) - Core implementation complete, debugging needed
- **Phase 3**: ⏳ Not started
- **Phase 4**: ⏳ Not started

Last Updated: 2025-10-16
