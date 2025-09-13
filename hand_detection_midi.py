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
import sys
import os
import threading

# Import our MIDI device
try:
    from midi_virtual_device import VirtualMIDIDevice
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
        self.knobs = {
            'filter': 0.0,    # 1 finger - high/low pass filter
            'low': 0.0,       # 2 fingers - low frequency
            'mid': 0.0,       # 3 fingers - mid frequency
            'high': 0.0       # 4 fingers - high frequency
        }
        self.knob_names = ['filter', 'low', 'mid', 'high']
        
        # Tracking variables for continuous control
        self.stream_initial_angle = None
        self.stream_previous_final_angle = {
            'filter': 0.0, 'low': 0.0, 'mid': 0.0, 'high': 0.0
        }
        self.previous_angle = None
        self.current_finger_count = 0
        self.previous_finger_count = 0
        self.active_knob = None
        self.previous_active_knob = None
        self.knob_locked = False
        self.gesture_active = False
        
        # Edge case handling
        self.hand_detected = False
        self.stable_detection_count = 0
        self.min_stable_frames = 1
        
        # Finger detection
        self.finger_tip_indices = [4, 8, 12, 16, 20]
        self.finger_pip_indices = [3, 6, 10, 14, 18]
        
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
                            
                            if sent_count > 0 and self.show_console_output:
                                print(f"MIDI: Sent {sent_count} control updates")
                    
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
                
                # Update DJ knob values for the first hand only
                if hand_idx == 0:
                    self.current_pointer_angle = self.update_knob_values(hand_landmarks.landmark)
        
        # Track processing time
        process_time = time.time() - start_time
        self.frame_times.append(process_time)
        
        return frame, landmark_data
    
    def count_fingers(self, landmarks):
        """Simple finger counting with debug output"""
        try:
            fingers_up = 0
            debug_info = []
            
            finger_data = [
                ("Index", 8, 6),    # tip, pip
                ("Middle", 12, 10),
                ("Ring", 16, 14),
                ("Pinky", 20, 18)
            ]
            
            for finger_name, tip_idx, pip_idx in finger_data:
                try:
                    tip = landmarks[tip_idx]
                    pip = landmarks[pip_idx]
                    
                    if (tip.x < 0 or tip.x > 1 or tip.y < 0 or tip.y > 1 or
                        pip.x < 0 or pip.x > 1 or pip.y < 0 or pip.y > 1):
                        debug_info.append(f"{finger_name}: INVALID")
                        continue
                    
                    tip_x, tip_y = int(tip.x * 1280), int(tip.y * 720)
                    pip_x, pip_y = int(pip.x * 1280), int(pip.y * 720)
                    
                    is_up = tip.y < pip.y
                    
                    if is_up:
                        fingers_up += 1
                        debug_info.append(f"{finger_name}: UP")
                    else:
                        debug_info.append(f"{finger_name}: DOWN")
                        
                except (IndexError, AttributeError):
                    debug_info.append(f"{finger_name}: ERROR")
                    continue
            
            self.finger_debug_info = debug_info
            self.finger_debug_count = fingers_up
            
            return max(0, min(4, fingers_up))
            
        except Exception as e:
            self.finger_debug_info = [f"COUNT ERROR: {e}"]
            self.finger_debug_count = 0
            return 0
    
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
            
            angle = math.degrees(math.atan2(dy, dx))
            
            while angle > 180:
                angle -= 360
            while angle < -180:
                angle += 360
                
            return angle
            
        except Exception as e:
            if self.show_console_output:
                print(f"Error calculating angle: {e}")
            return 0.0
    
    def update_knob_values(self, landmarks):
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
            
            finger_count = self.count_fingers(landmarks)
            current_angle = self.calculate_pointer_angle(landmarks)
            
            self.previous_finger_count = self.current_finger_count
            self.previous_active_knob = self.active_knob
            self.current_finger_count = finger_count
            
            # Determine target knob
            target_knob = None
            if finger_count == 1:
                target_knob = 'filter'
            elif finger_count == 2:
                target_knob = 'low'
            elif finger_count == 3:
                target_knob = 'mid'
            elif finger_count == 4:
                target_knob = 'high'
            
            pointer_up = self.is_pointer_finger_up(landmarks)
            
            if pointer_up and target_knob:
                self.stable_detection_count += 1
            else:
                self.stable_detection_count = 0
            
            # Gesture control logic
            if target_knob and pointer_up and not self.knob_locked:
                
                # Starting new gesture or switching knobs
                if self.active_knob != target_knob or not self.gesture_active:
                    if self.active_knob:
                        self.stream_previous_final_angle[self.active_knob] = self.knobs[self.active_knob]
                    
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
                    
                    scaled_delta = (135.0 / 50.0) * delta_angle
                    new_value = self.knobs[target_knob] + scaled_delta
                    self.knobs[target_knob] = max(-135.0, min(135.0, new_value))
                    
                    self.previous_angle = current_angle
            
            # End gesture when pointer goes down
            elif not pointer_up and self.gesture_active:
                if self.active_knob:
                    self.stream_previous_final_angle[self.active_knob] = self.knobs[self.active_knob]
                    if self.show_console_output:
                        print(f"Stream ended - {self.active_knob} locked at {self.knobs[self.active_knob]:.1f}")
                
                self.gesture_active = False
                self.knob_locked = True
                self.previous_angle = None
            
            # Reset when no valid gesture
            elif target_knob is None:
                if self.gesture_active and self.active_knob:
                    self.stream_previous_final_angle[self.active_knob] = self.knobs[self.active_knob]
                
                self.knob_locked = False
                self.gesture_active = False
                self.previous_angle = None
                self.active_knob = None
            
            self.hand_detected = True
            return current_angle
            
        except Exception as e:
            if self.show_console_output:
                print(f"Error in update_knob_values: {e}")
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
    
    def handle_detection_loss(self):
        """Handle cases where hand detection is lost"""
        self.hand_detected = False
        self.stable_detection_count = 0
        if self.gesture_active and self.active_knob:
            self.stream_previous_final_angle[self.active_knob] = self.knobs[self.active_knob]
        self.gesture_active = False
        self.previous_angle = None
    
    def draw_dj_interface(self, frame):
        """Draw DJ control interface with MIDI status"""
        height, width = frame.shape[:2]
        
        # DJ Interface positioned on the right side
        interface_x = width - 350  # Wider for MIDI info
        interface_y = 30
        
        # Background
        cv2.rectangle(frame, (interface_x - 10, interface_y - 10), 
                     (width - 10, interface_y + 280), (40, 40, 40), -1)
        cv2.rectangle(frame, (interface_x - 10, interface_y - 10), 
                     (width - 10, interface_y + 280), (255, 255, 255), 2)
        
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
        gesture_text = f"Gesture: {'Active' if self.gesture_active else 'Inactive'}"
        cv2.putText(frame, gesture_text, (interface_x, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0) if self.gesture_active else (255, 100, 100), 1)
        
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
        
        for i, knob_name in enumerate(self.knob_names):
            knob_value = self.knobs[knob_name]
            color = knob_colors[knob_name]
            
            # Knob label with MIDI CC
            label = f"{finger_mapping[knob_name]} {knob_name.upper()} ({cc_mapping[knob_name]})"
            cv2.putText(frame, label, (interface_x, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            # Knob value and MIDI value
            angle_text = f"{knob_value:+6.1f}°"
            midi_value = int((knob_value + 135.0) / 270.0 * 127) if self.midi_device else 0
            midi_text = f"MIDI:{midi_value:3d}"
            
            cv2.putText(frame, angle_text, (interface_x + 120, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            cv2.putText(frame, midi_text, (interface_x + 200, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
            
            # Knob visualization bar
            bar_x = interface_x + 270
            bar_y = y_pos - 8
            bar_width = 60
            bar_height = 10
            
            # Background bar
            cv2.rectangle(frame, (bar_x, bar_y), 
                         (bar_x + bar_width, bar_y + bar_height), (100, 100, 100), -1)
            
            # Value bar
            normalized_value = (knob_value + 135) / 270
            value_width = int(normalized_value * bar_width)
            if knob_value != 0:
                cv2.rectangle(frame, (bar_x, bar_y), 
                             (bar_x + value_width, bar_y + bar_height), color, -1)
            
            # Center line
            center_x = bar_x + bar_width // 2
            cv2.line(frame, (center_x, bar_y), (center_x, bar_y + bar_height), 
                    (255, 255, 255), 1)
            
            # Highlight active knob
            if self.active_knob == knob_name:
                cv2.rectangle(frame, (interface_x - 5, y_pos - 12), 
                             (interface_x + 330, y_pos + 8), (255, 255, 255), 2)
            
            y_pos += 25
    
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
                    self.knobs = {'filter': 0.0, 'low': 0.0, 'mid': 0.0, 'high': 0.0}
                    self.stream_previous_final_angle = {'filter': 0.0, 'low': 0.0, 'mid': 0.0, 'high': 0.0}
                    self.previous_angle = None
                    self.active_knob = None
                    self.knob_locked = False
                    self.gesture_active = False
                    print("All knobs reset to 0")
                elif key == ord('t'):
                    # Send MIDI test sequence
                    if self.midi_device:
                        print("Sending MIDI test sequence...")
                        self.midi_device.send_test_sequence()
                    else:
                        print("MIDI device not available")
        
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
