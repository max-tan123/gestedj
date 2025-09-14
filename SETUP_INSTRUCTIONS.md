# Setup Instructions

This guide gets you from source to a working Mixxx setup driven by hand gestures.

## 1) Install
```bash
pip install -r requirements.txt
```

## 2) Build the macOS app (optional, recommended)
```bash
zsh build_macos_app.sh
```
This creates `dist/GesteDJ.app` and a rounded app icon. You can also run from source with `python app.py`.

## 3) First-time Mixxx integration
Follow these once to register and use the virtual MIDI device.

1. Start **GesteDJ** (app or `python app.py`) to create the MIDI device `AI_DJ_Gestures`.
2. Open **Mixxx** → Preferences → Controllers. Ensure `AI_DJ_Gestures` appears and is enabled for Input/Output.
3. Click **Learning Wizard**. Choose any control you’ll use (e.g., Deck 1 → Volume Fader) and perform the matching hand gesture while learning. Mixxx will create a user `.xml` and `.js` mapping.
4. In Controllers, click **Open User Mapping Folder**. Copy our mapping `mixxx_utils/AI_DJ_Gestures.midi.xml` into that folder (replace or disable the auto-generated mapping if desired).
5. Restart **Mixxx**.

## 4) Run
- App bundle: open `dist/GesteDJ.app`
- From source: `python app.py`

The preview window stays on top; press `q` to quit.

## Gestures
- 1 finger (index only): Filter
- 2 fingers (index+middle): Low EQ
- 3 fingers (index+middle+ring): Mid EQ
- 4 fingers (index+middle+ring+pinky): High EQ
- Pinch (thumb–index) with middle+ring+pinky extended: Volume (move pinch midpoint up/down)
- Rockstar (index + pinky only): Toggle Effect 1 enabled
- Thumbs up: Toggle Play/Pause

## Troubleshooting
- `AI_DJ_Gestures` not listed: start GesteDJ first, then open Mixxx.
- No response after learning: paste `mixxx_utils/AI_DJ_Gestures.midi.xml` into the user folder and restart Mixxx.
- Camera blocked: allow camera permission for the app in macOS settings.
