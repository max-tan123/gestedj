#!/usr/bin/env python3
"""
Hand Detection with MIDI Output for DJ Control
Integrates hand gesture recognition with virtual MIDI device
"""

import cv2
import mediapipe as mp
import numpy as np
import time
import math
from collections import deque
import threading

# Import our MIDI device
try:
    from utils.midi_virtual_device import VirtualMIDIDevice
    MIDI_AVAILABLE = True
except ImportError as e:
    print(f"Warning: MIDI device not available: {e}")
    print("Install required packages: pip install python-rtmidi mido")
    MIDI_AVAILABLE = False

class HandDetectorWithMIDI:
    def __init__(self):
        # Initialize MediaPipe hands with optimized settings
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.8,
            min_tracking_confidence=0.7,
            model_complexity=0
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # All 21 hand landmarks
        self.key_landmarks = list(range(21))
        self.landmark_names = [
            "Wrist",           # 0
            "Thumb_CMC",       # 1
            "Thumb_MCP",       # 2
            "Thumb_IP",        # 3
            "Thumb_Tip",       # 4
            "Index_MCP",       # 5
            "Index_PIP",       # 6
            "Index_DIP",       # 7
            "Index_Tip",       # 8
            "Middle_MCP",      # 9
            "Middle_PIP",      # 10
            "Middle_DIP",      # 11
            "Middle_Tip",      # 12
            "Ring_MCP",        # 13
            "Ring_PIP",        # 14
            "Ring_DIP",        # 15
            "Ring_Tip",        # 16
            "Pinky_MCP",       # 17
            "Pinky_PIP",       # 18
            "Pinky_DIP",       # 19
            "Pinky_Tip"        # 20
        ]
        
        # Performance tracking
        self.fps_history = deque(maxlen=30)
        self.frame_times = deque(maxlen=5)
        
        # Display options
        self.show_console_output = False
        self.show_all_landmarks = False
        
        # DJ Control System
        self.knob_params = {
            'filter': {'min': 0.0, 'max': 1.0, 'default': 0.5, 'range': 1.0},
            'low':    {'min': 0.0, 'max': 4.0, 'default': 1.0, 'range': 4.0},
            'mid':    {'min': 0.0, 'max': 4.0, 'default': 1.0, 'range': 4.0},
            'high':   {'min': 0.0, 'max': 4.0, 'default': 1.0, 'range': 4.0}
        }
        self.knobs = {k: v['default'] for k, v in self.knob_params.items()}
        self.knob_names = ['filter', 'low', 'mid', 'high']
        
        # Deck 2 mirrors (do not change original deck 1 state)
        self.knobs2 = {k: v['default'] for k, v in self.knob_params.items()}
        self.active_knob2 = None
        self.previous_angle2 = None
        self.current_pointer_angle2 = 0.0
        self.current_finger_count2 = 0
        self.previous_finger_count2 = 0
        self.knob_locked2 = False
        self.gesture_active2 = False
        
        # Tracking variables for continuous control
        self.stream_initial_angle = None
        self.previous_angle = None
        self.current_finger_count = 0
        self.previous_finger_count = 0
        self.active_knob = None
        self.previous_active_knob = None
        self.knob_locked = False
        self.gesture_active = False
        self.current_pointer_angle = 0.0
        
        # Edge case handling
        self.hand_detected = False
        self.stable_detection_count = 0
        self.min_stable_frames = 1
        
        # Finger detection
        self.finger_tip_indices = [4, 8, 12, 16, 20]
        self.finger_pip_indices = [3, 6, 10, 14, 18]
        self.finger_debug_info = []
        self.finger_debug_count = 0
        
        # Volume gesture state (thumb-index pinch with M+R+P extended)
        self.pinch_distance_px = 40
        self.volume_sensitivity = -0.0035  # negative so upward movement increases volume (per px)

        self.volume = 1.0  # 0..1 scale
        self.volume_prev_y = None
        self.volume_curr_y = None
        self.volume_touching = False
        self.volume_distance_px = 0.0
        # Deck 2 volume state
        self.volume2 = 1.0  # 0..1 scale
        self.volume2_prev_y = None
        self.volume2_curr_y = None
        self.volume2_touching = False
        self.volume2_distance_px = 0.0
        
        # Effect 1 ("rockstar") detection flags per deck
        self.effect1_detected = False
        self.effect1_detected2 = False
        
        # Thumbs up gesture tracking
        self.thumbs_up_detected = False
        self.previous_thumbs_up = False
        # Deck 2 thumbs up tracking
        self.thumbs_up_detected2 = False
        self.previous_thumbs_up2 = False
        
        # MIDI Integration
        self.midi_device = None
        self.midi_enabled = False
        self.midi_send_rate = 30  # Hz - limit MIDI message rate
        self.last_midi_send_time = 0
        self.midi_thread = None
        self.midi_queue = []
        self.midi_lock = threading.Lock()
        
        self.init_midi()
    
    def init_midi(self):
        """Initialize MIDI device"""
        if not MIDI_AVAILABLE:
            print("MIDI functionality disabled - missing dependencies")
            return
        
        try:
            self.midi_device = VirtualMIDIDevice("AI_DJ_Gestures")
            if self.midi_device.midi_out:
                self.midi_enabled = True
                print("✓ MIDI device initialized successfully")
                self.midi_device.print_midi_mapping_info()
                
                # Start MIDI thread for smooth sending
                self.midi_thread = threading.Thread(target=self.midi_worker, daemon=True)
                self.midi_thread.start()
            else:
                print("✗ Failed to initialize MIDI device")
        except Exception as e:
            print(f"✗ MIDI initialization error: {e}")
    
    def midi_worker(self):
        """Background thread for sending MIDI messages at controlled rate"""
        while self.midi_enabled:
            try:
                current_time = time.time()
                
                # Check if it's time to send MIDI updates
                if current_time - self.last_midi_send_time >= (1.0 / self.midi_send_rate):
                    with self.midi_lock:
                        if self.midi_device:
                            # Send current knob values
                            sent_count = self.midi_device.update_all_controls(
                                self.knobs, 
                                self.active_knob
                            )
                            # Send deck 2 knob values on Deck 2 (deck numbering 1/2)
                            sent_count2 = self.midi_device.update_all_controls_on_channel(
                                self.knobs2,
                                self.active_knob2,
                                2
                            )
                            # Send channel volumes (0..1) on both decks
                            try:
                                self.midi_device.update_control_on_channel('volume', float(self.volume), deck=1)
                                self.midi_device.update_control_on_channel('volume', float(self.volume2), deck=2)
                            except Exception:
                                pass
                            
                            if (sent_count > 0 or sent_count2 > 0) and self.show_console_output:
                                print(f"MIDI: Sent deck1={sent_count} deck2={sent_count2} control updates")
                    
                    self.last_midi_send_time = current_time
                
                time.sleep(0.01)  # Small sleep to prevent busy waiting
                
            except Exception as e:
                if self.show_console_output:
                    print(f"MIDI worker error: {e}")
                time.sleep(0.1)
    
    def close_midi(self):
        """Clean up MIDI resources"""
        self.midi_enabled = False
        if self.midi_device:
            self.midi_device.close()
        if self.midi_thread and self.midi_thread.is_alive():
            self.midi_thread.join(timeout=1.0)
    
    def process_frame(self, frame):
        """Process frame with optimizations"""
        start_time = time.time()
        
        # Reset thumbs up indicators at the start of each frame.
        # They will be turned on only if hands exist and gesture passes.
        self.thumbs_up_detected = False
        self.thumbs_up_detected2 = False
        # Reset effect flags each frame (set true when gesture passes)
        self.effect1_detected = False
        self.effect1_detected2 = False
        
        # Resize frame for faster processing if needed
        height, width = frame.shape[:2]
        if width > 1280:
            scale = 1280 / width
            new_width = int(width * scale)
            new_height = int(height * scale)
            frame = cv2.resize(frame, (new_width, new_height))
        
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the frame
        results = self.hands.process(rgb_frame)
        
        # Extract landmark data
        landmark_data = []
        
        # Reset per-frame volume gesture aggregation (per deck)
        volume1_updated_this_frame = False
        volume2_updated_this_frame = False
        self.volume_touching = False
        self.volume_distance_px = 0.0
        self.volume2_touching = False
        self.volume2_distance_px = 0.0
        
        if results.multi_hand_landmarks:
            for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                # Draw landmarks if enabled
                if self.show_all_landmarks:
                    self.mp_draw.draw_landmarks(
                        frame, 
                        hand_landmarks, 
                        self.mp_hands.HAND_CONNECTIONS
                    )
                
                # Extract key landmarks
                h, w = frame.shape[:2]
                hand_data = []
                
                for i, landmark_idx in enumerate(self.key_landmarks):
                    landmark = hand_landmarks.landmark[landmark_idx]
                    x = int(landmark.x * w)
                    y = int(landmark.y * h)
                    
                    hand_data.append({
                        'name': self.landmark_names[i],
                        'x': x,
                        'y': y,
                        'z': landmark.z
                    })
                    
                    # Draw landmarks with color coding
                    if i == 0:  # Wrist
                        color = (0, 255, 255)  # Yellow
                    elif 1 <= i <= 4:  # Thumb
                        color = (0, 0, 255)    # Red
                    elif 5 <= i <= 8:  # Index
                        color = (0, 255, 0)    # Green
                    elif 9 <= i <= 12:  # Middle
                        color = (255, 0, 0)    # Blue
                    elif 13 <= i <= 16:  # Ring
                        color = (255, 0, 255)  # Magenta
                    else:  # Pinky (17-20)
                        color = (255, 255, 0)  # Cyan
                    
                    cv2.circle(frame, (x, y), 4, color, -1)
                    cv2.putText(frame, str(i), (x + 6, y - 6), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1)
                
                landmark_data.append({
                    'hand_index': hand_idx,
                    'landmarks': hand_data
                })
                
                # Determine handedness for this hand early
                raw_label = results.multi_handedness[hand_idx].classification[0].label

                # ---------------- Volume + Rockstar gesture detection (per deck) ----------------
                try:
                    # Extended finger flags
                    flags = self.get_extended_finger_flags(hand_landmarks.landmark)
                    mrp_extended = flags.get('middle', False) and flags.get('ring', False) and flags.get('pinky', False)

                    # Thumb (4) and Index (8) pixel coords
                    thumb_tip = hand_landmarks.landmark[4]
                    index_tip = hand_landmarks.landmark[8]
                    x4, y4 = int(thumb_tip.x * w), int(thumb_tip.y * h)
                    x8, y8 = int(index_tip.x * w), int(index_tip.y * h)
                    dx = x4 - x8
                    dy = y4 - y8
                    dist_px = (dx*dx + dy*dy) ** 0.5

                    # Gesture active if M+R+P extended and pinch distance < 50px
                    if mrp_extended and dist_px < self.pinch_distance_px:
                        midpoint_y = int((y4 + y8) / 2)
                        if raw_label == 'Left':
                            self.volume_touching = True
                            self.volume_distance_px = float(dist_px)
                            if self.volume_curr_y is None:
                                self.volume_prev_y = None
                                self.volume_curr_y = midpoint_y
                            else:
                                self.volume_prev_y = self.volume_curr_y
                                self.volume_curr_y = midpoint_y
                                if self.volume_prev_y is not None:
                                    delta = self.volume_curr_y - self.volume_prev_y
                                    self.volume += self.volume_sensitivity * float(delta)
                                    if self.volume < 0.0:
                                        self.volume = 0.0
                                    elif self.volume > 1.0:
                                        self.volume = 1.0
                            volume1_updated_this_frame = True
                        elif raw_label == 'Right':
                            self.volume2_touching = True
                            self.volume2_distance_px = float(dist_px)
                            if self.volume2_curr_y is None:
                                self.volume2_prev_y = None
                                self.volume2_curr_y = midpoint_y
                            else:
                                self.volume2_prev_y = self.volume2_curr_y
                                self.volume2_curr_y = midpoint_y
                                if self.volume2_prev_y is not None:
                                    delta2 = self.volume2_curr_y - self.volume2_prev_y
                                    self.volume2 += self.volume_sensitivity * float(delta2)
                                    if self.volume2 < 0.0:
                                        self.volume2 = 0.0
                                    elif self.volume2 > 1.0:
                                        self.volume2 = 1.0
                            volume2_updated_this_frame = True
                    
                    # Rockstar gesture: ONLY index and pinky are extended
                    is_rockstar = (
                        flags.get('index', False) and
                        flags.get('pinky', False) and
                        not flags.get('middle', False) and
                        not flags.get('ring', False)
                    )
                    if is_rockstar:
                        if raw_label == 'Left':
                            self.effect1_detected = True
                        elif raw_label == 'Right':
                            self.effect1_detected2 = True
                    
                except Exception:
                    # Keep volume state unchanged on errors for robustness
                    pass

                # Frame was flipped before processing, so MediaPipe labels are mirrored.
                # Flip deck mapping per request: map raw 'Left' → Deck 1, raw 'Right' → Deck 2
                if raw_label == 'Left':
                    # Deck 1
                    self.current_pointer_angle = self.update_knob_values_deck1(hand_landmarks.landmark)
                    current_thumbs_up = self.is_thumbs_up(hand_landmarks.landmark, raw_label)
                    if current_thumbs_up and not self.previous_thumbs_up:
                        self.send_play_pause_midi(deck=1)
                        if self.show_console_output:
                            print("Thumbs up detected - sending play/pause MIDI signal")
                    self.previous_thumbs_up = current_thumbs_up
                    self.thumbs_up_detected = current_thumbs_up
                elif raw_label == 'Right':
                    # Deck 2
                    self.current_pointer_angle2 = self.update_knob_values_deck2(hand_landmarks.landmark)
                    current_thumbs_up2 = self.is_thumbs_up(hand_landmarks.landmark, raw_label)
                    if current_thumbs_up2 and not self.previous_thumbs_up2:
                        self.send_play_pause_midi(deck=2)
                        if self.show_console_output:
                            print("Thumbs up detected (deck 2) - sending play/pause MIDI signal")
                    self.previous_thumbs_up2 = current_thumbs_up2
                    self.thumbs_up_detected2 = current_thumbs_up2
        
        # If no active volume gesture this frame, reset trackers per deck
        if not volume1_updated_this_frame:
            self.volume_touching = False
            self.volume_distance_px = 0.0
            self.volume_prev_y = None
            self.volume_curr_y = None
        if not volume2_updated_this_frame:
            self.volume2_touching = False
            self.volume2_distance_px = 0.0
            self.volume2_prev_y = None
            self.volume2_curr_y = None
        
        # Track processing time
        process_time = time.time() - start_time
        self.frame_times.append(process_time)
        
        return frame, landmark_data
    
    def count_fingers(self, landmarks):
        """Extended finger counting using colinearity and radial distance"""
        try:
            
            # Convert landmarks to numpy array
            lms = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])
            
            fingers_extended = 0
            debug_info = []
            
            # Finger chain definitions: [MCP, PIP, DIP, TIP]
            finger_chains = [
                ("Index", [5, 6, 7, 8]),
                ("Middle", [9, 10, 11, 12]),
                ("Ring", [13, 14, 15, 16]),
                ("Pinky", [17, 18, 19, 20])
            ]
            
            # Calculate palm scale (wrist to index MCP distance)
            wrist = lms[0]
            palm_scale = np.linalg.norm(lms[5] - wrist)
            
            if palm_scale < 0.01:  # Too small, invalid
                self.finger_debug_info = ["INVALID: Palm too small"]
                self.finger_debug_count = 0
                return 0
            
            for finger_name, chain in finger_chains:
                try:
                    mcp, pip, dip, tip = [lms[i] for i in chain]
                    
                    # Check colinearity (straightness) using segment vectors
                    s0 = pip - mcp    # MCP to PIP
                    s1 = dip - pip    # PIP to DIP  
                    s2 = tip - dip    # DIP to TIP
                    
                    def safe_cosine(a, b):
                        na = np.linalg.norm(a)
                        nb = np.linalg.norm(b)
                        if na < 1e-8 or nb < 1e-8:
                            return 1.0
                        return np.clip(np.dot(a, b) / (na * nb), -1.0, 1.0)
                    
                    # Calculate curvature (total bend angle)
                    cos01 = safe_cosine(s0, s1)
                    cos12 = safe_cosine(s1, s2)
                    
                    bend_angle_01 = math.degrees(math.acos(np.clip(cos01, -1.0, 1.0)))
                    bend_angle_12 = math.degrees(math.acos(np.clip(cos12, -1.0, 1.0)))
                    total_curvature = bend_angle_01 + bend_angle_12
                    
                    # Check if finger is straight enough (curvature approach)
                    angle_threshold = 40.0  # degrees
                    is_straight = total_curvature < angle_threshold
                    
                    # Check radial monotonicity (tip farther from wrist than base)
                    r_mcp = np.linalg.norm(mcp - wrist)
                    r_pip = np.linalg.norm(pip - wrist)
                    r_dip = np.linalg.norm(dip - wrist)
                    r_tip = np.linalg.norm(tip - wrist)
                    
                    # Ensure distances increase along the finger with some tolerance
                    margin = 0.03 * palm_scale
                    is_monotonic = (r_mcp + margin < r_pip < r_dip < r_tip - margin/2)
                    
                    # Finger is extended if both conditions are met
                    is_extended = is_straight and is_monotonic
                    
                    if is_extended:
                        fingers_extended += 1
                        debug_info.append(f"{finger_name}: EXTENDED (curve={total_curvature:.1f}°)")
                    else:
                        reason = "CURVED" if not is_straight else "NOT_MONOTONIC"
                        debug_info.append(f"{finger_name}: {reason} (curve={total_curvature:.1f}°)")
                        
                except (IndexError, AttributeError) as e:
                    debug_info.append(f"{finger_name}: ERROR")
                    continue
            
            self.finger_debug_info = debug_info
            self.finger_debug_count = fingers_extended
            
            return max(0, min(4, fingers_extended))
            
        except Exception as e:
            self.finger_debug_info = [f"COUNT ERROR: {e}"]
            self.finger_debug_count = 0
            return 0
    
    def get_extended_finger_flags(self, landmarks):
        """Return which fingers (Index, Middle, Ring, Pinky) are extended using curvature + radial tests."""
        flags = {'thumb': False, 'index': False, 'middle': False, 'ring': False, 'pinky': False}
        try:
            lms = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])
            wrist = lms[0]
            palm_scale = np.linalg.norm(lms[5] - wrist)
            if palm_scale < 0.01:
                return flags
            finger_chains = [
                ('thumb', [1, 2, 3, 4]),
                ('index', [5, 6, 7, 8]),
                ('middle', [9, 10, 11, 12]),
                ('ring', [13, 14, 15, 16]),
                ('pinky', [17, 18, 19, 20])
            ]
            for key, chain in finger_chains:
                mcp, pip, dip, tip = [lms[i] for i in chain]
                s0 = pip - mcp
                s1 = dip - pip
                s2 = tip - dip
                def safe_cos(a, b):
                    na = np.linalg.norm(a); nb = np.linalg.norm(b)
                    if na < 1e-8 or nb < 1e-8:
                        return 1.0
                    return np.clip(np.dot(a, b) / (na * nb), -1.0, 1.0)
                bend01 = math.degrees(math.acos(np.clip(safe_cos(s0, s1), -1.0, 1.0)))
                bend12 = math.degrees(math.acos(np.clip(safe_cos(s1, s2), -1.0, 1.0)))
                curvature = bend01 + bend12
                angle_threshold = 40.0
                is_straight = curvature < angle_threshold
                r_mcp = np.linalg.norm(mcp - wrist)
                r_pip = np.linalg.norm(pip - wrist)
                r_dip = np.linalg.norm(dip - wrist)
                r_tip = np.linalg.norm(tip - wrist)
                margin = 0.03 * palm_scale
                is_monotonic = (r_mcp + margin < r_pip < r_dip < r_tip - margin/2)
                flags[key] = bool(is_straight and is_monotonic)
            return flags
        except Exception:
            return flags
    
    def calculate_pointer_angle(self, landmarks):
        """Calculate angle between wrist and pointer finger tip"""
        try:
            wrist = landmarks[0]
            pointer_tip = landmarks[8]
            
            if (wrist.x < 0 or wrist.x > 1 or wrist.y < 0 or wrist.y > 1 or
                pointer_tip.x < 0 or pointer_tip.x > 1 or pointer_tip.y < 0 or pointer_tip.y > 1):
                return 0.0
            
            dx = pointer_tip.x - wrist.x
            dy = pointer_tip.y - wrist.y
            
            distance = (dx**2 + dy**2)**0.5
            if distance < 0.01:
                return 0.0
            
            angle = math.degrees(-math.atan2(dx, dy))
            
            while angle > 180:
                angle -= 360
            while angle < -180:
                angle += 360
                
            return angle
            
        except Exception as e:
            if self.show_console_output:
                print(f"Error calculating angle: {e}")
            return 0.0
    
    def update_knob_values_deck1(self, landmarks):
        """Update DJ knob values with MIDI output"""
        try:
            if not landmarks or len(landmarks) < 21:
                self.handle_detection_loss()
                return 0.0
            
            required_landmarks = [0, 6, 8]
            for idx in required_landmarks:
                if landmarks[idx].x < 0 or landmarks[idx].x > 1 or landmarks[idx].y < 0 or landmarks[idx].y > 1:
                    self.handle_detection_loss()
                    return 0.0
            
            # Determine which specific fingers are extended
            ext_flags = self.get_extended_finger_flags(landmarks)
            finger_count = int(ext_flags.get('index', False)) + int(ext_flags.get('middle', False)) + int(ext_flags.get('ring', False)) + int(ext_flags.get('pinky', False))
            current_angle = self.calculate_pointer_angle(landmarks)
            
            self.previous_finger_count = self.current_finger_count
            self.previous_active_knob = self.active_knob
            self.current_finger_count = finger_count
            
            # Determine target knob
            target_knob = None
            if ext_flags.get('index', False) and not ext_flags.get('middle', False) and not ext_flags.get('ring', False) and not ext_flags.get('pinky', False):
                target_knob = 'filter'  # 1 finger: index only
            elif ext_flags.get('index', False) and ext_flags.get('middle', False) and not ext_flags.get('ring', False) and not ext_flags.get('pinky', False):
                target_knob = 'low'     # 2 fingers: index + middle
            elif ext_flags.get('index', False) and ext_flags.get('middle', False) and ext_flags.get('ring', False) and not ext_flags.get('pinky', False):
                target_knob = 'mid'     # 3 fingers: index + middle + ring
            elif ext_flags.get('index', False) and ext_flags.get('middle', False) and ext_flags.get('ring', False) and ext_flags.get('pinky', False):
                target_knob = 'high'    # 4 fingers: index + middle + ring + pinky
            
            pointer_up = self.is_pointer_finger_up(landmarks)
            
            if pointer_up and target_knob:
                self.stable_detection_count += 1
            else:
                self.stable_detection_count = 0
            
            # Gesture control logic
            if target_knob and pointer_up and not self.knob_locked:
                
                # Starting new gesture or switching knobs
                if self.active_knob != target_knob or not self.gesture_active:
                    self.active_knob = target_knob
                    self.gesture_active = True
                    self.previous_angle = current_angle
                    
                    if self.show_console_output:
                        print(f"Started {target_knob} control at angle {current_angle:.1f}°")
                
                # Continue current gesture
                elif self.active_knob == target_knob and self.gesture_active and self.previous_angle is not None:
                    delta_angle = current_angle - self.previous_angle
                    
                    # Handle angle wraparound
                    if delta_angle > 180:
                        delta_angle -= 360
                    elif delta_angle < -180:
                        delta_angle += 360
                    
                    params = self.knob_params[target_knob]
                    # Sensitivity: 180 degrees of rotation covers the full range
                    sensitivity = params['range'] / 180.0
                    scaled_delta = delta_angle * sensitivity

                    new_value = self.knobs[target_knob] + scaled_delta
                    self.knobs[target_knob] = max(params['min'], min(params['max'], new_value))
                    
                    self.previous_angle = current_angle
            
            # End gesture when pointer goes down
            elif not pointer_up and self.gesture_active:
                if self.active_knob:
                    if self.show_console_output:
                        print(f"Gesture ended - {self.active_knob} locked at {self.knobs[self.active_knob]:.2f}")
                
                self.gesture_active = False
                self.knob_locked = True
                self.previous_angle = None
            
            # Reset when no valid gesture
            elif target_knob is None:
                self.knob_locked = False
                self.gesture_active = False
                self.previous_angle = None
                self.active_knob = None
            
            self.hand_detected = True
            return current_angle
            
        except Exception as e:
            if self.show_console_output:
                print(f"Error in update_knob_values_deck1: {e}")
            self.handle_detection_loss()
            return 0.0
    
    def is_pointer_finger_up(self, landmarks):
        """Check if pointer finger is up"""
        try:
            wrist = landmarks[0]
            index_tip = landmarks[8]
            index_mcp = landmarks[5]
            
            if (wrist.x < 0 or wrist.x > 1 or wrist.y < 0 or wrist.y > 1 or
                index_tip.x < 0 or index_tip.x > 1 or index_tip.y < 0 or index_tip.y > 1 or
                index_mcp.x < 0 or index_mcp.x > 1 or index_mcp.y < 0 or index_mcp.y > 1):
                return False
            
            tip_to_wrist = ((index_tip.x - wrist.x)**2 + (index_tip.y - wrist.y)**2)**0.5
            mcp_to_wrist = ((index_mcp.x - wrist.x)**2 + (index_mcp.y - wrist.y)**2)**0.5
            
            return tip_to_wrist > mcp_to_wrist * 1.15
            
        except Exception:
            return False
    
    def update_knob_values_deck2(self, landmarks):
        """Duplicate of update_knob_values for Deck 2 (right hand), independent state"""
        try:
            if not landmarks or len(landmarks) < 21:
                # Do not affect deck 1 state here
                return 0.0
            
            required_landmarks = [0, 6, 8]
            for idx in required_landmarks:
                if landmarks[idx].x < 0 or landmarks[idx].x > 1 or landmarks[idx].y < 0 or landmarks[idx].y > 1:
                    return 0.0
            
            # Determine which specific fingers are extended (deck 2)
            ext_flags = self.get_extended_finger_flags(landmarks)
            finger_count = int(ext_flags.get('index', False)) + int(ext_flags.get('middle', False)) + int(ext_flags.get('ring', False)) + int(ext_flags.get('pinky', False))
            current_angle = self.calculate_pointer_angle(landmarks)
            
            self.previous_finger_count2 = self.current_finger_count2
            self.current_finger_count2 = finger_count
            prev_active = self.active_knob2
            
            # Determine target knob
            target_knob = None
            if ext_flags.get('index', False) and not ext_flags.get('middle', False) and not ext_flags.get('ring', False) and not ext_flags.get('pinky', False):
                target_knob = 'filter'  # 1 finger: index only
            elif ext_flags.get('index', False) and ext_flags.get('middle', False) and not ext_flags.get('ring', False) and not ext_flags.get('pinky', False):
                target_knob = 'low'     # 2 fingers: index + middle
            elif ext_flags.get('index', False) and ext_flags.get('middle', False) and ext_flags.get('ring', False) and not ext_flags.get('pinky', False):
                target_knob = 'mid'     # 3 fingers: index + middle + ring
            elif ext_flags.get('index', False) and ext_flags.get('middle', False) and ext_flags.get('ring', False) and ext_flags.get('pinky', False):
                target_knob = 'high'    # 4 fingers: index + middle + ring + pinky
            
            pointer_up = self.is_pointer_finger_up(landmarks)
            
            if target_knob and pointer_up and not self.knob_locked2:
                # Starting new gesture or switching knobs
                if self.active_knob2 != target_knob or not self.gesture_active2:
                    self.active_knob2 = target_knob
                    self.gesture_active2 = True
                    self.previous_angle2 = current_angle
                    if self.show_console_output and prev_active != self.active_knob2:
                        print(f"[Deck2] Started {target_knob} control at angle {current_angle:.1f}°")
                elif self.active_knob2 == target_knob and self.gesture_active2 and self.previous_angle2 is not None:
                    delta_angle = current_angle - self.previous_angle2
                    if delta_angle > 180:
                        delta_angle -= 360
                    elif delta_angle < -180:
                        delta_angle += 360
                    params = self.knob_params[target_knob]
                    sensitivity = params['range'] / 180.0
                    scaled_delta = delta_angle * sensitivity
                    new_value = self.knobs2[target_knob] + scaled_delta
                    self.knobs2[target_knob] = max(params['min'], min(params['max'], new_value))
                    self.previous_angle2 = current_angle
            elif not pointer_up and self.gesture_active2:
                if self.active_knob2 and self.show_console_output:
                    print(f"[Deck2] Gesture ended - {self.active_knob2} locked at {self.knobs2[self.active_knob2]:.2f}")
                self.gesture_active2 = False
                self.knob_locked2 = True
                self.previous_angle2 = None
            elif target_knob is None:
                self.knob_locked2 = False
                self.gesture_active2 = False
                self.previous_angle2 = None
                self.active_knob2 = None
            
            return current_angle
        except Exception as e:
            if self.show_console_output:
                print(f"Error in update_knob_values_deck2: {e}")
            return 0.0
    
    def is_thumbs_up(self, landmarks, handedness):
        """
        Check for thumbs-up using strict deck-specific x/y constraints:
        - Record pixel locations for all 21 points.
        - Deck 1 (raw 'Left'): thumb 0..4 must be strictly LEFT of all 5..20.
        - Deck 2 (raw 'Right'): thumb 0..4 must be strictly RIGHT of all 5..20.
        - Ascending Y for the thumb chain: y0 < y1 < y2 < y3 < y4.
        """
        try:
            # Record pixel locations of all points (store for debugging/inspection)
            # Assumes landmark.x, landmark.y are pixel coordinates or already scaled.
            self.last_landmark_pixels = [
                (int(round(lm.x)), int(round(lm.y))) for lm in landmarks
            ]

            # Safety: ensure we have at least 21 landmarks
            if len(landmarks) < 21:
                return False

            # Extract X and Y for required indices
            thumb_indices = [0, 1, 2, 3, 4]
            other_indices = list(range(5, 21))

            thumb_x = [landmarks[i].x for i in thumb_indices]
            other_x = [landmarks[i].x for i in other_indices]

            thumb_y = [landmarks[i].y for i in thumb_indices]

            # X-side constraint (deck-specific, no other allowance)
            all_left = max(thumb_x) < min(other_x)
            all_right = min(thumb_x) > max(other_x)
            if handedness == 'Left':
                # Deck 1 must be LEFT of others
                x_side_ok = all_left
            elif handedness == 'Right':
                # Deck 2 must be RIGHT of others
                x_side_ok = all_right
            else:
                x_side_ok = False

            # Descending Y constraint for thumb chain (image Y grows downward):
            # y0 > y1 > y2 > y3 > y4
            descending_y = (
                thumb_y[0] > thumb_y[1] > thumb_y[2] > thumb_y[3] > thumb_y[4]
            )

            valid = bool(x_side_ok and descending_y)

            if valid:
                # Prepare debug sets sorted by X for on-screen display
                thumb_pts = [
                    (i, (int(round(landmarks[i].x)), int(round(landmarks[i].y))))
                    for i in thumb_indices
                ]
                other_pts = [
                    (i, (int(round(landmarks[i].x)), int(round(landmarks[i].y))))
                    for i in other_indices
                ]
                thumb_pts_sorted = sorted(thumb_pts, key=lambda t: t[1][0])
                other_pts_sorted = sorted(other_pts, key=lambda t: t[1][0])
                self.debug_thumb_sets = {
                    'thumb': thumb_pts_sorted,
                    'other': other_pts_sorted,
                }
            else:
                self.debug_thumb_sets = None

            return valid
        except Exception:
            return False

    
    def send_play_pause_midi(self, deck: int):
        """Send play/pause MIDI signal (CC 18, 0x12) as per XML configuration"""
        if self.midi_device and self.midi_enabled:
            try:
                # Deck 1 uses deck=1
                self.midi_device.send_toggle('play', deck)
                if self.show_console_output:
                    print(f"MIDI: Sent play/pause toggle (CC 18) for deck {deck}")
            except Exception as e:
                if self.show_console_output:
                    print(f"Error sending play/pause MIDI for deck {deck}: {e}")

    def handle_detection_loss(self):
        """Handle cases where hand detection is lost"""
        self.hand_detected = False
        self.stable_detection_count = 0
        self.gesture_active = False
        self.previous_angle = None
    
    def draw_dj_interface(self, frame):
        """Draw DJ control interface with MIDI status"""
        _, width = frame.shape[:2]
        
        # DJ Interface positioned on the left side (Deck 1)
        interface_x = 20  # Wider box for more space
        interface_y = 30
        
        # Background
        cv2.rectangle(frame, (interface_x - 10, interface_y - 10), 
                     (interface_x + 440, interface_y + 340), (40, 40, 40), -1)
        cv2.rectangle(frame, (interface_x - 10, interface_y - 10), 
                     (interface_x + 440, interface_y + 340), (255, 255, 255), 2)
        
        # Title
        cv2.putText(frame, "AI DJ CONTROL + MIDI", (interface_x, interface_y + 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # MIDI Status
        y_pos = interface_y + 35
        midi_status = "CONNECTED" if self.midi_enabled else "DISCONNECTED"
        midi_color = (0, 255, 0) if self.midi_enabled else (0, 0, 255)
        cv2.putText(frame, f"MIDI: {midi_status}", (interface_x, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, midi_color, 1)
        
        # Gesture info
        y_pos += 25
        finger_text = f"Fingers: {self.current_finger_count}"
        cv2.putText(frame, finger_text, (interface_x, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        y_pos += 20
        active_text = f"Active: {self.active_knob or 'None'}"
        cv2.putText(frame, active_text, (interface_x, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        y_pos += 20
        thumbs_up_text = f"Thumbs Up: {'YES' if self.thumbs_up_detected else 'NO'}"
        thumbs_up_color = (0, 255, 0) if self.thumbs_up_detected else (128, 128, 128)
        cv2.putText(frame, thumbs_up_text, (interface_x, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, thumbs_up_color, 1)
        
        y_pos += 20
        rockstar_text = f"Rockstar: {'YES' if self.effect1_detected else 'NO'}"
        rockstar_color = (0, 215, 255) if self.effect1_detected else (128, 128, 128)
        cv2.putText(frame, rockstar_text, (interface_x, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, rockstar_color, 1)
        
        y_pos += 20
        gesture_text = f"Gesture: {'Active' if self.gesture_active else 'Inactive'}"
        cv2.putText(frame, gesture_text, (interface_x, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0) if self.gesture_active else (255, 100, 100), 1)
        
        # Volume gesture overlay
        y_pos += 20
        pinch_text = f"Thumb+Index Touch: {'YES' if self.volume_touching else 'NO'}"
        pinch_color = (0, 255, 0) if self.volume_touching else (128, 128, 128)
        cv2.putText(frame, pinch_text, (interface_x, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, pinch_color, 1)
        y_pos += 20
        cv2.putText(frame, f"Touch Dist: {self.volume_distance_px:.0f}px", (interface_x, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Volume value and bar (0..1)
        y_pos += 20
        cv2.putText(frame, f"Volume: {self.volume:.2f}", (interface_x, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        bar_x = interface_x + 120
        bar_y = y_pos - 10
        bar_width = 150
        bar_height = 10
        # Background
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (80, 80, 80), -1)
        # Fill
        fill_width = int(self.volume * bar_width)
        fill_color = (0, 200, 0) if self.volume_touching else (160, 160, 160)
        if fill_width > 0:
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height), fill_color, -1)
        # Border
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (255, 255, 255), 1)
        
        # Show current pointer angle
        if hasattr(self, 'current_pointer_angle'):
            y_pos += 20
            angle_text = f"Angle: {self.current_pointer_angle:.1f}°"
            cv2.putText(frame, angle_text, (interface_x, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Draw knobs with MIDI CC info
        y_pos += 40
        knob_colors = {
            'filter': (255, 255, 0),  # Yellow
            'low': (0, 255, 0),       # Green  
            'mid': (0, 165, 255),     # Orange
            'high': (0, 0, 255)       # Red
        }
        
        finger_mapping = {
            'filter': '1F',
            'low': '2F', 
            'mid': '3F',
            'high': '4F'
        }
        
        cc_mapping = {
            'filter': 'CC1',
            'low': 'CC2',
            'mid': 'CC3',
            'high': 'CC4'
        }
        
        feedback_values = self.midi_device.get_feedback_values() if self.midi_device else {}

        for knob_name in self.knob_names:
            knob_value = self.knobs[knob_name]
            color = knob_colors[knob_name]
            
            # Knob label with MIDI CC
            label = f"{finger_mapping[knob_name]} {knob_name.upper()} ({cc_mapping[knob_name]})"
            cv2.putText(frame, label, (interface_x, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            # Knob value and MIDI value
            angle_text = f"{knob_value:+6.1f}°"
            if self.midi_device:
                midi_value = self.midi_device.value_to_midi(knob_name, knob_value)
            else:
                midi_value = 0
            
            feedback_val = feedback_values.get(knob_name, 0)

            sent_text = f"Sent:{midi_value:3d}"
            recv_text = f"Recv:{feedback_val:3d}"
            
            cv2.putText(frame, f"{knob_value:.2f}", (interface_x + 120, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            cv2.putText(frame, sent_text, (interface_x + 180, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
            cv2.putText(frame, recv_text, (interface_x + 250, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 255, 150), 1)
            
            # Knob visualization bar
            bar_x = interface_x + 320
            bar_y = y_pos - 8
            bar_width = 60
            bar_height = 10
            
            # Background bar
            cv2.rectangle(frame, (bar_x, bar_y), 
                         (bar_x + bar_width, bar_y + bar_height), (100, 100, 100), -1)
            
            # Value bar
            params = self.knob_params[knob_name]
            normalized_value = (knob_value - params['min']) / params['range']
            value_width = int(normalized_value * bar_width)
            if knob_value != params['default']:
                cv2.rectangle(frame, (bar_x, bar_y), 
                             (bar_x + value_width, bar_y + bar_height), color, -1)
            
            # Center line
            center_x = bar_x + int((params['default'] - params['min']) / params['range'] * bar_width)
            cv2.line(frame, (center_x, bar_y), (center_x, bar_y + bar_height), 
                    (255, 255, 255), 1)
            
            # Highlight active knob
            if self.active_knob == knob_name:
                cv2.rectangle(frame, (interface_x - 5, y_pos - 12), 
                             (interface_x + 440, y_pos + 8), (255, 255, 255), 2)
            
            y_pos += 25

        # -------------------- Deck 2 UI (right side) --------------------
        interface2_x = width - 460
        interface2_y = 30
        
        # Background
        cv2.rectangle(frame, (interface2_x - 10, interface2_y - 10), 
                     (interface2_x + 440, interface2_y + 340), (40, 40, 40), -1)
        cv2.rectangle(frame, (interface2_x - 10, interface2_y - 10), 
                     (interface2_x + 440, interface2_y + 340), (255, 255, 255), 2)
        
        # Title
        cv2.putText(frame, "AI DJ CONTROL + MIDI (Deck 2)", (interface2_x, interface2_y + 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # MIDI Status
        y2 = interface2_y + 35
        midi_status2 = "CONNECTED" if self.midi_enabled else "DISCONNECTED"
        midi_color2 = (0, 255, 0) if self.midi_enabled else (0, 0, 255)
        cv2.putText(frame, f"MIDI: {midi_status2}", (interface2_x, y2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, midi_color2, 1)
        
        # Gesture info Deck 2
        y2 += 25
        finger_text2 = f"Fingers: {self.current_finger_count2}"
        cv2.putText(frame, finger_text2, (interface2_x, y2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        y2 += 20
        active_text2 = f"Active: {self.active_knob2 or 'None'}"
        cv2.putText(frame, active_text2, (interface2_x, y2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        y2 += 20
        thumbs_up_text2 = f"Thumbs Up: {'YES' if self.thumbs_up_detected2 else 'NO'}"
        thumbs_up_color2 = (0, 255, 0) if self.thumbs_up_detected2 else (128, 128, 128)
        cv2.putText(frame, thumbs_up_text2, (interface2_x, y2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, thumbs_up_color2, 1)
        
        y2 += 20
        rockstar_text2 = f"Rockstar: {'YES' if self.effect1_detected2 else 'NO'}"
        rockstar_color2 = (0, 215, 255) if self.effect1_detected2 else (128, 128, 128)
        cv2.putText(frame, rockstar_text2, (interface2_x, y2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, rockstar_color2, 1)
        
        y2 += 20
        gesture_text2 = f"Gesture: {'Active' if self.gesture_active2 else 'Inactive'}"
        cv2.putText(frame, gesture_text2, (interface2_x, y2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0) if self.gesture_active2 else (255, 100, 100), 1)
        
        # Draw knobs with MIDI CC info Deck 2

        knob_colors2 = knob_colors
        finger_mapping2 = finger_mapping
        cc_mapping2 = cc_mapping
        
        # Deck 2 Volume gesture overlay
        y2 += 20
        pinch_text2 = f"Thumb+Index Touch: {'YES' if self.volume2_touching else 'NO'}"
        pinch_color2 = (0, 255, 0) if self.volume2_touching else (128, 128, 128)
        cv2.putText(frame, pinch_text2, (interface2_x, y2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, pinch_color2, 1)
        y2 += 20
        cv2.putText(frame, f"Touch Dist: {self.volume2_distance_px:.0f}px", (interface2_x, y2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y2 += 20
        cv2.putText(frame, f"Volume: {self.volume2:.2f}", (interface2_x, y2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        bar_x2v = interface2_x + 120
        bar_y2v = y2 - 10
        bar_w2v = 150
        bar_h2v = 10
        cv2.rectangle(frame, (bar_x2v, bar_y2v), (bar_x2v + bar_w2v, bar_y2v + bar_h2v), (80, 80, 80), -1)
        fill_w2v = int(self.volume2 * bar_w2v)
        fill_c2v = (0, 200, 0) if self.volume2_touching else (160, 160, 160)
        if fill_w2v > 0:
            cv2.rectangle(frame, (bar_x2v, bar_y2v), (bar_x2v + fill_w2v, bar_y2v + bar_h2v), fill_c2v, -1)
        cv2.rectangle(frame, (bar_x2v, bar_y2v), (bar_x2v + bar_w2v, bar_y2v + bar_h2v), (255, 255, 255), 1)
        
        # Show current pointer angle Deck 2
        if hasattr(self, 'current_pointer_angle2'):
            y2 += 20
            angle_text2 = f"Angle: {self.current_pointer_angle2:.1f}°"
            cv2.putText(frame, angle_text2, (interface2_x, y2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        y2 += 40
        for knob_name in self.knob_names:
            knob_value2 = self.knobs2[knob_name]
            color2 = knob_colors2[knob_name]
            
            label2 = f"{finger_mapping2[knob_name]} {knob_name.upper()} ({cc_mapping2[knob_name]})"
            cv2.putText(frame, label2, (interface2_x, y2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color2, 1)
            if self.midi_device:
                midi_value2 = self.midi_device.value_to_midi(knob_name, knob_value2)
            else:
                midi_value2 = 0
            
            cv2.putText(frame, f"{knob_value2:.2f}", (interface2_x + 120, y2),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            cv2.putText(frame, f"Sent:{midi_value2:3d}", (interface2_x + 180, y2),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
            
            # Knob visualization bar Deck 2
            bar_x2 = interface2_x + 320
            bar_y2 = y2 - 8
            bar_width2 = 60
            bar_height2 = 10
            cv2.rectangle(frame, (bar_x2, bar_y2), 
                         (bar_x2 + bar_width2, bar_y2 + bar_height2), (100, 100, 100), -1)
            params2 = self.knob_params[knob_name]
            normalized_value2 = (knob_value2 - params2['min']) / params2['range']
            value_width2 = int(normalized_value2 * bar_width2)
            if knob_value2 != params2['default']:
                cv2.rectangle(frame, (bar_x2, bar_y2), 
                             (bar_x2 + value_width2, bar_y2 + bar_height2), color2, -1)
            center_x2 = bar_x2 + int((params2['default'] - params2['min']) / params2['range'] * bar_width2)
            cv2.line(frame, (center_x2, bar_y2), (center_x2, bar_y2 + bar_height2), 
                    (255, 255, 255), 1)
            if self.active_knob2 == knob_name:
                cv2.rectangle(frame, (interface2_x - 5, y2 - 12), 
                             (interface2_x + 440, y2 + 8), (255, 255, 255), 2)
            y2 += 25
    
    def draw_optimized_info(self, frame, landmark_data):
        """Draw information overlay"""
        # Calculate FPS
        if self.frame_times:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
            self.fps_history.append(fps)
            avg_fps = sum(self.fps_history) / len(self.fps_history)
        else:
            avg_fps = 0
        
        # Draw FPS
        cv2.putText(frame, f"FPS: {avg_fps:.1f}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.putText(frame, f"Hands: {len(landmark_data)}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Draw DJ Control Interface
        self.draw_dj_interface(frame)
        
        # Draw prominent thumbs up / rockstar messages when detected for each deck
        height, width = frame.shape[:2]
        if self.thumbs_up_detected or self.thumbs_up_detected2 or self.effect1_detected or self.effect1_detected2:
            text = ""
            if self.effect1_detected or self.effect1_detected2:
                if self.effect1_detected and self.effect1_detected2:
                    text = "ROCKSTAR! (DECK 1 & DECK 2)"
                elif self.effect1_detected:
                    text = "ROCKSTAR! (DECK 1)"
                elif self.effect1_detected2:
                    text = "ROCKSTAR! (DECK 2)"
            elif self.thumbs_up_detected or self.thumbs_up_detected2:
                if self.thumbs_up_detected and self.thumbs_up_detected2:
                    text = "THUMBS UP! (DECK 1 & DECK 2)"
                elif self.thumbs_up_detected:
                    text = "THUMBS UP! (DECK 1)"
                elif self.thumbs_up_detected2:
                    text = "THUMBS UP! (DECK 2)"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 2.0
            thickness = 4
            
            # Get text size to center it
            (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
            
            # Center position
            center_x = (width - text_width) // 2
            center_y = (height + text_height) // 2
            
            # Draw text with outline for better visibility
            # Black outline
            cv2.putText(frame, text, (center_x, center_y), font, font_scale, (0, 0, 0), thickness + 2)
            # Color text
            color = (0, 215, 255) if text.startswith("ROCKSTAR") else (0, 255, 0)
            cv2.putText(frame, text, (center_x, center_y), font, font_scale, color, thickness)
        
        return frame
    
    def run(self):
        """Main loop with MIDI integration"""
        # Initialize camera
        cap = cv2.VideoCapture(0)
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if not cap.isOpened():
            print("Error: Could not open camera")
            return
        
        print("AI DJ Hand Detection with MIDI Started!")
        print("Controls:")
        print("  'q' - Quit")
        print("  'c' - Toggle console output")
        print("  'a' - Toggle landmarks display")
        print("  's' - Save current frame")
        print("  'r' - Reset all knobs to 0")
        print("  't' - Send MIDI test sequence")
        print("  'd' - Toggle MIDI debug output")
        print("\nDJ Controls:")
        print("  1 finger up = Filter knob (CC1)")
        print("  2 fingers up = Low EQ knob (CC2)") 
        print("  3 fingers up = Mid EQ knob (CC3)")
        print("  4 fingers up = High EQ knob (CC4)")
        print("  Rotate hand to control values")
        print("  Close hand to lock current value")
        
        if self.midi_enabled:
            print(f"\n✓ MIDI Output: {self.midi_device.device_name}")
            print("  Connect this device in Mixxx > Preferences > Controllers")
        else:
            print("\n✗ MIDI Output: Disabled")
        
        frame_count = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    continue
                
                frame_count += 1
                
                # Flip for mirror effect
                frame = cv2.flip(frame, 1)
                
                # Process frame
                annotated_frame, landmark_data = self.process_frame(frame)
                
                # Add overlay information
                final_frame = self.draw_optimized_info(annotated_frame, landmark_data)
                
                # Display frame
                cv2.imshow('AI DJ Hand Control with MIDI', final_frame)
                
                # Handle key presses
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('c'):
                    self.show_console_output = not self.show_console_output
                    print(f"Console output: {'ON' if self.show_console_output else 'OFF'}")
                elif key == ord('a'):
                    self.show_all_landmarks = not self.show_all_landmarks
                    print(f"All landmarks: {'ON' if self.show_all_landmarks else 'OFF'}")
                elif key == ord('s'):
                    cv2.imwrite(f'hand_detection_midi_frame_{frame_count}.jpg', final_frame)
                    print(f"Saved frame {frame_count}")
                elif key == ord('r'):
                    # Reset all knobs
                    self.knobs = {k: v['default'] for k, v in self.knob_params.items()}
                    self.previous_angle = None
                    self.active_knob = None
                    self.knob_locked = False
                    self.gesture_active = False
                    print("All knobs reset to default values")
                elif key == ord('t'):
                    # Send MIDI test sequence
                    if self.midi_device:
                        print("Sending MIDI test sequence...")
                        self.midi_device.send_test_sequence()
                    else:
                        print("MIDI device not available")
                elif key == ord('d'):
                    if self.midi_device:
                        self.midi_device.debug = not self.midi_device.debug
                        print(f"MIDI Debug output: {'ON' if self.midi_device.debug else 'OFF'}")
        
        except KeyboardInterrupt:
            print("\nShutting down...")
        
        finally:
            # Cleanup
            cap.release()
            cv2.destroyAllWindows()
            self.close_midi()
            print("AI DJ Hand detection stopped.")

if __name__ == "__main__":
    detector = HandDetectorWithMIDI()
    detector.run()
