import cv2
import mediapipe as mp
import numpy as np
import time

class HandDetector:
    def __init__(self):
        # Initialize MediaPipe hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Key landmarks to display (thumb tip, index tip, middle tip, ring tip, pinky tip, wrist)
        self.key_landmarks = [4, 8, 12, 16, 20, 0]
        self.landmark_names = ["Thumb Tip", "Index Tip", "Middle Tip", "Ring Tip", "Pinky Tip", "Wrist"]
        
        # Performance tracking
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.fps = 0
    
    def process_frame(self, frame):
        """Process a single frame and return annotated frame with landmarks"""
        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the frame
        results = self.hands.process(rgb_frame)
        
        # Draw landmarks and get coordinates
        landmark_data = []
        
        if results.multi_hand_landmarks:
            for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                # Draw hand landmarks
                self.mp_draw.draw_landmarks(
                    frame, 
                    hand_landmarks, 
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing_styles.get_default_hand_landmarks_style(),
                    self.mp_drawing_styles.get_default_hand_connections_style()
                )
                
                # Extract key landmark coordinates
                h, w, _ = frame.shape
                hand_data = []
                
                for i, landmark_idx in enumerate(self.key_landmarks):
                    landmark = hand_landmarks.landmark[landmark_idx]
                    x = int(landmark.x * w)
                    y = int(landmark.y * h)
                    z = landmark.z
                    
                    hand_data.append({
                        'name': self.landmark_names[i],
                        'x': x,
                        'y': y,
                        'z': z,
                        'normalized_x': landmark.x,
                        'normalized_y': landmark.y
                    })
                    
                    # Draw landmark index on frame
                    cv2.circle(frame, (x, y), 8, (255, 0, 0), -1)
                    cv2.putText(frame, str(landmark_idx), (x + 10, y - 10), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                landmark_data.append({
                    'hand_index': hand_idx,
                    'landmarks': hand_data
                })
        
        return frame, landmark_data
    
    def draw_landmark_info(self, frame, landmark_data):
        """Draw landmark information on the frame"""
        y_offset = 30
        
        # Draw FPS
        cv2.putText(frame, f"FPS: {self.fps:.1f}", (10, y_offset), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        y_offset += 30
        
        # Draw landmark data
        for hand_data in landmark_data:
            hand_idx = hand_data['hand_index']
            cv2.putText(frame, f"Hand {hand_idx + 1}:", (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            y_offset += 25
            
            for landmark in hand_data['landmarks']:
                text = f"{landmark['name']}: ({landmark['x']}, {landmark['y']}, {landmark['z']:.3f})"
                cv2.putText(frame, text, (10, y_offset), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                y_offset += 20
            
            y_offset += 10  # Extra space between hands
        
        return frame
    
    def update_fps(self):
        """Update FPS calculation"""
        self.fps_counter += 1
        current_time = time.time()
        
        if current_time - self.fps_start_time >= 1.0:
            self.fps = self.fps_counter / (current_time - self.fps_start_time)
            self.fps_counter = 0
            self.fps_start_time = current_time
    
    def run(self):
        """Main loop for hand detection"""
        # Initialize camera
        cap = cv2.VideoCapture(0)
        
        # Optimize camera settings for performance
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 60)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer to minimize lag
        
        if not cap.isOpened():
            print("Error: Could not open camera")
            return
        
        print("Hand Detection Started! Press 'q' to quit.")
        print("Key landmarks being tracked:")
        for i, name in enumerate(self.landmark_names):
            print(f"  {self.key_landmarks[i]}: {name}")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Could not read frame")
                break
            
            # Flip frame horizontally for mirror effect
            frame = cv2.flip(frame, 1)
            
            # Process frame
            annotated_frame, landmark_data = self.process_frame(frame)
            
            # Add landmark information to frame
            final_frame = self.draw_landmark_info(annotated_frame, landmark_data)
            
            # Update FPS
            self.update_fps()
            
            # Print landmark data to console (optional, can be commented out for better performance)
            if landmark_data:
                print(f"\nFrame - FPS: {self.fps:.1f}")
                for hand_data in landmark_data:
                    print(f"Hand {hand_data['hand_index'] + 1}:")
                    for landmark in hand_data['landmarks']:
                        print(f"  {landmark['name']}: x={landmark['x']}, y={landmark['y']}, z={landmark['z']:.3f}")
            
            # Display frame
            cv2.imshow('Hand Landmark Detection', final_frame)
            
            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # Cleanup
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    detector = HandDetector()
    detector.run()

