#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan
import numpy as np

class RobustAvoider(Node):
    def __init__(self):
        super().__init__('robust_avoider')
        self.publisher_ = self.create_publisher(Twist, '/cmd_vel', 10)
        self.subscription = self.create_subscription(LaserScan, '/scan', self.listener_callback, 10)
        self.safe_distance = 0.8  # 0.8米内避障
        self.get_logger().info("避障脚本已启动，监听 /scan 中...")

    def listener_callback(self, msg):
        ranges = np.array(msg.ranges)
        
        # --- 关键过滤步骤 ---
        # 1. 剔除 0 (通常是无效数据) 和 inf (无穷远)
        ranges = np.where((ranges < 0.05) | np.isinf(ranges), 10.0, ranges)
        
        # 2. 确定正前方区域 (取中间 10% 的数据量)
        num_samples = len(ranges)
        margin = num_samples // 20  # 取左右各 5%
        center = num_samples // 2
        front_sector = ranges[center - margin : center + margin]
        
        # 3. 使用平均值或中位数，防止单个噪点触发
        avg_dist = np.mean(front_sector)
        min_dist = np.min(front_sector)

        move_cmd = Twist()
        # 只有当 最小值 真的小于安全距离时才转弯
        if min_dist < self.safe_distance:
            self.get_logger().warn(f'⚠️ 障碍物过近! 最小距离: {min_dist:.2f}m')
            move_cmd.linear.x = 0.0
            move_cmd.angular.z = 0.5
        else:
            # 只有当平均距离也安全时才前进
            self.get_logger().info(f'✅ 路径安全。前方平均距离: {avg_dist:.2f}m')
            move_cmd.linear.x = 0.3
            move_cmd.angular.z = 0.0

        self.publisher_.publish(move_cmd)

def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(RobustAvoider())
    rclpy.shutdown()

if __name__ == '__main__':
    main()