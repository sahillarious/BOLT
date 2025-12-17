#!/usr/bin/env python3
"""
Ball tracker with depth - Using custom trained model
Target ball read from target.txt (green, pink, yellow, or all)
Change target anytime: echo "yellow" > target.txt
"""
import pyrealsense2 as rs
import numpy as np
import time
import cv2
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from ultralytics import YOLO

CLASS_NAMES = {0: 'green_ball', 1: 'pink_ball', 2: 'yellow_ball'}
NAME_TO_ID = {'green': 0, 'pink': 1, 'yellow': 2, 'all': None}
COLORS = {0: (0, 255, 0), 1: (255, 0, 255), 2: (0, 255, 255)}

target_file = '/home/unitree/depth_test/target.txt'
cmd_file = '/home/unitree/depth_test/velocities.txt'

# Initialize target file
with open(target_file, 'w') as f:
    f.write('all')

latest_frame = None
frame_lock = threading.Lock()
current_target = 'all'
target_classes = [0, 1, 2]

def read_target():
    global current_target, target_classes
    try:
        with open(target_file, 'r') as f:
            t = f.read().strip().lower()
            if t != current_target and t in NAME_TO_ID:
                current_target = t
                if t == 'all':
                    target_classes = [0, 1, 2]
                else:
                    target_classes = [NAME_TO_ID[t]]
                print(f">>> TARGET CHANGED: {current_target.upper()} <<<")
    except:
        pass

def target_reader():
    while True:
        read_target()
        time.sleep(0.5)

class MJPEGHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
        self.end_headers()
        while True:
            with frame_lock:
                if latest_frame is not None:
                    _, jpeg = cv2.imencode('.jpg', latest_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    self.wfile.write(b'--frame\r\n')
                    self.send_header('Content-type', 'image/jpeg')
                    self.send_header('Content-length', len(jpeg))
                    self.end_headers()
                    self.wfile.write(jpeg.tobytes())
                    self.wfile.write(b'\r\n')
            time.sleep(0.033)
    def log_message(self, format, *args): pass

def start_server():
    server = HTTPServer(('0.0.0.0', 8080), MJPEGHandler)
    server.serve_forever()

threading.Thread(target=start_server, daemon=True).start()
threading.Thread(target=target_reader, daemon=True).start()

print("="*60)
print("BALL TRACKER - CUSTOM MODEL")
print("="*60)
print(f"Stream: http://<robot_ip>:8080")
print(f"Change target: echo 'yellow' > {target_file}")
print("Options: green, pink, yellow, all")

print("\n1. Initializing RealSense...")
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
profile = pipeline.start(config)
depth_scale = profile.get_device().first_depth_sensor().get_depth_scale()
print(f"✓ Depth scale: {depth_scale}")
align = rs.align(rs.stream.color)

print("Warming up...")
for i in range(30):
    pipeline.poll_for_frames()
    time.sleep(0.033)
print("✓ RealSense ready")

print("\n2. Loading model...")
model = YOLO('/home/unitree/depth_test/final_best.pt', task='detect')
for _ in range(3):
    model(np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8), verbose=False)
print("✓ Model ready")

with open(cmd_file, 'w') as f:
    f.write('0.0,0.0,0.0')

print("\n" + "="*60)
print("TRACKING ACTIVE")
print("="*60 + "\n")

try:
    loop_count = 0
    last_detection_time = time.time()
    ball_found = False
    
    while True:
        loop_count += 1
        frames = pipeline.poll_for_frames()
        if not frames:
            time.sleep(0.01)
            continue
        
        aligned = align.process(frames)
        depth_frame = aligned.get_depth_frame()
        color_frame = aligned.get_color_frame()
        if not depth_frame or not color_frame:
            continue
        
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())
        display_image = color_image.copy()
        
        # Show target on display
        t_color = COLORS.get(NAME_TO_ID.get(current_target), (255,255,255))
        cv2.putText(display_image, f"Target: {current_target}", (10, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, t_color, 2)
        
        results = model(color_image, classes=target_classes, verbose=False)
        
        if len(results[0].boxes) > 0:
            last_detection_time = time.time()
            box = results[0].boxes[0]
            conf = float(box.conf.cpu().numpy()[0])
            cls_id = int(box.cls.cpu().numpy()[0])
            cls_name = CLASS_NAMES.get(cls_id, f"class_{cls_id}")
            color = COLORS.get(cls_id, (255, 255, 255))
            xyxy = box.xyxy.cpu().numpy()[0].astype(int)
            
            cv2.rectangle(display_image, (xyxy[0], xyxy[1]), (xyxy[2], xyxy[3]), color, 2)
            
            x_center = int((xyxy[0] + xyxy[2]) / 2)
            y_center = int((xyxy[1] + xyxy[3]) / 2)
            x_c = max(5, min(634, x_center))
            y_c = max(5, min(474, y_center))
            
            cv2.circle(display_image, (x_center, y_center), 5, color, -1)
            
            depth_region = depth_image[y_c-3:y_c+4, x_c-3:x_c+4]
            valid_depths = depth_region[depth_region > 0]
            
            if len(valid_depths) < 5:
                with frame_lock:
                    latest_frame = display_image
                continue
            
            distance = np.median(valid_depths) * depth_scale
            
            if distance < 0.1 or distance > 3.0:
                with frame_lock:
                    latest_frame = display_image
                continue
            
            error = x_center - 320
            turn_speed = -error / 320.0
            if abs(turn_speed) < 0.08:
                turn_speed = 0.0
            
            d_error = distance - 0.45
            
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
            
            cv2.putText(display_image, f"{cls_name} {distance:.2f}m {status}", 
                       (xyxy[0], xyxy[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            if status == "HOLDING" and not ball_found:
                print(f"Ball found: {cls_name}")
                ball_found = True
            
            with open(cmd_file, 'w') as f:
                f.write(f'{vx:.3f},0.0,{vyaw:.3f}')
            
            if loop_count % 10 == 0:
                print(f"{status:12s} | {cls_name:11s} | dist: {distance:5.2f}m | conf={conf:.2f}")
        
        else:
            ball_found = False
            if time.time() - last_detection_time > 0.5:
                with open(cmd_file, 'w') as f:
                    f.write('0.0,0.0,0.4')
                cv2.putText(display_image, f"SEARCHING {current_target}...", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                if loop_count % 10 == 0:
                    print(f"SEARCHING {current_target}...")
        
        with frame_lock:
            latest_frame = display_image
        
        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    with open(cmd_file, 'w') as f:
        f.write('0.0,0.0,0.0')
    pipeline.stop()
    print("Stopped")
