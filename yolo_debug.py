#!/usr/bin/env python3
"""
Test YOLOv8s detection
"""
import pyrealsense2 as rs
import numpy as np
import cv2
import time
from ultralytics import YOLO

print("Testing YOLOv8s (better accuracy)...\n")

pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
pipeline.start(config)
time.sleep(2)

# Load YOLOv8s
model = YOLO('yolov8s.onnx', task='detect')
print("✓ YOLOv8s loaded\n")

for i in range(10):
    frames = pipeline.poll_for_frames()
    if not frames:
        time.sleep(0.1)
        continue
    
    color_frame = frames.get_color_frame()
    if not color_frame:
        continue
    
    img = np.asanyarray(color_frame.get_data())
    
    # Detect
    results = model(img, verbose=False)
    
    print(f"Frame {i+1}: {len(results[0].boxes)} detections")
    
    for box in results[0].boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        name = model.names[cls_id]
        
        if cls_id == 32:  # Sports ball
            print(f"  ⚽ BALL: {conf:.2%}")
        else:
            print(f"  {name}: {conf:.2%}")
    
    # Save image
    annotated = results[0].plot()
    cv2.imwrite(f'yolov8s_test_{i}.jpg', annotated)
    
    time.sleep(0.5)

pipeline.stop()
print("\n✓ Check yolov8s_test_*.jpg images")