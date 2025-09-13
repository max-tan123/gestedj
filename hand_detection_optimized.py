import cv2
import mediapipe as mp
import numpy as np
import time
import math
from collections import deque

class OptimizedHandDetector:
    def __init__(self):
        # Initialize MediaPipe hands with optimized settings
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.8,  # Higher confidence for better performance
            min_tracking_confidence=0.7,   # Higher tracking confidence
            model_complexity=0  # Use lighter model for better performance
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # All 21 hand landmarks
        self.key_landmarks = list(range(21))  # All landmarks 0-20
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
        
        # Performance tracking with moving average
        self.fps_history = deque(maxlen=30)
        self.frame_times = deque(maxlen=5)
        
        # Display options
        self.show_console_output = False  # Set to True to enable console printing
        self.show_all_landmarks = False   # Set to True to show all 21 landmarks
        
        # DJ Control System
        self.knobs = {
            'filter': 0.0,    # 1 finger - high/low pass filter
            'low': 0.0,       # 2 fingers - low frequency
            'mid': 0.0,       # 3 fingers - mid frequency
            'high': 0.0       # 4 fingers - high frequency
        }
        self.knob_names = ['filter', 'low', 'mid', 'high']
        
        # Tracking variables for continuous control - FIXED STREAM LOGIC
        self.stream_initial_angle = None  # Initial angle when stream starts
        self.stream_previous_final_angle = {  # Final angle from previous streams
            'filter': 0.0, 'low': 0.0, 'mid': 0.0, 'high': 0.0
        }
        # Simple tracking - just remember previous angle
        self.previous_angle = None  # Previous frame's angle for delta calculation
        self.current_finger_count = 0
        self.previous_finger_count = 0
        self.active_knob = None
        self.previous_active_knob = None
        self.knob_locked = False
        self.gesture_active = False
        
        # Edge case handling
        self.hand_detected = False
        self.stable_detection_count = 0
        self.min_stable_frames = 1  # Require stable detection for 1 frame (immediate response)
        
        # Finger detection threshold (for counting fingers up)
        self.finger_tip_indices = [4, 8, 12, 16, 20]  # Thumb, Index, Middle, Ring, Pinky tips
        self.finger_pip_indices = [3, 6, 10, 14, 18]  # PIP joints for comparison
        
    def process_frame(self, frame):
        """Process frame with optimizations"""
        start_time = time.time()
        
        # Resize frame for faster processing (optional)
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
                # Draw landmarks with minimal style for performance
                if self.show_all_landmarks:
                    self.mp_draw.draw_landmarks(
                        frame, 
                        hand_landmarks, 
                        self.mp_hands.HAND_CONNECTIONS
                    )
                
                # Extract key landmarks only
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
                    
                    # Draw landmarks with color coding by finger
                    # Wrist: Yellow, Thumb: Red, Index: Green, Middle: Blue, Ring: Magenta, Pinky: Cyan
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
                    # Show landmark number for clarity
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
        """SIMPLE finger counting with DEBUG OUTPUT"""
        try:
            fingers_up = 0
            debug_info = []
            
            # Simple check: tip above PIP joint (basic but reliable)
            finger_data = [
                ("Index", 8, 6),    # tip, pip
                ("Middle", 12, 10),  # tip, pip
                ("Ring", 16, 14),    # tip, pip
                ("Pinky", 20, 18)    # tip, pip
            ]
            
            for finger_name, tip_idx, pip_idx in finger_data:
                try:
                    tip = landmarks[tip_idx]
                    pip = landmarks[pip_idx]
                    
                    # Check validity
                    if (tip.x < 0 or tip.x > 1 or tip.y < 0 or tip.y > 1 or
                        pip.x < 0 or pip.x > 1 or pip.y < 0 or pip.y > 1):
                        debug_info.append(f"{finger_name}: INVALID")
                        continue
                    
                    # Convert to pixel coordinates for debug
                    tip_x, tip_y = int(tip.x * 1280), int(tip.y * 720)
                    pip_x, pip_y = int(pip.x * 1280), int(pip.y * 720)
                    
                    # Simple check: tip above pip (lower y value = higher on screen)
                    is_up = tip.y < pip.y
                    
                    if is_up:
                        fingers_up += 1
                        debug_info.append(f"{finger_name}: UP tip({tip_x},{tip_y}) pip({pip_x},{pip_y})")
                    else:
                        debug_info.append(f"{finger_name}: DOWN tip({tip_x},{tip_y}) pip({pip_x},{pip_y})")
                        
                except (IndexError, AttributeError):
                    debug_info.append(f"{finger_name}: ERROR")
                    continue
            
            # Store debug info for display
            self.finger_debug_info = debug_info
            self.finger_debug_count = fingers_up
            
            return max(0, min(4, fingers_up))
            
        except Exception as e:
            self.finger_debug_info = [f"COUNT ERROR: {e}"]
            self.finger_debug_count = 0
            return 0
    
    def is_finger_extended(self, vectors, joint_positions):
        """Determine if finger is extended - PERMISSIVE VERSION"""
        try:
            mcp_pos = joint_positions[0]  # Base of finger
            tip_pos = joint_positions[-1]  # Tip of finger
            
            # Overall vector from base to tip
            overall_vector = (tip_pos[0] - mcp_pos[0], tip_pos[1] - mcp_pos[1])
            overall_length = (overall_vector[0]**2 + overall_vector[1]**2)**0.5
            
            if overall_length < 0.04:  # Too short, probably curled or invalid
                return False
            
            # KEY INSIGHT: Don't care about "upward" direction, care about CONSISTENCY
            # A finger pointing down/sideways is still extended if joints are aligned
            
            # Check vector consistency - are the joint-to-joint vectors going in similar directions?
            consistency_score = 0
            total_comparisons = 0
            
            for i in range(len(vectors) - 1):
                v1 = vectors[i]
                v2 = vectors[i + 1]
                
                # Calculate lengths
                v1_len = (v1[0]**2 + v1[1]**2)**0.5
                v2_len = (v2[0]**2 + v2[1]**2)**0.5
                
                if v1_len > 0.005 and v2_len > 0.005:  # Valid vector lengths
                    # Dot product to check similarity in direction
                    dot_product = v1[0] * v2[0] + v1[1] * v2[1]
                    cos_angle = dot_product / (v1_len * v2_len)
                    
                    # If vectors point in similar direction (cos > 0), that's good
                    # If they point in opposite directions (cos < -0.3), that's bad (folded finger)
                    if cos_angle > -0.3:  # Not strongly opposing
                        consistency_score += 1
                    total_comparisons += 1
            
            # Check if finger segments have reasonable length (not all bunched up)
            segment_length_ok = True
            for vector in vectors:
                length = (vector[0]**2 + vector[1]**2)**0.5
                if length < 0.01:  # Too short segment
                    segment_length_ok = False
                    break
            
            # PERMISSIVE DECISION: 
            # - Must have reasonable overall length
            # - Most vector pairs should not be strongly opposing (no sharp folds)
            # - Individual segments should have reasonable length
            consistency_ratio = consistency_score / max(1, total_comparisons)
            
            is_extended = (
                overall_length > 0.04 and  # Minimum extension
                consistency_ratio > 0.5 and  # At least half the vectors are consistent
                segment_length_ok  # No collapsed segments
            )
            
            return is_extended
            
        except Exception:
            return False
    
    def calculate_pointer_angle(self, landmarks):
        """Calculate angle between wrist and pointer finger tip - ROBUST VERSION"""
        try:
            wrist = landmarks[0]  # Wrist landmark
            pointer_tip = landmarks[8]  # Index finger tip
            
            # Validate landmarks
            if (wrist.x < 0 or wrist.x > 1 or wrist.y < 0 or wrist.y > 1 or
                pointer_tip.x < 0 or pointer_tip.x > 1 or pointer_tip.y < 0 or pointer_tip.y > 1):
                return 0.0
            
            # Calculate differences
            dx = pointer_tip.x - wrist.x
            dy = pointer_tip.y - wrist.y
            
            # Check if the distance is reasonable (not too close)
            distance = (dx**2 + dy**2)**0.5
            if distance < 0.01:  # Too close, probably invalid detection
                return 0.0
            
            # Calculate angle in degrees
            angle = math.degrees(math.atan2(dy, dx))
            
            # Normalize to -180 to +180 range
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
        """Update DJ knob values - FIXED STREAM LOGIC: prev_final + (curr - initial)"""
        try:
            # Validate landmarks
            if not landmarks or len(landmarks) < 21:
                self.handle_detection_loss()
                return 0.0
            
            # Check if required landmarks are present and valid
            required_landmarks = [0, 6, 8]  # Wrist, Index PIP, Index Tip
            for idx in required_landmarks:
                if landmarks[idx].x < 0 or landmarks[idx].x > 1 or landmarks[idx].y < 0 or landmarks[idx].y > 1:
                    self.handle_detection_loss()
                    return 0.0
            
            finger_count = self.count_fingers(landmarks)
            current_angle = self.calculate_pointer_angle(landmarks)
            
            # Store previous states
            self.previous_finger_count = self.current_finger_count
            self.previous_active_knob = self.active_knob
            self.current_finger_count = finger_count
            
            # Determine which knob should be active
            target_knob = None
            if finger_count == 1:
                target_knob = 'filter'
            elif finger_count == 2:
                target_knob = 'low'
            elif finger_count == 3:
                target_knob = 'mid'
            elif finger_count == 4:
                target_knob = 'high'
            
            # Check if pointer finger is up using vector analysis
            pointer_up = self.is_pointer_finger_up(landmarks)
            
            # Stable detection counter
            if pointer_up and target_knob:
                self.stable_detection_count += 1
            else:
                self.stable_detection_count = 0
            
            # SIMPLE LOGIC: Only proceed if we have target knob and pointer up
            if target_knob and pointer_up and not self.knob_locked:
                
                # Case 1: Starting new gesture or switching knobs
                if self.active_knob != target_knob or not self.gesture_active:
                    # Save previous knob value
                    if self.active_knob:
                        self.stream_previous_final_angle[self.active_knob] = self.knobs[self.active_knob]
                    
                    # Start new gesture
                    self.active_knob = target_knob
                    self.gesture_active = True
                    self.previous_angle = current_angle  # Set previous angle for delta calc
                    
                    if self.show_console_output:
                        print(f"Started {target_knob} control at angle {current_angle:.1f}°")
                
                # Case 2: Continue current gesture - SIMPLE DELTA
                elif self.active_knob == target_knob and self.gesture_active and self.previous_angle is not None:
                    # Calculate delta from PREVIOUS frame (not initial)
                    delta_angle = current_angle - self.previous_angle
                    
                    # Handle angle wraparound
                    if delta_angle > 180:
                        delta_angle -= 360
                    elif delta_angle < -180:
                        delta_angle += 360
                    
                    # Scale delta
                    scaled_delta = (135.0 / 50.0) * delta_angle
                    
                    # Add to current knob value
                    new_value = self.knobs[target_knob] + scaled_delta
                    
                    # Simple clamp - no complex tracking
                    self.knobs[target_knob] = max(-135.0, min(135.0, new_value))
                    
                    # Update previous angle for next frame
                    self.previous_angle = current_angle
            
            # Case 3: Pointer finger goes down - END CURRENT STREAM
            elif not pointer_up and self.gesture_active:
                if self.active_knob:
                    # Save the final value from this stream
                    self.stream_previous_final_angle[self.active_knob] = self.knobs[self.active_knob]
                    if self.show_console_output:
                        print(f"Stream ended - {self.active_knob} locked at {self.knobs[self.active_knob]:.1f}")
                
                # Reset stream state
                self.gesture_active = False
                self.knob_locked = True
                self.previous_angle = None
            
            # Case 4: No valid gesture - reset stream state but keep values
            elif target_knob is None:
                if self.gesture_active and self.active_knob:
                    # Save current stream value before resetting
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
        """Simple check if pointer finger is up"""
        try:
            wrist = landmarks[0]
            index_tip = landmarks[8]
            index_mcp = landmarks[5]
            
            # Check if landmarks are valid
            if (wrist.x < 0 or wrist.x > 1 or wrist.y < 0 or wrist.y > 1 or
                index_tip.x < 0 or index_tip.x > 1 or index_tip.y < 0 or index_tip.y > 1 or
                index_mcp.x < 0 or index_mcp.x > 1 or index_mcp.y < 0 or index_mcp.y > 1):
                return False
            
            # Simple distance check: is tip far enough from wrist?
            tip_to_wrist = ((index_tip.x - wrist.x)**2 + (index_tip.y - wrist.y)**2)**0.5
            mcp_to_wrist = ((index_mcp.x - wrist.x)**2 + (index_mcp.y - wrist.y)**2)**0.5
            
            return tip_to_wrist > mcp_to_wrist * 1.15  # Tip is 15% further from wrist
            
        except Exception:
            return False
    
    def handle_detection_loss(self):
        """Handle cases where hand detection is lost or unstable"""
        self.hand_detected = False
        self.stable_detection_count = 0
        # Save current stream value before losing detection
        if self.gesture_active and self.active_knob:
            self.stream_previous_final_angle[self.active_knob] = self.knobs[self.active_knob]
        # Reset stream state but keep final values
        self.gesture_active = False
        self.previous_angle = None
    
    def draw_dj_interface(self, frame):
        """Draw DJ control interface on the frame"""
        height, width = frame.shape[:2]
        
        # DJ Interface positioned on the right side
        interface_x = width - 300
        interface_y = 30
        
        # Background for DJ interface
        cv2.rectangle(frame, (interface_x - 10, interface_y - 10), 
                     (width - 10, interface_y + 200), (40, 40, 40), -1)
        cv2.rectangle(frame, (interface_x - 10, interface_y - 10), 
                     (width - 10, interface_y + 200), (255, 255, 255), 2)
        
        # Title
        cv2.putText(frame, "DJ CONTROL", (interface_x, interface_y + 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Finger count and active knob
        y_pos = interface_y + 40
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
        
        y_pos += 20
        status_text = f"Locked: {'Yes' if self.knob_locked else 'No'}"
        cv2.putText(frame, status_text, (interface_x, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 100, 100), 1)
        
        # Show current pointer angle if available
        if hasattr(self, 'current_pointer_angle'):
            y_pos += 20
            angle_text = f"Angle: {self.current_pointer_angle:.1f}°"
            cv2.putText(frame, angle_text, (interface_x, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        y_pos += 20
        stable_text = f"Stable: {self.stable_detection_count}/{self.min_stable_frames}"
        cv2.putText(frame, stable_text, (interface_x, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Show previous angle for debugging
        if hasattr(self, 'previous_angle') and self.previous_angle is not None:
            y_pos += 20
            prev_text = f"Prev Angle: {self.previous_angle:.1f}°"
            cv2.putText(frame, prev_text, (interface_x, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # DEBUG: Show finger detection info
        if hasattr(self, 'finger_debug_info'):
            y_pos += 30
            cv2.putText(frame, f"DEBUG FINGERS ({self.finger_debug_count}):", (interface_x, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
            y_pos += 15
            for i, debug_line in enumerate(self.finger_debug_info):
                if i < 4:  # Only show first 4 lines
                    cv2.putText(frame, debug_line, (interface_x, y_pos), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
                    y_pos += 12
        
        # Draw knobs
        y_pos += 30
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
        
        for i, knob_name in enumerate(self.knob_names):
            knob_value = self.knobs[knob_name]
            color = knob_colors[knob_name]
            
            # Knob label and finger mapping
            label = f"{finger_mapping[knob_name]} {knob_name.upper()}"
            cv2.putText(frame, label, (interface_x, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            # Knob value
            value_text = f"{knob_value:+6.1f}°"
            cv2.putText(frame, value_text, (interface_x + 80, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            
            # Knob visualization bar
            bar_x = interface_x + 150
            bar_y = y_pos - 8
            bar_width = 100
            bar_height = 10
            
            # Background bar
            cv2.rectangle(frame, (bar_x, bar_y), 
                         (bar_x + bar_width, bar_y + bar_height), (100, 100, 100), -1)
            
            # Value bar (normalize -135 to +135 to 0 to bar_width)
            normalized_value = (knob_value + 135) / 270  # 0 to 1
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
                             (interface_x + 250, y_pos + 8), (255, 255, 255), 2)
            
            y_pos += 25
    
    def draw_optimized_info(self, frame, landmark_data):
        """Draw minimal information overlay for maximum performance"""
        # Calculate average FPS
        if self.frame_times:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
            self.fps_history.append(fps)
            avg_fps = sum(self.fps_history) / len(self.fps_history)
        else:
            avg_fps = 0
        
        # Draw FPS and processing info
        cv2.putText(frame, f"FPS: {avg_fps:.1f}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        if self.frame_times:
            cv2.putText(frame, f"Process: {avg_frame_time*1000:.1f}ms", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Draw hand count
        cv2.putText(frame, f"Hands: {len(landmark_data)}", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Draw DJ Control Interface
        self.draw_dj_interface(frame)
        
        # Draw compact landmark info only if enabled (moved to bottom left)
        if self.show_all_landmarks:
            height, width = frame.shape[:2]
            y_start = height - 150
            for hand_data in landmark_data:
                hand_idx = hand_data['hand_index']
                cv2.putText(frame, f"H{hand_idx + 1}:", (10, y_start), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
                
                # Show only key landmarks to save space
                key_indices = [0, 4, 8, 12, 16, 20]  # Wrist and fingertips
                y_pos = y_start + 15
                
                for i in key_indices:
                    if i < len(hand_data['landmarks']):
                        landmark = hand_data['landmarks'][i]
                        
                        # Color code by finger group
                        if i == 0:  # Wrist
                            color = (0, 255, 255)
                        elif i == 4:  # Thumb
                            color = (0, 0, 255)
                        elif i == 8:  # Index
                            color = (0, 255, 0)
                        elif i == 12:  # Middle
                            color = (255, 0, 0)
                        elif i == 16:  # Ring
                            color = (255, 0, 255)
                        else:  # Pinky
                            color = (255, 255, 0)
                        
                        text = f"{i}:{landmark['name'][:4]}({landmark['x']},{landmark['y']})"
                        cv2.putText(frame, text, (10, y_pos), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1)
                        y_pos += 15
        
        return frame
    
    def run(self):
        """Optimized main loop"""
        # Initialize camera with optimal settings
        cap = cv2.VideoCapture(0)
        
        # Camera optimization
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)  # Reduced for stability
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Additional optimizations
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)  # Disable autofocus
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Manual exposure
        
        if not cap.isOpened():
            print("Error: Could not open camera")
            return
        
        print("Optimized Hand Detection Started!")
        print("Controls:")
        print("  'q' - Quit")
        print("  'c' - Toggle console output")
        print("  'a' - Toggle landmarks display")
        print("  's' - Save current frame")
        print("  'r' - Reset all knobs to 0")
        print("\nDJ Controls:")
        print("  1 finger up = Filter knob")
        print("  2 fingers up = Low knob") 
        print("  3 fingers up = Mid knob")
        print("  4 fingers up = High knob")
        print("  Close hand to lock current knob value")
        
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            
            frame_count += 1
            
            # Flip for mirror effect
            frame = cv2.flip(frame, 1)
            
            # Process every frame for smooth detection
            annotated_frame, landmark_data = self.process_frame(frame)
            
            # Add overlay information
            final_frame = self.draw_optimized_info(annotated_frame, landmark_data)
            
            # Optional console output
            if self.show_console_output and landmark_data and frame_count % 10 == 0:
                print(f"\nFrame {frame_count}:")
                for hand_data in landmark_data:
                    print(f"Hand {hand_data['hand_index'] + 1}:")
                    # Group landmarks by finger for better readability
                    finger_groups = {
                        'Wrist': [0],
                        'Thumb': [1, 2, 3, 4],
                        'Index': [5, 6, 7, 8],
                        'Middle': [9, 10, 11, 12],
                        'Ring': [13, 14, 15, 16],
                        'Pinky': [17, 18, 19, 20]
                    }
                    
                    for finger_name, indices in finger_groups.items():
                        print(f"  {finger_name}:")
                        for idx in indices:
                            landmark = hand_data['landmarks'][idx]
                            print(f"    {idx:2d}-{landmark['name']}: ({landmark['x']:3d}, {landmark['y']:3d}, {landmark['z']:6.3f})")
            
            # Display
            cv2.imshow('Optimized Hand Detection', final_frame)
            
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
                cv2.imwrite(f'hand_detection_frame_{frame_count}.jpg', final_frame)
                print(f"Saved frame {frame_count}")
            elif key == ord('r'):
                # Reset all knobs and stream values
                self.knobs = {'filter': 0.0, 'low': 0.0, 'mid': 0.0, 'high': 0.0}
                self.stream_previous_final_angle = {'filter': 0.0, 'low': 0.0, 'mid': 0.0, 'high': 0.0}
                self.previous_angle = None
                self.active_knob = None
                self.knob_locked = False
                self.gesture_active = False
                print("All knobs reset to 0")
        
        # Cleanup
        cap.release()
        cv2.destroyAllWindows()
        print("Hand detection stopped.")

if __name__ == "__main__":
    detector = OptimizedHandDetector()
    detector.run()
