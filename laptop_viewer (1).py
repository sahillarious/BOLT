#!/usr/bin/env python3
"""
Laptop viewer for robot ball tracker
Displays MJPEG stream and buttons to change target
Usage: python laptop_viewer.py <robot_ip>
"""
import sys
import tkinter as tk
import urllib.request
import threading
from PIL import Image, ImageTk
import io
import paramiko

# Robot connection - change this to your robot's IP
ROBOT_IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.123.18"
ROBOT_USER = "unitree"
ROBOT_PASS = "123"
TARGET_FILE = "/home/unitree/depth_test/target.txt"
STREAM_URL = f"http://{ROBOT_IP}:8080"

class BallTrackerViewer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"Ball Tracker - {ROBOT_IP}")
        self.root.configure(bg='#2b2b2b')
        
        self.video_label = tk.Label(self.root, bg='black', width=640, height=480)
        self.video_label.pack(padx=10, pady=10)
        
        self.status_var = tk.StringVar(value="Connecting...")
        tk.Label(self.root, textvariable=self.status_var, font=('Arial', 12), 
                 fg='white', bg='#2b2b2b').pack(pady=5)
        
        btn_frame = tk.Frame(self.root, bg='#2b2b2b')
        btn_frame.pack(pady=10)
        
        tk.Label(btn_frame, text="Target:", font=('Arial', 12, 'bold'), 
                 fg='white', bg='#2b2b2b').pack(side=tk.LEFT, padx=5)
        
        for text, color, target in [('ALL', '#888888', 'all'), ('GREEN', '#00ff00', 'green'),
                                     ('PINK', '#ff00ff', 'pink'), ('YELLOW', '#ffff00', 'yellow')]:
            tk.Button(btn_frame, text=text, width=8, font=('Arial', 11, 'bold'),
                     bg=color, command=lambda t=target: self.set_target(t)).pack(side=tk.LEFT, padx=5)
        
        self.target_var = tk.StringVar(value="Current: all")
        tk.Label(self.root, textvariable=self.target_var, font=('Arial', 14, 'bold'), 
                 fg='#00ff00', bg='#2b2b2b').pack(pady=10)
        
        self.running = True
        threading.Thread(target=self.stream_video, daemon=True).start()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def set_target(self, target):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ROBOT_IP, username=ROBOT_USER, password=ROBOT_PASS, timeout=5)
            ssh.exec_command(f"echo '{target}' > {TARGET_FILE}")
            ssh.close()
            self.target_var.set(f"Current: {target}")
            self.status_var.set(f"Target set to: {target}")
        except Exception as e:
            self.status_var.set(f"SSH Error: {e}")
    
    def stream_video(self):
        import time
        while self.running:
            try:
                stream = urllib.request.urlopen(STREAM_URL, timeout=5)
                data = b''
                while self.running:
                    chunk = stream.read(4096)
                    if not chunk:
                        break
                    data += chunk
                    start = data.find(b'\xff\xd8')
                    end = data.find(b'\xff\xd9')
                    if start != -1 and end != -1 and end > start:
                        try:
                            img = Image.open(io.BytesIO(data[start:end+2]))
                            photo = ImageTk.PhotoImage(img)
                            self.video_label.configure(image=photo)
                            self.video_label.image = photo
                            self.status_var.set("Connected")
                        except: pass
                        data = data[end+2:]
            except Exception as e:
                self.status_var.set(f"Connecting... {e}")
                time.sleep(2)
    
    def on_close(self):
        self.running = False
        self.root.destroy()
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    print(f"Connecting to {ROBOT_IP}...")
    BallTrackerViewer().run()
