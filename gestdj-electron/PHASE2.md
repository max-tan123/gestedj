# Phase 2: Hybrid JavaScript/Python Architecture

**Status**: Core Implementation Complete - Debugging Needed
**Date**: 2025-10-16

---

## Architecture Decision

After analyzing performance and feasibility, Phase 2 will implement a **hybrid approach**:

- **JavaScript**: Camera capture + MediaPipe hand detection
- **Python**: Gesture recognition logic + MIDI virtual device creation

### Why Hybrid?

**Technical Constraints:**
- Web MIDI API cannot create virtual MIDI devices (macOS/Windows)
- `python-rtmidi` is the only viable option for system MIDI device creation

**Performance Benefits:**
- Landmarks: ~500 bytes @ 30fps (vs ~50KB for frames)
- 100x reduction in data transfer overhead
- Same GPU backend (WebGL) as Python MediaPipe

**Code Reuse:**
- Keep 1,551 lines of proven gesture recognition logic
- No need to rewrite finger counting, angle calculation, etc.

---

## Data Flow

```
Camera (JS) → MediaPipe (JS) → Landmarks JSON → Python → MIDI → Mixxx
              @mediapipe/       (IPC stdin)    Gesture   rtmidi
              tasks-vision                     Logic
```

---

## Implementation Tasks

### Frontend (JavaScript)
1. Install `@mediapipe/tasks-vision` package
2. Create `CameraFeed.tsx`:
   - Camera access via `getUserMedia()`
   - Initialize `HandLandmarker` with GPU delegate
   - Process frames at 30 FPS
   - Draw landmarks on canvas overlay
3. Update `preload.js`:
   - Add `sendLandmarks(data)` IPC method
   - Add `onGestureUpdate(callback)` listener
4. Add gesture status overlay UI

### Backend (Python)
1. Create `gesture_processor.py`:
   - Read landmark JSON from stdin
   - Extract gesture logic from `app.py`
   - Keep `VirtualMIDIDevice` integration
   - Output gesture state as JSON to stdout
2. Update `main.js`:
   - Pipe landmark JSON to Python stdin
   - Parse gesture JSON from stdout
   - Forward to renderer via IPC

### Testing
1. Verify end-to-end latency < 50ms
2. Test dual-hand detection (Deck 1 + Deck 2)
3. Validate MIDI output in Mixxx

---

## Data Formats

### Landmarks (JS → Python stdin)
```json
{
  "type": "landmarks",
  "hands": ["Left", "Right"],
  "landmarks": [
    [{"x": 0.5, "y": 0.6, "z": -0.02}, ...],  // 21 points
    [{"x": 0.52, "y": 0.58, "z": -0.01}, ...]
  ]
}
```

### Gesture State (Python stdout → JS)
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

---

## Implementation Progress

### Completed ✅
- [x] Camera feed displays in Electron UI
- [x] Hand landmarks render on canvas in real-time (green=Left, red=Right)
- [x] MediaPipe HandLandmarker running @ 30 FPS
- [x] IPC bridge: `sendLandmarks()` and `onGestureUpdate()`
- [x] `gesture_processor.py` created with finger counting & angle calculation
- [x] MIDI device integration (`VirtualMIDIDevice`)
- [x] Landmark → gesture → MIDI pipeline implemented
- [x] Python reads from stdin, outputs to stdout

### Testing Required ⏳
- [ ] Verify MIDI device created and visible to Mixxx
- [ ] Test gesture recognition (finger count 1-4)
- [ ] Debug IPC communication (landmarks → Python → gestures → UI)
- [ ] Measure latency (target ≤ 50ms)
- [ ] Validate dual-hand control (Left=Deck 1, Right=Deck 2)

### Remaining Tasks 📋
- [ ] Gesture overlay UI (finger count, active knob, deck indicators)

---

## Next Steps After Phase 2

**Phase 3**: DJ Control Interface
- Virtual knobs, sliders, buttons
- Read-only visualization of MIDI output
- Deck 1/Deck 2 side-by-side panels

See `ROADMAP.md` for complete project timeline.
