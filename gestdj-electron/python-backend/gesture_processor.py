#!/usr/bin/env python3
"""
Gesture Processor - Receives landmarks from Electron, outputs MIDI
Reads landmark JSON from stdin, processes gestures, sends MIDI to Mixxx
"""

import sys
import json
import math
import time
from utils.midi_virtual_device import VirtualMIDIDevice

class GestureProcessor:
    def __init__(self):
        # Initialize MIDI device
        self.midi_device = VirtualMIDIDevice("AI_DJ_Gestures")
        print("✓ MIDI device initialized", flush=True)

        # Knob parameters (same as app.py)
        self.knob_params = {
            'filter': {'min': 0.0, 'max': 1.0, 'default': 0.5, 'range': 1.0},
            'low':    {'min': 0.0, 'max': 4.0, 'default': 1.0, 'range': 4.0},
            'mid':    {'min': 0.0, 'max': 4.0, 'default': 1.0, 'range': 4.0},
            'high':   {'min': 0.0, 'max': 4.0, 'default': 1.0, 'range': 4.0}
        }

        # State per deck
        self.deck_state = {
            1: {
                'knobs': {k: v['default'] for k, v in self.knob_params.items()},
                'active_knob': None,
                'previous_angle': None
            },
            2: {
                'knobs': {k: v['default'] for k, v in self.knob_params.items()},
                'active_knob': None,
                'previous_angle': None
            }
        }

        self.knob_max_angle = 135  # -135° to +135° range

    def get_extended_finger_flags(self, landmarks):
        """
        Determine which fingers are extended using curvature analysis.
        landmarks: list of {'x': norm_x, 'y': norm_y, 'z': norm_z}
        """
        flags = {'thumb': False, 'index': False, 'middle': False, 'ring': False, 'pinky': False}

        try:
            # Finger definitions (landmark indices)
            fingers = {
                'index':  [5, 6, 7, 8],
                'middle': [9, 10, 11, 12],
                'ring':   [13, 14, 15, 16],
                'pinky':  [17, 18, 19, 20]
            }

            wrist = landmarks[0]

            for finger_name, indices in fingers.items():
                # Get landmarks for this finger
                mcp = landmarks[indices[0]]
                pip = landmarks[indices[1]]
                dip = landmarks[indices[2]]
                tip = landmarks[indices[3]]

                # Calculate curvature (sum of bend angles)
                def angle_between_3_points(p1, p2, p3):
                    """Calculate angle at p2"""
                    v1 = {'x': p1['x'] - p2['x'], 'y': p1['y'] - p2['y']}
                    v2 = {'x': p3['x'] - p2['x'], 'y': p3['y'] - p2['y']}

                    dot = v1['x'] * v2['x'] + v1['y'] * v2['y']
                    mag1 = math.sqrt(v1['x']**2 + v1['y']**2)
                    mag2 = math.sqrt(v2['x']**2 + v2['y']**2)

                    if mag1 < 1e-6 or mag2 < 1e-6:
                        return 0.0

                    cos_angle = dot / (mag1 * mag2)
                    cos_angle = max(-1.0, min(1.0, cos_angle))
                    return math.degrees(math.acos(cos_angle))

                angle1 = angle_between_3_points(mcp, pip, dip)
                angle2 = angle_between_3_points(pip, dip, tip)
                total_curvature = angle1 + angle2

                # Check radial monotonicity (landmarks getting farther from wrist)
                dist_mcp = math.sqrt((mcp['x'] - wrist['x'])**2 + (mcp['y'] - wrist['y'])**2)
                dist_pip = math.sqrt((pip['x'] - wrist['x'])**2 + (pip['y'] - wrist['y'])**2)
                dist_dip = math.sqrt((dip['x'] - wrist['x'])**2 + (dip['y'] - wrist['y'])**2)
                dist_tip = math.sqrt((tip['x'] - wrist['x'])**2 + (tip['y'] - wrist['y'])**2)

                radial_ok = (dist_mcp <= dist_pip <= dist_dip <= dist_tip)

                # Extended if low curvature and proper radial ordering
                if total_curvature < 35 and radial_ok:
                    flags[finger_name] = True

        except Exception as e:
            print(f"Error in finger detection: {e}", flush=True)

        return flags

    def calculate_pointer_angle(self, landmarks):
        """
        Calculate rotation angle of hand (wrist to index tip).
        Returns angle in degrees (-135 to +135 range for knob control).
        """
        try:
            wrist = landmarks[0]
            index_tip = landmarks[8]

            dx = index_tip['x'] - wrist['x']
            dy = index_tip['y'] - wrist['y']

            # atan2 returns -π to π, convert to degrees
            angle_rad = math.atan2(-dx, dy)  # Note: -dx for proper orientation
            angle_deg = math.degrees(angle_rad)

            # Map to -135 to +135 range
            angle_deg = max(-135, min(135, angle_deg))

            return angle_deg

        except Exception as e:
            print(f"Error calculating angle: {e}", flush=True)
            return 0.0

    def process_hand(self, landmarks, deck):
        """Process gestures for one hand"""
        try:
            # Get extended finger flags
            flags = self.get_extended_finger_flags(landmarks)
            finger_count = sum([flags['index'], flags['middle'], flags['ring'], flags['pinky']])

            # Map finger count to control type
            control_map = {
                1: 'filter',  # Index only
                2: 'low',     # Index + Middle
                3: 'mid',     # Index + Middle + Ring
                4: 'high'     # All four fingers
            }

            state = self.deck_state[deck]

            if finger_count in control_map and flags['index']:  # Require index finger
                control_type = control_map[finger_count]
                angle = self.calculate_pointer_angle(landmarks)

                # Map angle to knob value (0.0 to 1.0 for filter, 0.0 to 4.0 for EQ)
                normalized_angle = (angle + 135) / 270  # Map -135...+135 to 0...1

                param = self.knob_params[control_type]
                value = param['min'] + (normalized_angle * param['range'])
                value = max(param['min'], min(param['max'], value))

                # Update state
                state['knobs'][control_type] = value
                state['active_knob'] = control_type
                state['previous_angle'] = angle

                # Send MIDI
                self.midi_device.update_control_on_channel(control_type, value, deck)

                # Output gesture state to stdout (for Electron UI)
                gesture_update = {
                    'type': 'gesture_update',
                    'deck': deck,
                    'fingers': finger_count,
                    'gesture': control_type,
                    'value': round(value, 3),
                    'angle': round(angle, 1)
                }
                print(json.dumps(gesture_update), flush=True)

        except Exception as e:
            print(f"Error processing hand: {e}", flush=True)

    def process_landmarks(self, landmark_data):
        """Process landmark data from JavaScript"""
        try:
            hands = landmark_data.get('hands', {})

            # Process Left hand (Deck 1)
            if 'Left' in hands:
                self.process_hand(hands['Left'], deck=1)

            # Process Right hand (Deck 2)
            if 'Right' in hands:
                self.process_hand(hands['Right'], deck=2)

        except Exception as e:
            print(f"Error processing landmarks: {e}", flush=True)

    def run(self):
        """Main loop: read landmarks from stdin"""
        print("✓ Gesture processor ready, waiting for landmarks...", flush=True)

        try:
            for line in sys.stdin:
                try:
                    data = json.loads(line.strip())

                    if data.get('type') == 'landmarks':
                        self.process_landmarks(data)

                except json.JSONDecodeError:
                    # Skip malformed JSON
                    continue
                except Exception as e:
                    print(f"Error processing line: {e}", flush=True)

        except KeyboardInterrupt:
            print("\n✓ Shutting down gesture processor", flush=True)
        finally:
            if self.midi_device:
                self.midi_device.close()

if __name__ == '__main__':
    processor = GestureProcessor()
    processor.run()
