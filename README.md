## GesteDJ — Gesture-Controlled DJ for Mixxx

GesteDJ uses MediaPipe and OpenCV to detect hand gestures and drives a virtual MIDI instrument named `AI_DJ_Gestures` that Mixxx can learn and control. A simple on-screen preview shows what the system sees and stays on top while you perform.

### Features
- **Real-time gestures**: up to two hands with 21 landmarks
- **Virtual MIDI device**: bi-directional port `AI_DJ_Gestures`
- **EQ/Filter/Volume control** via finger-count + rotation
- **Always-on-top preview window** for quick feedback

### Requirements
- macOS with a webcam
- Python 3.11 (project ships with a `venv/` folder)

### Install
```bash
pip install -r requirements.txt
```

### Run (dev)
```bash
python app.py
```

### Build a macOS App
```bash
zsh build_macos_app.sh
```
This generates `dist/GesteDJ.app`.

### First-time Mixxx Integration (do this once)
1. **Start GesteDJ** to create the MIDI device `AI_DJ_Gestures`.
2. **Open Mixxx** → Preferences → Controllers. You should see `AI_DJ_Gestures` listed for Input and Output.
3. Click **Learning Wizard** and map any effect you plan to use (for example: Deck 1 → Volume Fader). Perform the matching hand gesture while learning. This creates a user mapping `.xml` and `.js` in Mixxx’s user mapping folder.
4. Back in Preferences → Controllers, click **Open User Mapping Folder** and copy our mapping file `mixxx_utils/AI_DJ_Gestures.midi.xml` into that folder. Overwrite or disable the auto-generated mapping if prompted.
5. **Restart Mixxx**. You’re ready to play.

### Gestures (as implemented)
- **1 finger (index only)**: Filter
- **2 fingers (index+middle)**: Low EQ
- **3 fingers (index+middle+ring)**: Mid EQ
- **4 fingers (index+middle+ring+pinky)**: High EQ
- **Pinch (thumb–index) with middle+ring+pinky extended)**: Volume. Move pinch midpoint up/down to change channel volume.
- **Rockstar (index + pinky only)**: Toggle Effect 1 enabled for the deck.
- **Thumbs up**: Toggle Play/Pause for the deck.

Notes
- Raw MediaPipe labels are mirrored after frame flip: raw 'Left' → Deck 1, raw 'Right' → Deck 2.
- Rotate your hand to change the active knob; values are smoothed and sent at 30 Hz.

### Controls in the app
- Press `q` to quit
- Press `c` to toggle console output
- Press `a` to toggle full landmark draw
- Press `s` to save a frame

### Troubleshooting
- **No `AI_DJ_Gestures` in Mixxx**: Make sure GesteDJ is running first.
- **Camera permissions**: Allow camera access for GesteDJ/GesteDJ.app in macOS settings.
- **Mapping missing**: Re-run the Learning Wizard, then paste `AI_DJ_Gestures.midi.xml` into the User Mapping Folder and restart Mixxx.
