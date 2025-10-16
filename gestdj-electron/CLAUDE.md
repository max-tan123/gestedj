# GesteDJ Electron - Architecture

## Phase 2 Architecture: Hybrid JavaScript/Python

### Data Flow
```
Camera (JS) → MediaPipe (JS) → Landmarks → Python → MIDI → Mixxx
              @mediapipe/       (JSON)     Gesture   rtmidi
              tasks-vision                 Logic
```

### Why Hybrid?
- **MIDI limitation**: Web MIDI API cannot create virtual devices
- **Efficient transfer**: Landmarks (~500 bytes) vs frames (~50KB)
- **Code reuse**: Keep proven Python gesture logic
- **Rich UI**: JavaScript handles visualization

## Tech Stack

### Frontend (JavaScript)
- React 18 + TypeScript + Vite
- `@mediapipe/tasks-vision` for hand detection
- Canvas API for landmark visualization

### Backend (Python)
- `gesture_processor.py` reads landmarks from stdin
- Gesture recognition logic (from `app.py`)
- `python-rtmidi` for MIDI virtual device

### IPC Bridge (Electron)
- Renderer → Main: `sendLandmarks(data)`
- Main → Python: stdin (JSON lines)
- Python → Main: stdout (gesture state)
- Main → Renderer: `onGestureUpdate(callback)`

## Current State (Phase 2 Core Implementation Complete)

**What's Working:**
- ✅ Camera feed with MediaPipe hand detection @ 30 FPS
- ✅ Hand skeleton overlay (green=Left, red=Right)
- ✅ IPC bridge: landmarks flow from renderer → main → Python
- ✅ `gesture_processor.py` reads landmarks from stdin
- ✅ Gesture recognition (finger counting, angle calculation)
- ✅ MIDI device creation (`VirtualMIDIDevice`)
- ✅ Gesture updates output to stdout (ready for UI)

**What Needs Testing:**
- ⏳ End-to-end pipeline verification
- ⏳ MIDI output to Mixxx
- ⏳ Gesture recognition accuracy
- ⏳ Dual-hand control (Deck 1 & Deck 2)

**Project Structure:**
```
gestdj-electron/
├── src/
│   ├── main/
│   │   ├── main.js           # Pipes landmarks to Python stdin
│   │   └── preload.js        # IPC: sendLandmarks, onGestureUpdate
│   └── renderer/
│       ├── App.tsx           # Converts MediaPipe → landmark JSON
│       ├── components/
│       │   └── CameraFeed.tsx  # MediaPipe HandLandmarker
│       └── types/
│           └── electron.d.ts   # TypeScript definitions
└── python-backend/
    ├── gesture_processor.py   # NEW: Reads landmarks, outputs MIDI
    ├── utils/ → ../../utils/  # Symlink to MIDI device
    └── venv/                  # Bundled Python environment
```

## Next Steps

1. **Debug & Test**: Verify complete data flow works
2. **Gesture UI**: Add overlay showing finger count, active knob, deck
3. **Latency Test**: Measure camera → MIDI latency (target < 50ms)

See `ROADMAP.md` and `PHASE2.md` for details.