#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan

class ScanFrameFixer(Node):
    def __init__(self):
        super().__init__('scan_frame_fixer')
        self.declare_parameter('input_topic', '/scan')
        self.declare_parameter('output_topic', '/scan_fixed')
        self.declare_parameter('frame_id', 'laser_frame')
        
        input_topic = self.get_parameter('input_topic').get_parameter_value().string_value
        output_topic = self.get_parameter('output_topic').get_parameter_value().string_value
        frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
        
        self.sub = self.create_subscription(
            LaserScan,
            input_topic,
            self.callback,
            10
        )
        self.pub = self.create_publisher(LaserScan, output_topic, 10)
        self.frame_id = frame_id
        self.get_logger().info(f'ScanFrameFixer: {input_topic} -> {output_topic} (frame_id: {frame_id})')
        
    def callback(self, msg: LaserScan):
        msg.header.frame_id = self.frame_id
        self.pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = ScanFrameFixer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
