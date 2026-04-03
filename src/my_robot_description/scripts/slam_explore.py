import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist

class SlamExplorer(Node):
    def __init__(self):
        super().__init__('slam_explorer')
        self.publisher_ = self.create_publisher(Twist, '/cmd_vel', 10)
        self.subscription = self.create_subscription(LaserScan, '/scan', self.listener_callback, 10)
        self.move_cmd = Twist()

    def listener_callback(self, msg):
        # 将激光雷达数据分为：右侧、前方、左侧
        # 假设激光雷达是 360 度，索引分布取决于你的雷达配置
        regions = {
            'right':  min(min(msg.ranges[0:120]), 10),
            'fright': min(min(msg.ranges[120:240]), 10),
            'front':  min(min(msg.ranges[240:360]), 10),
            'fleft':  min(min(msg.ranges[360:480]), 10),
            'left':   min(min(msg.ranges[480:600]), 10),
        }
        self.take_action(regions)

    def take_action(self, regions):
        d = 0.7  # 期望离墙距离
        linear_speed = 0.3
        angular_speed = 0.6

        if regions['front'] > d and regions['fleft'] > d and regions['fright'] > d:
            # 前方无障碍，直行并轻微向右靠寻找墙壁
            self.move_cmd.linear.x = linear_speed
            self.move_cmd.angular.z = -0.1 
        elif regions['front'] < d:
            # 面前有墙，左转
            self.move_cmd.linear.x = 0.0
            self.move_cmd.angular.z = angular_speed
        elif regions['fright'] < d:
            # 右前方太近，向左微调
            self.move_cmd.linear.x = linear_speed
            self.move_cmd.angular.z = angular_speed
        elif regions['fright'] > d + 0.2:
            # 离墙太远，向右微调
            self.move_cmd.linear.x = linear_speed
            self.move_cmd.angular.z = -angular_speed
        
        self.publisher_.publish(self.move_cmd)

def main(args=None):
    rclpy.init(args=args)
    node = SlamExplorer()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()