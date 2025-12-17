#!/usr/bin/env python3
"""
Download and export YOLOv8s (better than nano)
"""
from ultralytics import YOLO
import os

print("="*60)
print("DOWNLOADING YOLOv8s (SMALL - BETTER ACCURACY)")
print("="*60)

# Download YOLOv8s
print("\n1. Downloading YOLOv8s.pt...")
model = YOLO('yolov8s.pt')  # Auto-downloads
print(f"✓ Downloaded: {os.path.getsize('yolov8s.pt')/1e6:.1f} MB")

# Export to ONNX
print("\n2. Exporting to ONNX...")
model.export(
    format='onnx',
    simplify=True,
    dynamic=False,
    opset=12,
    imgsz=640
)

print(f"\n✓ Created: yolov8s.onnx")
print(f"💾 Size: {os.path.getsize('yolov8s.onnx')/1e6:.1f} MB")
print("\n✅ Ready to use YOLOv8s!")