#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseStamped
from nav_msgs.msg import Odometry, Path
import tf_transformations # 如果没安装：sudo apt install ros-humble-tf-transformations
import math
import numpy as np

class StarPlannerPID(Node):
    def __init__(self):
        super().__init__('star_planner_pid')
        
        # 发布与订阅
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.path_pub = self.create_publisher(Path, '/robot_path', 10)
        self.odom_sub = self.create_subscription(Odometry, '/odom', self.odom_callback, 10)
        
        # 轨迹消息初始化
        self.path = Path()
        self.path.header.frame_id = 'odom'
        
        # PID 参数
        self.kp_linear = 0.5
        self.kp_angular = 2.0
        
        # 机器人状态
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_yaw = 0.0
        
        # 五角星任务状态机
        self.state = "MOVE" # MOVE 或 TURN
        self.side_count = 0
        self.side_length = 2.0  # 每条边长 2 米
        self.turn_angle = 144.0 * (math.pi / 180.0) # 五角星外角 144 度
        
        # 记录起始点
        self.start_x = 0.0
        self.start_y = 0.0
        self.start_yaw = 0.0
        self.first_run = True

        self.timer = self.create_timer(0.1, self.control_loop)

    def odom_callback(self, msg):
        # 获取位置
        self.current_x = msg.pose.pose.position.x
        self.current_y = msg.pose.pose.position.y
        
        # 获取朝向 (四元数转欧拉角)
        q = msg.pose.pose.orientation
        euler = tf_transformations.euler_from_quaternion([q.x, q.y, q.z, q.w])
        self.current_yaw = euler[2]
        
        # 更新 RViz 轨迹数据
        pose = PoseStamped()
        pose.header = msg.header
        pose.pose = msg.pose.pose
        self.path.poses.append(pose)
        self.path_pub.publish(self.path)

        if self.first_run:
            self.reset_reference()
            self.first_run = False

    def reset_reference(self):
        self.start_x = self.current_x
        self.start_y = self.current_y
        self.start_yaw = self.current_yaw

    def control_loop(self):
        if self.first_run or self.side_count >= 5:
            self.stop_robot()
            return

        msg = Twist()
        
        if self.state == "MOVE":
            # 计算已走距离
            dist_moved = math.sqrt((self.current_x - self.start_x)**2 + (self.current_y - self.start_y)**2)
            error = self.side_length - dist_moved
            
            if error > 0.05:
                msg.linear.x = min(self.kp_linear * error, 0.4) # 限制最大速度
            else:
                self.stop_robot()
                self.state = "TURN"
                self.reset_reference()
                self.get_logger().info(f"已完成第 {self.side_count+1} 条边，开始转弯")
        
        elif self.state == "TURN":
            # 计算已转角度 (处理 -pi 到 pi 的跳转)
            angle_diff = self.current_yaw - self.start_yaw
            while angle_diff > math.pi: angle_diff -= 2*math.pi
            while angle_diff < -math.pi: angle_diff += 2*math.pi
            
            error = self.turn_angle - abs(angle_diff)
            
            if error > 0.05:
                msg.angular.z = 0.6 * (self.kp_angular * error / self.turn_angle) + 0.1
            else:
                self.stop_robot()
                self.state = "MOVE"
                self.side_count += 1
                self.reset_reference()
                self.get_logger().info(f"转向完毕，开始第 {self.side_count+1} 条边")

        self.cmd_pub.publish(msg)

    def stop_robot(self):
        self.cmd_pub.publish(Twist())

def main():
    rclpy.init()
    rclpy.spin(StarPlannerPID())
    rclpy.shutdown()

if __name__ == '__main__':
    main()