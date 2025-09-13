# AI DJ Hand Gesture Control Setup Instructions

This guide will help you set up the complete AI DJ hand gesture control system for Mixxx.

## Overview

The system consists of:
1. **Hand gesture recognition** using MediaPipe and OpenCV
2. **Virtual MIDI device** that converts gestures to MIDI messages
3. **Mixxx XML mapping** that connects MIDI to DJ controls

## Prerequisites

- Python 3.7 or higher
- Webcam/camera
- Mixxx DJ software (free download from mixxx.org)
- macOS/Linux (Windows requires additional MIDI setup)

## Installation Steps

### 1. Install Python Dependencies

```bash
# Navigate to the project directory
cd /Users/vasukaker/Desktop/HackMIT_2025/AI_DJ

# Install required packages
pip install -r requirements.txt
```

If you encounter issues with `python-rtmidi`, you may need to install additional system dependencies:

**macOS:**
```bash
# Install with Homebrew if needed
brew install rtmidi
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install libasound2-dev libjack-dev
```

### 2. Test the Components

#### Test Hand Detection (without MIDI)
```bash
python hand_detection_optimized.py
```
- This should open your camera and detect hand gestures
- Press 'q' to quit, 'c' to toggle console output

#### Test MIDI Device
```bash
python midi_virtual_device.py
```
- This creates a virtual MIDI device called "AI_DJ_Gestures"
- Press 't' to send test sequences, 'q' to quit

#### Test Complete System
```bash
python hand_detection_midi.py
```
- This combines hand detection with MIDI output
- You should see MIDI status in the interface

### 3. Configure Mixxx

#### Install the Mapping File
1. Copy `AI_DJ_Gestures.mixxx.xml` to your Mixxx controller mappings folder:
   - **macOS:** `~/Library/Application Support/Mixxx/controllers/`
   - **Linux:** `~/.mixxx/controllers/`
   - **Windows:** `%APPDATA%\Mixxx\controllers\`

2. If the folder doesn't exist, create it.

#### Enable the Controller in Mixxx
1. Open Mixxx
2. Go to **Preferences > Controllers**
3. Look for "AI_DJ_Gestures" in the available devices
4. Enable it and select the "AI DJ Hand Gestures Controller" preset
5. Click **Apply** and **OK**

### 4. Run the Complete System

1. **Start the gesture recognition:**
   ```bash
   python hand_detection_midi.py
   ```

2. **Launch Mixxx** and load some tracks

3. **Start controlling with gestures:**
   - Hold up different numbers of fingers and rotate your hand
   - Watch the EQ and filter controls in Mixxx respond

## Gesture Controls

| Fingers | Control | Mixxx Parameter | MIDI CC |
|---------|---------|-----------------|---------|
| 1 finger | Filter | High/Low Pass Filter | CC1 |
| 2 fingers | Low EQ | Low Frequency EQ | CC2 |
| 3 fingers | Mid EQ | Mid Frequency EQ | CC3 |
| 4 fingers | High EQ | High Frequency EQ | CC4 |

### How to Use:
1. **Point with your index finger** (other fingers down)
2. **Hold up the desired number of fingers** (1-4)
3. **Rotate your hand** clockwise/counter-clockwise to control the value
4. **Close your hand** to lock the current value
5. **Switch to different finger counts** to control different parameters

## Troubleshooting

### MIDI Issues
- **"MIDI device not available"**: Make sure `python-rtmidi` is installed correctly
- **Device not showing in Mixxx**: Restart Mixxx after starting the gesture recognition
- **No response in Mixxx**: Check that the controller is enabled in Preferences

### Camera Issues
- **Camera not found**: Ensure no other applications are using your camera
- **Poor detection**: Ensure good lighting and clear background
- **Laggy performance**: Try reducing video resolution in the code

### Hand Detection Issues
- **Fingers not counted correctly**: Ensure fingers are clearly separated and visible
- **Angle detection problems**: Keep your hand flat and parallel to the camera
- **Inconsistent tracking**: Move slowly and keep gestures deliberate

### Performance Optimization
- **Reduce video resolution** in `hand_detection_midi.py`
- **Lower MIDI send rate** by changing `midi_send_rate` variable
- **Disable visual landmarks** by pressing 'a' key during runtime

## File Structure

```
AI_DJ/
├── hand_detection_optimized.py      # Original hand detection (no MIDI)
├── midi_virtual_device.py           # Virtual MIDI device class
├── hand_detection_midi.py           # Complete system with MIDI
├── AI_DJ_Gestures.mixxx.xml         # Mixxx controller mapping
├── requirements.txt                 # Python dependencies
├── SETUP_INSTRUCTIONS.md            # This file
└── README.md                        # Project overview
```

## Advanced Configuration

### Customizing MIDI Mapping
Edit `AI_DJ_Gestures.mixxx.xml` to:
- Change which controls are mapped
- Adjust MIDI channel numbers
- Add more controls (crossfader, effects, etc.)

### Adjusting Gesture Sensitivity
Edit `hand_detection_midi.py` to:
- Change angle-to-MIDI scaling factor
- Modify finger detection thresholds
- Adjust smoothing parameters

### Adding More Gestures
Extend the system by:
- Adding thumb detection for more controls
- Using two-hand detection for stereo control
- Adding gesture-based button triggers

## MIDI Technical Details

- **Device Name:** AI_DJ_Gestures
- **MIDI Channel:** 1 (0x00 in hex)
- **Message Type:** Control Change (0xB0)
- **Value Range:** 0-127 (maps to -135° to +135° hand rotation)
- **Send Rate:** 30 Hz (adjustable)

## Support

If you encounter issues:

1. Check the console output for error messages
2. Verify all dependencies are installed correctly
3. Test each component individually
4. Ensure Mixxx version compatibility (tested with Mixxx 2.3+)

## Next Steps

Once the basic system is working, you can:
- Add more gesture controls
- Implement beat synchronization
- Create custom effects mappings
- Add visual feedback LEDs/displays
- Integrate with other DJ software

Enjoy your AI-powered DJ setup! 🎵🤖
