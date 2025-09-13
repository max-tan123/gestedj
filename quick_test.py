#!/usr/bin/env python3
"""
Quick test script to verify the AI DJ system components
"""

import sys
import time

def test_imports():
    """Test all required imports"""
    print("Testing imports...")
    
    try:
        import cv2
        print("✓ OpenCV available")
    except ImportError:
        print("✗ OpenCV not found")
        return False
    
    try:
        import mediapipe as mp
        print("✓ MediaPipe available")
    except ImportError:
        print("✗ MediaPipe not found")
        return False
    
    try:
        import numpy as np
        print("✓ NumPy available")
    except ImportError:
        print("✗ NumPy not found")
        return False
    
    try:
        import rtmidi
        print("✓ python-rtmidi available")
    except ImportError:
        print("✗ python-rtmidi not found")
        return False
    
    try:
        import mido
        print("✓ mido available")
    except ImportError:
        print("✗ mido not found")
        return False
    
    return True

def test_camera():
    """Test camera access"""
    print("\nTesting camera access...")
    
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("✗ Camera not accessible")
            return False
        
        ret, frame = cap.read()
        if ret:
            height, width = frame.shape[:2]
            print(f"✓ Camera working - Resolution: {width}x{height}")
            success = True
        else:
            print("✗ Cannot read from camera")
            success = False
        
        cap.release()
        return success
        
    except Exception as e:
        print(f"✗ Camera test failed: {e}")
        return False

def test_midi_device():
    """Test MIDI device creation"""
    print("\nTesting MIDI device...")
    
    try:
        from midi_virtual_device import VirtualMIDIDevice
        
        device = VirtualMIDIDevice("AI_DJ_Test")
        if device.midi_out:
            print("✓ Virtual MIDI device created successfully")
            
            # Send a test message
            device.send_control_change(0, 1, 64)
            print("✓ MIDI message sent successfully")
            
            device.close()
            print("✓ MIDI device closed cleanly")
            return True
        else:
            print("✗ Failed to create MIDI device")
            return False
            
    except Exception as e:
        print(f"✗ MIDI test failed: {e}")
        return False

def test_hand_detection():
    """Test hand detection code import"""
    print("\nTesting hand detection code...")
    
    try:
        from hand_detection_midi import HandDetectorWithMIDI
        print("✓ Hand detection with MIDI code imports successfully")
        return True
    except Exception as e:
        print(f"✗ Hand detection test failed: {e}")
        return False

def test_mixxx_mapping():
    """Test Mixxx mapping file"""
    print("\nTesting Mixxx mapping file...")
    
    try:
        import os
        mapping_file = "AI_DJ_Gestures.mixxx.xml"
        
        if os.path.exists(mapping_file):
            print("✓ Mixxx mapping file exists")
            
            # Check if it's valid XML
            import xml.etree.ElementTree as ET
            tree = ET.parse(mapping_file)
            root = tree.getroot()
            
            if root.tag == "MixxxControllerPreset":
                print("✓ Mixxx mapping file is valid XML")
                return True
            else:
                print("✗ Invalid Mixxx mapping format")
                return False
        else:
            print("✗ Mixxx mapping file not found")
            return False
            
    except Exception as e:
        print(f"✗ Mixxx mapping test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("AI DJ System Component Test")
    print("=" * 40)
    
    tests = [
        ("Imports", test_imports),
        ("Camera", test_camera),
        ("MIDI Device", test_midi_device),
        ("Hand Detection", test_hand_detection),
        ("Mixxx Mapping", test_mixxx_mapping)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name} Test:")
        print("-" * 20)
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 40)
    print("TEST SUMMARY")
    print("=" * 40)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        icon = "✓" if success else "✗"
        print(f"{icon} {test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your AI DJ system is ready to use!")
        print("\nNext steps:")
        print("1. Run: python hand_detection_midi.py")
        print("2. Open Mixxx and enable the AI_DJ_Gestures controller")
        print("3. Load some music and start DJing with gestures!")
    else:
        print(f"\n❌ {total - passed} test(s) failed. Please check the issues above.")
        print("Refer to SETUP_INSTRUCTIONS.md for troubleshooting help.")

if __name__ == "__main__":
    main()
