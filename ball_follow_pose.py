#!/usr/bin/env python3
"""
Ball tracker with depth - CORRECTED POLLING
Updated to integrate with file_control.py: writes to velocities.txt, sits when close to ball
"""
import pyrealsense2 as rs
import numpy as np
import time
from ultralytics import YOLO

print("="*60)
print("BALL TRACKER WITH DEPTH")
print("="*60)

print("\n1. Initializing RealSense...")
pipeline = rs.pipeline()
config = rs.config()

config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

print("Starting pipeline...")
profile = pipeline.start(config)

depth_sensor = profile.get_device().first_depth_sensor()
depth_scale = depth_sensor.get_depth_scale()
print(f"✓ Depth scale: {depth_scale}")

align = rs.align(rs.stream.color)

# Warmup
print("Warming up (polling mode)...")
for i in range(30):
    frames = pipeline.poll_for_frames()
    if frames and i % 10 == 0:
        print(f"  {i}/30")
    time.sleep(0.033)

print("✓ RealSense ready")

# YOLO
print("\n2. Loading ONNX model...")
model = YOLO('yolov8s.onnx', task='detect')
dummy = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
for _ in range(3):
    _ = model(dummy, classes=[32], verbose=False)
print("✓ Model ready")

cmd_file = '/home/unitree/depth_test/velocities.txt'  # Updated to match file_control.py

with open(cmd_file, 'w') as f:
    f.write('0.0,0.0,0.0')

print("\n" + "="*60)
print("TRACKING ACTIVE")
print("="*60 + "\n")

try:
    loop_count = 0
    last_detection_time = time.time()
    sitting = False  # Flag to track if sitting
    
    while True:
        loop_count += 1
        
        # Poll for frames
        frames = pipeline.poll_for_frames()
        
        if not frames:
            time.sleep(0.01)
            continue
        
        # Align
        aligned = align.process(frames)
        depth_frame = aligned.get_depth_frame()
        color_frame = aligned.get_color_frame()
        
        if not depth_frame or not color_frame:
            continue
        
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())
        
        # Detect
        results = model(color_image, classes=[32], verbose=False)
        
        if len(results[0].boxes) > 0:
            last_detection_time = time.time()
            sitting = False  # Reset sitting flag on detection
            
            # Get detection
            box = results[0].boxes[0]
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)
            
            # Depth calculation
            region = depth_image[max(0, center_y-5):min(depth_image.shape[0], center_y+5),
                                 max(0, center_x-5):min(depth_image.shape[1], center_x+5)]
            valid_depths = region[(region > 0) & (region < 10)]
            if len(valid_depths) > 0:
                depth = np.median(valid_depths) * depth_scale
                
                if depth < 0.5:  # Close to ball: sit down
                    with open(cmd_file, 'w') as f:
                        f.write('sit')
                    sitting = True
                    print("Ball close - sitting down")
                    time.sleep(0.01)  # Brief pause after sitting
                    continue  # Skip velocity calculation
                
                # Velocity calculation
                error_x = center_x - 320  # Horizontal error
                vyaw = -error_x * 0.005  # Turn speed
                
                if depth > 1.0:
                    vx = 0.2  # Approach
                elif depth < 0.3:
                    vx = -0.1  # Back up
                else:
                    vx = 0.0
                
                vy = 0.0
                
                with open(cmd_file, 'w') as f:
                    f.write(f'{vx:.3f},{vy:.3f},{vyaw:.3f}')
            else:
                # No valid depth: search
                with open(cmd_file, 'w') as f:
                    f.write('0.000,0.000,0.100')  # Slow turn
        else:
            # No detection: search or sit if previously sitting
            if sitting:
                with open(cmd_file, 'w') as f:
                    f.write('sit')  # Maintain sit if close before
            else:
                with open(cmd_file, 'w') as f:
                    f.write('0.000,0.000,0.100')  # Slow turn
        
        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    with open(cmd_file, 'w') as f:
        f.write('0.0,0.0,0.0')
    pipeline.stop()
    print("Stopped")