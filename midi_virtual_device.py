#!/usr/bin/env python3
"""
Virtual MIDI Device for Hand Gesture DJ Control
Translates hand gesture outputs to MIDI messages for Mixxx DJ software
"""

import time
import threading
import sys
import traceback
from typing import Dict, Optional, Tuple
import mido
from mido import MidiFile, MidiTrack, Message
import rtmidi

class VirtualMIDIDevice:
    """Virtual MIDI device that converts gesture data to MIDI messages"""
    
    def __init__(self, device_name: str = "AI_DJ_Gestures"):
        self.device_name = device_name
        self.midi_out = None
        self.running = False
        
        # MIDI Configuration for Mixxx
        self.midi_config = {
            # EQ Controls (using CC messages on channel 1)
            'filter': {'channel': 0, 'cc': 1, 'min_value': 0, 'max_value': 127},    # High/Low pass filter
            'low': {'channel': 0, 'cc': 2, 'min_value': 0, 'max_value': 127},       # Low EQ
            'mid': {'channel': 0, 'cc': 3, 'min_value': 0, 'max_value': 127},       # Mid EQ  
            'high': {'channel': 0, 'cc': 4, 'min_value': 0, 'max_value': 127},      # High EQ
        }
        
        # Last sent values to avoid duplicate messages
        self.last_sent_values = {
            'filter': None,
            'low': None,
            'mid': None,
            'high': None
        }
        
        # Value smoothing
        self.smoothing_factor = 0.8  # 0.0 = no smoothing, 1.0 = max smoothing
        self.smoothed_values = {
            'filter': 0.0,
            'low': 0.0,
            'mid': 0.0,
            'high': 0.0
        }
        
        self.init_midi()
    
    def init_midi(self):
        """Initialize MIDI output device"""
        try:
            self.midi_out = rtmidi.MidiOut()
            
            # Create virtual port
            self.midi_out.open_virtual_port(self.device_name)
            print(f"✓ Virtual MIDI device '{self.device_name}' created successfully")
            print(f"  Available for connection in Mixxx MIDI preferences")
            
            # Send initialization message
            self.send_control_change(0, 0, 64)  # Initialize with center values
            time.sleep(0.1)
            
            return True
            
        except Exception as e:
            print(f"✗ Failed to create MIDI device: {e}")
            print("  Make sure you have python-rtmidi installed:")
            print("  pip install python-rtmidi")
            return False
    
    def close(self):
        """Close MIDI device"""
        self.running = False
        if self.midi_out:
            self.midi_out.close_port()
            print(f"✓ MIDI device '{self.device_name}' closed")
    
    def send_control_change(self, channel: int, cc_number: int, value: int):
        """Send a MIDI Control Change message"""
        if not self.midi_out:
            return False
            
        try:
            # Clamp value to MIDI range
            value = max(0, min(127, int(value)))
            
            # Create and send CC message
            msg = [0xB0 | channel, cc_number, value]  # Control Change on channel
            self.midi_out.send_message(msg)
            return True
            
        except Exception as e:
            print(f"✗ Error sending MIDI message: {e}")
            return False
    
    def gesture_angle_to_midi(self, angle_value: float) -> int:
        """
        Convert gesture angle (-135 to +135 degrees) to MIDI value (0-127)
        
        Args:
            angle_value: Angle in degrees from -135 to +135
            
        Returns:
            MIDI value from 0 to 127
        """
        # Normalize from [-135, +135] to [0, 1]
        normalized = (angle_value + 135.0) / 270.0
        
        # Clamp to valid range
        normalized = max(0.0, min(1.0, normalized))
        
        # Convert to MIDI range
        midi_value = int(normalized * 127)
        
        return midi_value
    
    def apply_smoothing(self, control_name: str, new_value: float) -> float:
        """Apply smoothing to reduce jitter"""
        if control_name not in self.smoothed_values:
            self.smoothed_values[control_name] = new_value
            return new_value
        
        # Exponential smoothing
        old_value = self.smoothed_values[control_name]
        smoothed = (self.smoothing_factor * old_value) + ((1 - self.smoothing_factor) * new_value)
        self.smoothed_values[control_name] = smoothed
        
        return smoothed
    
    def update_control(self, control_name: str, angle_value: float, force_send: bool = False):
        """
        Update a specific control with gesture data
        
        Args:
            control_name: 'filter', 'low', 'mid', or 'high'
            angle_value: Angle value from -135 to +135 degrees
            force_send: Send even if value hasn't changed significantly
        """
        if control_name not in self.midi_config:
            return False
        
        # Apply smoothing
        smoothed_angle = self.apply_smoothing(control_name, angle_value)
        
        # Convert to MIDI value
        midi_value = self.gesture_angle_to_midi(smoothed_angle)
        
        # Check if we need to send (avoid spam)
        last_value = self.last_sent_values[control_name]
        if not force_send and last_value is not None:
            # Only send if value changed by at least 2 (reduces MIDI spam)
            if abs(midi_value - last_value) < 2:
                return False
        
        # Get MIDI configuration
        config = self.midi_config[control_name]
        channel = config['channel']
        cc_number = config['cc']
        
        # Send MIDI message
        success = self.send_control_change(channel, cc_number, midi_value)
        
        if success:
            self.last_sent_values[control_name] = midi_value
            return True
        
        return False
    
    def update_all_controls(self, knob_values: Dict[str, float], active_knob: Optional[str] = None):
        """
        Update all controls from gesture data
        
        Args:
            knob_values: Dictionary with 'filter', 'low', 'mid', 'high' angle values
            active_knob: Currently active knob name (for priority sending)
        """
        if not self.midi_out:
            return
        
        sent_count = 0
        
        # Send active knob first (priority)
        if active_knob and active_knob in knob_values:
            if self.update_control(active_knob, knob_values[active_knob]):
                sent_count += 1
        
        # Send other controls
        for control_name, angle_value in knob_values.items():
            if control_name != active_knob:  # Skip active knob (already sent)
                if self.update_control(control_name, angle_value):
                    sent_count += 1
        
        return sent_count
    
    def send_test_sequence(self):
        """Send a test sequence to verify MIDI connection"""
        print("Sending test MIDI sequence...")
        
        test_controls = ['filter', 'low', 'mid', 'high']
        
        for control in test_controls:
            print(f"Testing {control}...")
            
            # Send min value
            self.update_control(control, -135.0, force_send=True)
            time.sleep(0.5)
            
            # Send center value  
            self.update_control(control, 0.0, force_send=True)
            time.sleep(0.5)
            
            # Send max value
            self.update_control(control, 135.0, force_send=True)
            time.sleep(0.5)
            
            # Return to center
            self.update_control(control, 0.0, force_send=True)
            time.sleep(0.5)
        
        print("Test sequence complete!")
    
    def print_midi_mapping_info(self):
        """Print MIDI mapping information for Mixxx configuration"""
        print("\n" + "="*60)
        print("MIDI MAPPING INFORMATION FOR MIXXX")
        print("="*60)
        print(f"Device Name: {self.device_name}")
        print(f"MIDI Channel: 1 (Channel 0 in code)")
        print("\nControl Mapping:")
        print("┌─────────────┬────────────┬─────────────┬──────────────┐")
        print("│ Control     │ Fingers    │ CC Number   │ Range        │")
        print("├─────────────┼────────────┼─────────────┼──────────────┤")
        
        control_names = {
            'filter': 'Hi/Lo Filter',
            'low': 'Low EQ',
            'mid': 'Mid EQ', 
            'high': 'High EQ'
        }
        
        finger_counts = {
            'filter': '1 finger',
            'low': '2 fingers',
            'mid': '3 fingers',
            'high': '4 fingers'
        }
        
        for control, config in self.midi_config.items():
            control_display = control_names[control]
            fingers = finger_counts[control]
            cc_num = config['cc']
            range_display = f"{config['min_value']}-{config['max_value']}"
            
            print(f"│ {control_display:<11} │ {fingers:<10} │ {cc_num:<11} │ {range_display:<12} │")
        
        print("└─────────────┴────────────┴─────────────┴──────────────┘")
        print("\nMIDI Message Format:")
        print("  Status: 0xB0 (Control Change, Channel 1)")
        print("  Data 1: CC Number (1-4)")
        print("  Data 2: Value (0-127)")
        print("\nGesture Angle Mapping:")
        print("  -135° → MIDI 0   (Full Counter-Clockwise)")
        print("     0° → MIDI 64  (Center)")
        print("  +135° → MIDI 127 (Full Clockwise)")
        print("="*60)

def main():
    """Test the virtual MIDI device"""
    print("Virtual MIDI Device for AI DJ Gestures")
    print("======================================")
    
    # Create MIDI device
    midi_device = VirtualMIDIDevice()
    
    if not midi_device.midi_out:
        print("Failed to initialize MIDI device")
        return
    
    # Print mapping information
    midi_device.print_midi_mapping_info()
    
    try:
        print("\nMIDI device is running...")
        print("Commands:")
        print("  't' - Send test sequence")
        print("  'q' - Quit")
        print("  'i' - Show MIDI info again")
        
        while True:
            user_input = input("\nEnter command: ").strip().lower()
            
            if user_input == 'q':
                break
            elif user_input == 't':
                midi_device.send_test_sequence()
            elif user_input == 'i':
                midi_device.print_midi_mapping_info()
            elif user_input == '':
                continue
            else:
                print("Unknown command. Use 't' for test, 'i' for info, 'q' to quit.")
    
    except KeyboardInterrupt:
        print("\nShutting down...")
    
    finally:
        midi_device.close()

if __name__ == "__main__":
    main()
