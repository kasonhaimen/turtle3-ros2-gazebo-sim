# 问题1：LaserScan 没有显示红点

## 问题描述

在RViz中，LaserScan面板没有显示激光扫描的红点。

## 排查过程

### 1. 检查topic数据

运行诊断脚本检查 `/scan` topic的实际内容：

```bash
source ~/ros2_ws/install/setup.bash
python3 ~/ros2_ws/src/my_robot_description/scripts/check_scan.py
```

**检查结果**：
```
Scan received!
  header.frame_id: my_cool_robot/base_link/laser
  angle_min: -3.140000104904175
  angle_max: 3.140000104904175
  ranges count: 360
  ranges[0]: 2.91261625289917
```

发现问题：`header.frame_id` 是 `my_cool_robot/base_link/laser`

### 2. 检查TF tree

```bash
ros2 run tf2_tools view_frames
```

**检查结果**：TF tree中存在 `laser_frame` frame
```
base_link: 
  parent: 'odom'
odom -> base_link
base_link -> chassis
chassis -> laser_frame
```

### 3. 分析问题

LaserScan的 `header.frame_id` 是 `my_cool_robot/base_link/laser`，但TF tree中的frame名称是 `laser_frame`。两者不匹配，导致RViz无法正确显示激光数据。

## 问题原理

Gazebo Harmonic的 `gpu_lidar` sensor在生成LaserScan消息时，`header.frame_id`是根据Gazebo内部的模型结构生成的。在URDF到SDF的转换过程中，sensor被放在了 `base_link` 下而非 `laser_frame` 下，导致frame_id变成了 `my_cool_robot/base_link/laser`。

### Gazebo日志中的警告

```
Warning: XML Element[frame_id], child of element[sensor], not defined in SDF.
Warning: XML Element[ignition_frame_id], child of element[sensor], not defined in SDF.
[/sdf/model[@name="my_cool_robot"]/link[@name="base_link"]/sensor[@name="laser"]]
```

这证实了Gazebo在解析URDF时将sensor放在了错误的位置。

## 解决方法

### 步骤1：创建scan_frame_fixer.py

创建 `scripts/scan_frame_fixer.py` 节点：

```python
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
```

### 步骤2：修改launch文件

修改 `launch/slam-sim.launch.py`，添加scan_frame_fixer节点：

```python
# 9. LaserScan frame_id 修复节点
scan_fixer_script = os.path.join(pkg_share, 'scripts', 'scan_frame_fixer.py')
scan_fixer = ExecuteProcess(
    cmd=['/usr/bin/python3', scan_fixer_script],
    output='screen'
)

# 在LaunchDescription中添加
return LaunchDescription([
    ...
    scan_fixer
])
```

### 步骤3：更新rviz配置

修改 `rviz/slam.rviz`，将LaserScan的Topic从 `/scan` 改为 `/scan_fixed`：

```yaml
      Topic:
        Depth: 5
        Durability Policy: Volatile
        Filter size: 10
        History Policy: Keep Last
        Reliability Policy: Reliable
        Value: /scan_fixed    # 原来是 /scan
```

### 步骤4：更新slam配置

修改 `config/mapper_params_online_async.yaml`：

```yaml
    scan_topic: /scan_fixed    # 原来是 /scan
```

### 步骤5：更新CMakeLists.txt

修改 `CMakeLists.txt`，添加脚本安装：

```cmake
install(PROGRAMS
  scripts/obstacle_avoidance.py
  scripts/scan_frame_fixer.py    # 添加这一行
  DESTINATION lib/${PROJECT_NAME}
)
```

## 验证结果

修复后运行：

```bash
python3 ~/ros2_ws/src/my_robot_description/scripts/check_scan_fixed.py
```

输出：
```
Listening for one /scan_fixed message...
Scan received!
  header.frame_id: laser_frame    # 现在是正确的frame_id
  angle_min: -3.140000104904175
  angle_max: 3.140000104904175
  ranges count: 360
  ranges[0]: 2.91261625289917
```

RViz中LaserScan可以正确显示红点了。
