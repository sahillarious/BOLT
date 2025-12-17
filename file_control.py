#!/usr/bin/env python3
"""
File-based robot control - reads commands from file
Run this in Terminal 1 on the robot
Supports velocity commands (vx,vy,vyaw) and pose commands ('stand', 'sit')
"""
import sys
import time
import logging
sys.path.insert(0, '/home/unitree/Documents/code/unitree_sdk2_python')
from unitree_sdk2py.core.channel import ChannelFactortyInitialize
from unitree_sdk2py.go2.sport.sport_client import SportClient

# Set up logging to file
logging.basicConfig(filename='/home/unitree/depth_test/file_control.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

print("="*60)
print("ROBOT CONTROL - FILE-BASED")
print("="*60)

# Initialize robot
print("\nInitializing robot...")
logging.info("Initializing robot")
try:
    ChannelFactortyInitialize(0)
    client = SportClient()
    client.SetTimeout(10.0)
    client.Init()
    print("Standing up...")
    logging.info("Standing up")
    client.RecoveryStand()
    time.sleep(2)
except Exception as e:
    print(f"Init error: {e}")
    logging.error(f"Init error: {e}")
    sys.exit(1)

# Command file (updated to match pose_control.py)
cmd_file = '/home/unitree/depth_test/velocities.txt'

# Write default
with open(cmd_file, 'w') as f:
    f.write('0.0,0.0,0.0')

print(f"✓ Ready - reading from {cmd_file}")
logging.info(f"Ready - reading from {cmd_file}")
print("Press Ctrl+C to stop\n")

vx, vy, vyaw = 0.0, 0.0, 0.0
current_pose = "stand"  # Track current pose
iteration = 0

try:
    while True:
        # Read command from file
        try:
            with open(cmd_file, 'r') as f:
                content = f.read().strip()
                parts = content.split(',')
                if len(parts) == 1 and parts[0] in ['stand', 'sit']:
                    # Pose command
                    pose_cmd = parts[0]
                    if pose_cmd != current_pose:
                        try:
                            if pose_cmd == "sit":
                                client.StandDown()
                                current_pose = "sit"
                            elif pose_cmd == "stand":
                                client.StandUp()
                                current_pose = "stand"
                            print(f"Executed pose: {pose_cmd}")
                            logging.info(f"Executed pose: {pose_cmd}")
                            time.sleep(2)  # Delay for stability
                        except Exception as e:
                            print(f"Pose error: {e}")
                            logging.error(f"Pose error: {e}")
                    # Skip Move for pose commands
                    time.sleep(0.01)
                    iteration += 1
                    continue
                elif len(parts) >= 3:
                    # Velocity command
                    vx = float(parts[0])
                    vy = float(parts[1])
                    vyaw = float(parts[2])
        except Exception as e:
            print(f"Read error: {e}")
            logging.error(f"Read error: {e}")
            pass
        
        # Send move command (only for velocities)
        try:
            client.Move(vx, vy, vyaw)
        except Exception as e:
            print(f"Move error: {e}")
            logging.error(f"Move error: {e}")
        
        if iteration % 100 == 0:
            print(f"vx={vx:+.2f}, vyaw={vyaw:+.2f}, pose={current_pose}")
            logging.info(f"vx={vx:+.2f}, vyaw={vyaw:+.2f}, pose={current_pose}")
        
        iteration += 1
        time.sleep(0.01)  # 100Hz

except KeyboardInterrupt:
    print("\n\nStopping robot...")
    logging.info("Stopping robot")

finally:
    # Stop with multiple commands
    for _ in range(30):
        try:
            client.Move(0.0, 0.0, 0.0)
        except Exception as e:
            print(f"Stop error: {e}")
            logging.error(f"Stop error: {e}")
        time.sleep(0.01)
    
    print("Robot stopped.")
    logging.info("Robot stopped.")