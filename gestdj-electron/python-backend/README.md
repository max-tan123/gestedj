# Python Backend for GesteDJ Electron

This directory contains the Python backend that handles gesture recognition and MIDI device creation.

## Architecture

The backend uses **symlinks** to the main GesteDJ codebase:
- `main.py` → `../../app.py` (main hand detection + MIDI logic)
- `utils/` → `../../utils/` (MIDI virtual device utilities)

This approach allows the Electron app to reuse the battle-tested standalone implementation without code duplication.

## Dependencies

Install Python dependencies:
```bash
pip install -r requirements.txt
```

Or use the root-level requirements.txt:
```bash
cd ../.. && pip install -r requirements.txt
```

## Usage

The Electron main process spawns this backend automatically:

```javascript
spawn('python3', ['main.py'], {
  cwd: path.join(__dirname, '../python-backend')
})
```

## Why Symlinks?

1. **Single source of truth**: Changes to `app.py` automatically apply to Electron
2. **No code duplication**: Reduces maintenance burden
3. **Consistent behavior**: Standalone and Electron versions use identical gesture logic
4. **Easy testing**: Can test `app.py` directly without Electron

## Direct Mode vs OpenCV Window

When spawned by Electron:
- The OpenCV window is suppressed (Electron provides the UI)
- Python outputs gesture state to stdout as JSON
- Electron parses stdout and updates React UI

Future: Add `--headless` flag to completely disable OpenCV window.
