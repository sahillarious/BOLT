#!/usr/bin/env python3
"""
Simple posing script: Updates velocities.txt with pose commands for file_control.py
Usage: python3 pose_control.py <pose>  (e.g., 'stand', 'sit', 'point')
"""
import sys
import os

BASE = os.path.dirname(os.path.abspath(__file__))
VEL_FILE = os.path.join(BASE, 'velocities.txt')

if len(sys.argv) < 2:
    print("Usage: python3 pose_control.py <pose>  (e.g., 'stand', 'sit', 'point')")
    sys.exit(1)

pose = sys.argv[1].lower()
valid_poses = ['stand', 'sit', 'point']

if pose not in valid_poses:
    print(f"Invalid pose. Valid options: {valid_poses}")
    sys.exit(1)

# Write pose command to the file
with open(VEL_FILE, 'w') as f:
    f.write(pose)

print(f"Posed robot to: {pose}")