# Python Backend Setup

## Current Setup: Bundled venv ✅

Python dependencies are bundled in a virtual environment at `venv/`.

### Already Installed
- `mediapipe==0.10.21`
- `opencv-python==4.11.0.86`
- `python-rtmidi==1.5.8`
- `numpy==1.26.4`

### Testing
```bash
# Test venv works
./venv/bin/python3 -c "import mediapipe, cv2, rtmidi; print('✅ Working')"

# Test backend manually
./venv/bin/python3 main.py
```

### Rebuilding venv (if needed)
```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install mediapipe opencv-python python-rtmidi numpy
deactivate
```

---

## Architecture

- `main.py` → symlink to `../../app.py` (reuses standalone implementation)
- `utils/` → symlink to `../../utils/` (MIDI virtual device)
- `venv/` → bundled Python environment (gitignored)

**No code duplication**: Changes to `app.py` automatically apply here.

---

## Future: PyInstaller Bundle

For production distribution, migrate to PyInstaller:

```bash
# Install PyInstaller
pip install pyinstaller

# Create standalone binary
pyinstaller --onefile \
  --add-data "utils:utils" \
  --hidden-import mediapipe \
  --hidden-import cv2 \
  --hidden-import rtmidi \
  main.py

# Binary created at: dist/main
```

Then update Electron to use bundled binary in production.
