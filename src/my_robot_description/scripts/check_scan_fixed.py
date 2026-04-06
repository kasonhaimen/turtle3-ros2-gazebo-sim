#!/usr/bin/env python3
import rclpy
from sensor_msgs.msg import LaserScan

def scan_callback(msg):
    print(f"Scan received!")
    print(f"  header.frame_id: {msg.header.frame_id}")
    print(f"  angle_min: {msg.angle_min}")
    print(f"  angle_max: {msg.angle_max}")
    print(f"  ranges count: {len(msg.ranges)}")
    print(f"  ranges[0]: {msg.ranges[0] if msg.ranges else 'N/A'}")
    rclpy.shutdown()

rclpy.init()
node = rclpy.create_node('scan_checker')
node.create_subscription(LaserScan, '/scan_fixed', scan_callback, 10)
print("Listening for one /scan_fixed message...")
rclpy.spin(node)