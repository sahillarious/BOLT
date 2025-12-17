#!/usr/bin/env python3
"""
Ball tracker with depth - CORRECTED POLLING
Prints 'ball found' when entering holding mode
"""
import pyrealsense2 as rs
import numpy as np
import time
import os
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

cmd_file = '/home/unitree/depth_test/velocities.txt'
with open(cmd_file, 'w') as f:
    f.write('0.0,0.0,0.0')

print("\n" + "="*60)
print("TRACKING ACTIVE")
print("="*60 + "\n")

try:
    loop_count = 0
    last_detection_time = time.time()
    ball_found = False  # Flag for ball found
    
    while True:
        loop_count += 1
        
        # Poll for frames
        frames = pipeline.poll_for_frames()
        
        if not frames:
            print("No frames")  # Debug print
            time.sleep(0.01)
            continue
        
        # Align
        aligned = align.process(frames)
        depth_frame = aligned.get_depth_frame()
        color_frame = aligned.get_color_frame()
        
        if not depth_frame or not color_frame:
            print("No depth/color frame")  # Debug print
            continue
        
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())
        
        # Detect
        results = model(color_image, classes=[32], verbose=False)
        
        if len(results[0].boxes) > 0:
            last_detection_time = time.time()
            
            box = results[0].boxes[0]
            conf = float(box.conf.cpu().numpy()[0])
            xyxy = box.xyxy.cpu().numpy()[0]
            
            x_center = int((xyxy[0] + xyxy[2]) / 2)
            y_center = int((xyxy[1] + xyxy[3]) / 2)
            x_center = max(5, min(634, x_center))
            y_center = max(5, min(474, y_center))
            
            # Depth
            x1, x2 = x_center - 3, x_center + 4
            y1, y2 = y_center - 3, y_center + 4
            depth_region = depth_image[y1:y2, x1:x2]
            valid_depths = depth_region[depth_region > 0]
            
            if len(valid_depths) < 5:
                continue
            
            distance = np.median(valid_depths) * depth_scale
            
            if distance < 0.1 or distance > 3.0:
                continue
            
            # Control
            error = x_center - 320
            turn_speed = -error / 320.0 * 1.0
            if abs(turn_speed) < 0.08:
                turn_speed = 0.0
            
            target = 0.45
            d_error = distance - target
            
            if distance < 0.15:
                vx, vyaw, status = -0.15, turn_speed * 0.5, "TOO CLOSE"
            elif abs(d_error) < 0.05:
                vx, vyaw, status = 0.0, turn_speed, "HOLDING"
            elif d_error > 0.4:
                vx, vyaw, status = 0.30, turn_speed * 0.7, "APPROACHING"
            elif d_error > 0:
                vx, vyaw, status = 0.30, turn_speed * 0.8, "CREEPING"
            else:
                vx, vyaw, status = -0.12, turn_speed * 0.6, "BACKING"
            
            # Print 'ball found' when entering holding
            if status == "HOLDING" and not ball_found:
                print("Ball found")
                ball_found = True
            
            with open(cmd_file, 'w') as f:
                f.write(f'{vx:.3f},0.0,{vyaw:.3f}')
            
            if loop_count % 10 == 0:
                print(f"{status:12s} | dist: {distance:5.2f}m | x={x_center:3d} | "
                      f"vx={vx:+5.2f} vyaw={vyaw:+5.2f}")
        
        else:
            # No detection: search
            ball_found = False  # Reset flag when ball lost
            if time.time() - last_detection_time > 0.5:
                with open(cmd_file, 'w') as f:
                    f.write('0.0,0.0,0.4')
                if loop_count % 10 == 0:
                    print("SEARCHING...")
            else:
                print("Waiting for search")  # Debug print
        
        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    with open(cmd_file, 'w') as f:
        f.write('0.0,0.0,0.0')
    pipeline.stop()
    print("Stopped")